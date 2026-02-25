# -*- coding: utf-8 -*-
import csv
import fnmatch
import json
import logging
import logging.config
import os
import pprint
import shutil
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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
            'url_entries_detected': 0,
            'url_origin_saved': 0,
            'collision_strategy': self.args.get('collision_strategy', 'path-score'),
            'link_mode': self.args.get('link_mode', 'copy'),
            'details': [],
            'origin_links': [],
        }
        log.info('\n' + pp.pformat(self.args))

    @staticmethod
    def setup_logging():
        module_path = os.path.abspath(os.path.dirname(__file__))
        cfg_path = os.path.join(module_path, 'logging.conf')

        if os.path.exists(cfg_path):
            logging.config.fileConfig(cfg_path)
            return

        # Fallback para build PyInstaller/ambientes sem logging.conf
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        )

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
    def is_url(line):
        return line.lower().startswith('http://') or line.lower().startswith('https://')

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

    @staticmethod
    def resolve_final_url(url, timeout=8):
        try:
            req = Request(url, method='HEAD', headers={'User-Agent': 'm3u-dump/1.2'})
            with urlopen(req, timeout=timeout) as resp:
                return resp.geturl()
        except Exception:
            try:
                req = Request(url, method='GET', headers={'User-Agent': 'm3u-dump/1.2'})
                with urlopen(req, timeout=timeout) as resp:
                    return resp.geturl()
            except Exception:
                return url

    def capture_url_origins(self, playlist_lines):
        resolve_final = self.args.get('resolve_url_final', True)
        for line in playlist_lines:
            if self.is_comment(line) or not self.is_url(line):
                continue

            self.report['url_entries_detected'] += 1
            final_url = self.resolve_final_url(line) if resolve_final else line
            parsed = urlparse(final_url)
            origin_server = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ''

            item = {
                'original_url': line,
                'final_url': final_url,
                'origin_server': origin_server,
            }
            self.report['origin_links'].append(item)
            self.report['url_origin_saved'] += 1

    def fix_playlist(self_or_search_path_files, search_path_files_or_playlist_lines, playlist_lines=None):
        """Backward compatible:
        - legacy static usage: M3uDump.fix_playlist(search_path_files, playlist_lines)
        - instance usage: self.fix_playlist(search_path_files, playlist_lines)
        """
        if playlist_lines is None:
            # legacy static call style
            self = None
            search_path_files = self_or_search_path_files
            playlist_lines = search_path_files_or_playlist_lines
            strategy = 'path-score'
            report = None
        else:
            self = self_or_search_path_files
            search_path_files = search_path_files_or_playlist_lines
            strategy = self.args.get('collision_strategy', 'path-score')
            report = self.report

        new_playlist_lines = []

        for line in playlist_lines:
            if M3uDump.is_comment(line):
                new_playlist_lines.append(line)
                continue

            if M3uDump.is_url(line):
                new_playlist_lines.append(line)
                continue

            if os.path.exists(line):
                new_playlist_lines.append(line)
                continue

            basename = os.path.basename(line)
            roots = search_path_files.get(basename, [])

            if roots:
                if report is not None and len(roots) > 1:
                    report['collisions_resolved'] += 1
                fixed_path = M3uDump.choose_candidate_path(line, roots, basename, strategy)
                new_playlist_lines.append(fixed_path)
                if report is not None:
                    report['fixed_paths'] += 1
                    if len(roots) > 1:
                        report['details'].append({
                            'type': 'collision',
                            'basename': basename,
                            'strategy': strategy,
                            'candidates': [os.path.join(root, basename) for root in roots],
                            'selected': fixed_path,
                        })
            else:
                log.warning('skip dump, because music file of {0} was not found in search path.'.format(basename))
                if report is not None:
                    report['unresolved_paths'] += 1
                if new_playlist_lines and M3uDump.is_comment(new_playlist_lines[-1]):
                    new_playlist_lines.pop()

        return new_playlist_lines

    @staticmethod
    def _materialize(src, dst, mode='copy', report=None):
        if mode == 'copy':
            shutil.copyfile(src, dst)
            if report is not None:
                report['copied'] += 1
            return 'copied'

        if mode == 'hardlink':
            os.link(src, dst)
            if report is not None:
                report['linked'] += 1
            return 'hardlink'

        if mode == 'symlink':
            os.symlink(src, dst)
            if report is not None:
                report['linked'] += 1
            return 'symlink'

        shutil.copyfile(src, dst)
        if report is not None:
            report['copied'] += 1
        return 'copied'

    def copy_music(self_or_playlist_lines, playlist_lines_or_dump_music_path, dump_music_path_or_dry_run, dry_run=None):
        """Backward compatible:
        - legacy static usage: M3uDump.copy_music(playlist_lines, dump_music_path, dry_run)
        - instance usage: self.copy_music(playlist_lines, dump_music_path, dry_run)
        """
        if dry_run is None:
            # legacy static call style
            playlist_lines = self_or_playlist_lines
            dump_music_path = playlist_lines_or_dump_music_path
            dry_run = dump_music_path_or_dry_run
            skip_existing = False
            link_mode = 'copy'
            report = None
        else:
            self = self_or_playlist_lines
            playlist_lines = playlist_lines_or_dump_music_path
            dump_music_path = dump_music_path_or_dry_run
            skip_existing = self.args.get('skip_existing', True)
            link_mode = self.args.get('link_mode', 'copy')
            report = self.report

        for line in playlist_lines:
            if M3uDump.is_comment(line) or M3uDump.is_url(line):
                continue
            if not os.path.exists(line):
                log.warning('skip copy, because music file({}) was not found.'.format(line))
                if report is not None:
                    report['copy_skipped_missing'] += 1
                continue

            dst = os.path.join(dump_music_path, os.path.basename(line))

            if skip_existing and os.path.exists(dst):
                log.info('skip existing {0}'.format(dst))
                if report is not None:
                    report['copy_skipped_existing'] += 1
                    report['details'].append({'type': 'skip_existing', 'src': line, 'dst': dst})
                continue

            if not dry_run:
                action = M3uDump._materialize(line, dst, mode=link_mode, report=report)
                log.info('{0} {1} -> {2}'.format(action, line, dst))
                if report is not None:
                    report['details'].append({'type': action, 'src': line, 'dst': dst})
            else:
                log.info('(dryrun)copying {0} -> {1}'.format(line, dst))
                if report is not None:
                    report['details'].append({'type': 'dryrun', 'src': line, 'dst': dst})

    @staticmethod
    def save_playlist(playlist_name, playlist_lines, dump_music_path, dry_run):
        playlist_path = os.path.join(dump_music_path, playlist_name)
        if not dry_run:
            with open(playlist_path, 'w', encoding='utf-8') as f:
                log.info('writing playlist({})...'.format(playlist_path))
                for line in playlist_lines:
                    if M3uDump.is_comment(line):
                        f.write(line + '\n')
                    elif M3uDump.is_url(line):
                        f.write(line + '\n')
                    else:
                        f.write(os.path.basename(line) + '\n')
        else:
            log.info('(dryrun)writing playlist({})...'.format(playlist_path))

    def dump_playlist(self, playlist_path):
        playlist_lines = list(M3uDump.parse_playlist(playlist_path))
        self.capture_url_origins(playlist_lines)

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

        origin_path = self.args.get('origin_links_file')
        if origin_path:
            with open(origin_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['original_url', 'final_url', 'origin_server'])
                writer.writeheader()
                for row in self.report.get('origin_links', []):
                    writer.writerow(row)
            log.info('origin links written: {}'.format(origin_path))

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
