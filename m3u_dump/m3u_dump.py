# -*- coding: utf-8 -*-
import fnmatch
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
    def fix_playlist(search_path_files, playlist_lines):
        new_playlist_lines = []

        for line in playlist_lines:
            if M3uDump.is_comment(line):
                new_playlist_lines.append(line)
                continue

            if os.path.exists(line):
                new_playlist_lines.append(line)
                continue

            basename = os.path.basename(line)
            if basename in search_path_files:
                fixed_path = os.path.join(search_path_files[basename][0], basename)
                new_playlist_lines.append(fixed_path)
            else:
                log.warning(
                    'skip dump, because music file of {0} was not found in search path.'.format(basename)
                )
                # remove previous comment pair when applicable
                if new_playlist_lines and M3uDump.is_comment(new_playlist_lines[-1]):
                    new_playlist_lines.pop()

        return new_playlist_lines

    @staticmethod
    def copy_music(playlist_lines, dump_music_path, dry_run):
        for line in playlist_lines:
            if M3uDump.is_comment(line):
                continue
            if not os.path.exists(line):
                log.warning('skip copy, because music file({}) was not found.'.format(line))
                continue

            dst = os.path.join(dump_music_path, os.path.basename(line))
            if not dry_run:
                log.info('copying {0} -> {1}'.format(line, dst))
                shutil.copyfile(line, dst)
            else:
                log.info('(dryrun)copying {0} -> {1}'.format(line, dst))

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
                        music_file_name = os.path.basename(line)
                        f.write(music_file_name + '\n')
        else:
            log.info('(dryrun)writing playlist({})...'.format(playlist_path))

    def dump_playlist(self, playlist_path):
        playlist_lines = list(M3uDump.parse_playlist(playlist_path))
        log.debug('playlist_line is follows...')
        show_num = len(playlist_lines) if len(playlist_lines) < 3 else 3
        for i in range(0, show_num):
            log.debug(playlist_lines[i])

        if self.args.get('fix_search_path'):
            search_path_files = M3uDump.get_search_path_files(self.args['fix_search_path'])
            playlist_lines = M3uDump.fix_playlist(search_path_files, playlist_lines)

        M3uDump.copy_music(playlist_lines, self.args['dump_music_path'], self.args['dry_run'])

        if self.args.get('with_playlist', True):
            playlist_name = os.path.basename(playlist_path)
            M3uDump.save_playlist(
                playlist_name,
                playlist_lines,
                self.args['dump_music_path'],
                self.args['dry_run'],
            )

    @staticmethod
    def load_from_playlist_path(load_m3u_path, pattern_list):
        """Return playlist paths in playlist directory."""
        log.info('loading playlist({})...'.format(load_m3u_path))
        log.info('allowed pattern is {}'.format(pattern_list))
        path_list = []
        for root, _dirs, files in os.walk(load_m3u_path):
            for filename in files:
                if any(fnmatch.fnmatch(filename, pattern) for pattern in pattern_list):
                    path_list.append(os.path.join(root, filename))
        return sorted(path_list)

    def start(self):
        log.debug('start -----')

        load_m3u_path = self.args['load_m3u_path']
        if os.path.isfile(load_m3u_path):
            paths = [load_m3u_path]
        else:
            paths = M3uDump.load_from_playlist_path(load_m3u_path, self.args['playlist_pattern_list'])

        log.info('playlist is {}'.format(paths))
        for path in paths:
            self.dump_playlist(path)
        log.info('copy done.')
