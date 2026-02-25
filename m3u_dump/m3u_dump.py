# -*- coding: utf-8 -*-
import csv
import fnmatch
import json
import logging
import logging.config
import os
import pprint
import shutil

pp = pprint.PrettyPrinter(indent=4)
log = logging.getLogger(__name__)


class M3uDump:
    def __init__(self, args):
        self.args = args
        self.setup_logging()
        self.report = {
            'playlists_processed': 0,
            'copied': 0,
            'linked': 0,
            'copy_skipped_missing': 0,
            'copy_skipped_existing': 0,
            'fixed_paths': 0,
            'unresolved_paths': 0,
            'collisions_resolved': 0,
            'collision_strategy': self.args.get('collision_strategy', 'path-score'),
            'link_mode': self.args.get('link_mode', 'copy'),
            'details': [],
        }
        log.info('\n' + pp.pformat(self.args))

    @staticmethod
    def setup_logging():
        module_path = os.path.abspath(os.path.dirname(__file__))
        logging.config.fileConfig(os.path.join(module_path, 'logging.conf'))

    @staticmethod
    def parse_playlist(playlist_path):
        log.info('playlist{} reading....'.format(playlist_path))
        with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f.readlines() if len(line.strip()) > 0]

    @staticmethod
    def get_search_path_files(search_path):
        log.info('scanning search_path({0})...'.format(search_path))
        search_path_files = {}
        for root, _dirs, files in os.walk(search_path):
            for filename in files:
                search_path_files.setdefault(filename, []).append(root)
        return search_path_files

    @staticmethod
    def is_comment(line):
        return line.lstrip().startswith('#EXTINF') or line.lstrip().startswith('#EXTM3U')

    @staticmethod
    def _path_score(original_line, candidate_root):
        original_parts = set(part.lower() for part in os.path.normpath(original_line).split(os.sep) if part)
        candidate_parts = set(part.lower() for part in os.path.normpath(candidate_root).split(os.sep) if part)
        return len(original_parts.intersection(candidate_parts))

    @staticmethod
    def choose_candidate_path(original_line, roots, basename, strategy='path-score'):
        if not roots:
            return None

        if strategy == 'first':
            selected_root = roots[0]
        elif strategy == 'shortest':
            selected_root = min(roots, key=lambda r: len(os.path.normpath(r).split(os.sep)))
        else:
            ranked = sorted(
                roots,
                key=lambda r: (M3uDump._path_score(original_line, r), -len(os.path.normpath(r).split(os.sep))),
                reverse=True,
            )
            selected_root = ranked[0]

        return os.path.join(selected_root, basename)

    def fix_playlist(self, search_path_files, playlist_lines):
        new_playlist_lines = []
        strategy = self.args.get('collision_strategy', 'path-score')

        for line in playlist_lines:
            if M3uDump.is_comment(line):
                new_playlist_lines.append(line)
                continue

            if os.path.exists(line):
                new_playlist_lines.append(line)
                continue

            basename = os.path.basename(line)
            roots = search_path_files.get(basename, [])

            if roots:
                if len(roots) > 1:
                    self.report['collisions_resolved'] += 1
                fixed_path = M3uDump.choose_candidate_path(line, roots, basename, strategy)
                new_playlist_lines.append(fixed_path)
                self.report['fixed_paths'] += 1
                if len(roots) > 1:
                    self.report['details'].append({
                        'type': 'collision',
                        'basename': basename,
                        'strategy': strategy,
                        'candidates': [os.path.join(root, basename) for root in roots],
                        'selected': fixed_path,
                    })
            else:
                log.warning('skip dump, because music file of {0} was not found in search path.'.format(basename))
                self.report['unresolved_paths'] += 1
                if new_playlist_lines and M3uDump.is_comment(new_playlist_lines[-1]):
                    new_playlist_lines.pop()

        return new_playlist_lines

    def _materialize(self, src, dst):
        mode = self.args.get('link_mode', 'copy')
        if mode == 'copy':
            shutil.copyfile(src, dst)
            self.report['copied'] += 1
            return 'copied'

        if mode == 'hardlink':
            os.link(src, dst)
            self.report['linked'] += 1
            return 'hardlink'

        if mode == 'symlink':
            os.symlink(src, dst)
            self.report['linked'] += 1
            return 'symlink'

        shutil.copyfile(src, dst)
        self.report['copied'] += 1
        return 'copied'

    def copy_music(self, playlist_lines, dump_music_path, dry_run):
        for line in playlist_lines:
            if M3uDump.is_comment(line):
                continue
            if not os.path.exists(line):
                log.warning('skip copy, because music file({}) was not found.'.format(line))
                self.report['copy_skipped_missing'] += 1
                continue

            dst = os.path.join(dump_music_path, os.path.basename(line))

            if self.args.get('skip_existing', True) and os.path.exists(dst):
                log.info('skip existing {0}'.format(dst))
                self.report['copy_skipped_existing'] += 1
                self.report['details'].append({'type': 'skip_existing', 'src': line, 'dst': dst})
                continue

            if not dry_run:
                action = self._materialize(line, dst)
                log.info('{0} {1} -> {2}'.format(action, line, dst))
                self.report['details'].append({'type': action, 'src': line, 'dst': dst})
            else:
                log.info('(dryrun)copying {0} -> {1}'.format(line, dst))
                self.report['details'].append({'type': 'dryrun', 'src': line, 'dst': dst})

    @staticmethod
    def save_playlist(playlist_name, playlist_lines, dump_music_path, dry_run):
        playlist_path = os.path.join(dump_music_path, playlist_name)
        if not dry_run:
            with open(playlist_path, 'w', encoding='utf-8') as f:
                log.info('writing playlist({})...'.format(playlist_path))
                for line in playlist_lines:
                    if M3uDump.is_comment(line):
                        f.write(line + '\n')
                    else:
                        f.write(os.path.basename(line) + '\n')
        else:
            log.info('(dryrun)writing playlist({})...'.format(playlist_path))

    def dump_playlist(self, playlist_path):
        playlist_lines = list(M3uDump.parse_playlist(playlist_path))

        if self.args.get('fix_search_path'):
            search_path_files = M3uDump.get_search_path_files(self.args['fix_search_path'])
            playlist_lines = self.fix_playlist(search_path_files, playlist_lines)

        self.copy_music(playlist_lines, self.args['dump_music_path'], self.args['dry_run'])

        if self.args.get('with_playlist', True):
            M3uDump.save_playlist(
                os.path.basename(playlist_path),
                playlist_lines,
                self.args['dump_music_path'],
                self.args['dry_run'],
            )

        self.report['playlists_processed'] += 1

    @staticmethod
    def load_from_playlist_path(load_m3u_path, pattern_list):
        log.info('loading playlist({})...'.format(load_m3u_path))
        log.info('allowed pattern is {}'.format(pattern_list))
        path_list = []
        for root, _dirs, files in os.walk(load_m3u_path):
            for filename in files:
                if any(fnmatch.fnmatch(filename, pattern) for pattern in pattern_list):
                    path_list.append(os.path.join(root, filename))
        return sorted(path_list)

    def write_report(self):
        report_path = self.args.get('report_json')
        if report_path:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2)
            log.info('report written: {}'.format(report_path))

        csv_path = self.args.get('report_csv')
        if csv_path:
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['type', 'src', 'dst', 'basename', 'strategy', 'selected'])
                writer.writeheader()
                for row in self.report.get('details', []):
                    writer.writerow({
                        'type': row.get('type', ''),
                        'src': row.get('src', ''),
                        'dst': row.get('dst', ''),
                        'basename': row.get('basename', ''),
                        'strategy': row.get('strategy', ''),
                        'selected': row.get('selected', ''),
                    })
            log.info('csv report written: {}'.format(csv_path))

    def start(self):
        load_m3u_path = self.args['load_m3u_path']
        if os.path.isfile(load_m3u_path):
            paths = [load_m3u_path]
        else:
            paths = M3uDump.load_from_playlist_path(load_m3u_path, self.args['playlist_pattern_list'])

        log.info('playlist is {}'.format(paths))
        for path in paths:
            self.dump_playlist(path)

        self.write_report()
        log.info('copy done.')
