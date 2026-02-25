# -*- coding: utf-8 -*-
import json
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from m3u_dump.m3u_dump import M3uDump


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('m3u-dump Pro for Windows')
        self.geometry('980x700')
        self.minsize(900, 620)

        self.var_source = tk.StringVar()
        self.var_output = tk.StringVar()
        self.var_fix = tk.StringVar()
        self.var_patterns = tk.StringVar(value='*.m3u,*.m3u8')
        self.var_collision = tk.StringVar(value='path-score')
        self.var_linkmode = tk.StringVar(value='copy')
        self.var_report_json = tk.StringVar()
        self.var_report_csv = tk.StringVar()
        self.var_skip_existing = tk.BooleanVar(value=True)
        self.var_with_playlist = tk.BooleanVar(value=True)
        self.var_dry_run = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill='both', expand=True)

        title = ttk.Label(root, text='m3u-dump Pro for Windows', font=('Segoe UI', 16, 'bold'))
        title.pack(anchor='w', pady=(0, 12))

        grid = ttk.Frame(root)
        grid.pack(fill='x')
        for i in range(3):
            grid.columnconfigure(i, weight=1)

        self._row_path(grid, 0, 'Origem (playlist ou pasta):', self.var_source, self._pick_source)
        self._row_path(grid, 1, 'Destino (pasta):', self.var_output, self._pick_output)
        self._row_path(grid, 2, 'Fix Search Path (opcional):', self.var_fix, self._pick_fix)
        self._row_path(grid, 3, 'Relatório JSON (opcional):', self.var_report_json, self._pick_json)
        self._row_path(grid, 4, 'Relatório CSV (opcional):', self.var_report_csv, self._pick_csv)

        ttk.Label(grid, text='Padrões de playlist (separados por vírgula):').grid(row=5, column=0, sticky='w', pady=6)
        ttk.Entry(grid, textvariable=self.var_patterns).grid(row=5, column=1, columnspan=2, sticky='ew', pady=6)

        opts = ttk.Frame(root)
        opts.pack(fill='x', pady=8)

        ttk.Label(opts, text='Estratégia de colisão:').grid(row=0, column=0, sticky='w')
        ttk.Combobox(opts, textvariable=self.var_collision, values=['first', 'shortest', 'path-score'], state='readonly', width=18).grid(row=0, column=1, padx=8)

        ttk.Label(opts, text='Link mode:').grid(row=0, column=2, sticky='w')
        ttk.Combobox(opts, textvariable=self.var_linkmode, values=['copy', 'hardlink', 'symlink'], state='readonly', width=14).grid(row=0, column=3, padx=8)

        ttk.Checkbutton(opts, text='Skip existing', variable=self.var_skip_existing).grid(row=0, column=4, padx=8)
        ttk.Checkbutton(opts, text='Gerar playlist no destino', variable=self.var_with_playlist).grid(row=0, column=5, padx=8)
        ttk.Checkbutton(opts, text='Dry-run', variable=self.var_dry_run).grid(row=0, column=6, padx=8)

        bar = ttk.Frame(root)
        bar.pack(fill='x', pady=(6, 8))
        self.btn_run = ttk.Button(bar, text='Executar', command=self.run_job)
        self.btn_run.pack(side='left')
        ttk.Button(bar, text='Salvar preset', command=self.save_preset).pack(side='left', padx=8)
        ttk.Button(bar, text='Carregar preset', command=self.load_preset).pack(side='left')

        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(fill='x', pady=(0, 8))

        self.log = tk.Text(root, height=20, wrap='word')
        self.log.pack(fill='both', expand=True)

    def _row_path(self, parent, row, label, var, cmd):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=6)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky='ew', pady=6, padx=(0, 8))
        ttk.Button(parent, text='Selecionar', command=cmd).grid(row=row, column=2, sticky='ew', pady=6)

    def _pick_source(self):
        path = filedialog.askopenfilename(title='Selecione playlist')
        if not path:
            path = filedialog.askdirectory(title='Selecione pasta de playlists')
        if path:
            self.var_source.set(path)

    def _pick_output(self):
        path = filedialog.askdirectory(title='Selecione pasta de saída')
        if path:
            self.var_output.set(path)

    def _pick_fix(self):
        path = filedialog.askdirectory(title='Selecione pasta para fix-search-path')
        if path:
            self.var_fix.set(path)

    def _pick_json(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            self.var_report_json.set(path)

    def _pick_csv(self):
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if path:
            self.var_report_csv.set(path)

    def append_log(self, text):
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.update_idletasks()

    def _validate(self):
        if not self.var_source.get().strip():
            raise ValueError('Informe a origem (playlist ou pasta).')
        if not self.var_output.get().strip():
            raise ValueError('Informe a pasta de destino.')

    def _build_args(self):
        patterns = [p.strip() for p in self.var_patterns.get().split(',') if p.strip()]
        return {
            'load_m3u_path': self.var_source.get().strip(),
            'dump_music_path': self.var_output.get().strip(),
            'dry_run': self.var_dry_run.get(),
            'with_playlist': self.var_with_playlist.get(),
            'fix_search_path': self.var_fix.get().strip() or None,
            'playlist_pattern_list': tuple(patterns or ['*.m3u', '*.m3u8']),
            'collision_strategy': self.var_collision.get(),
            'report_json': self.var_report_json.get().strip() or None,
            'report_csv': self.var_report_csv.get().strip() or None,
            'skip_existing': self.var_skip_existing.get(),
            'link_mode': self.var_linkmode.get(),
        }

    def run_job(self):
        try:
            self._validate()
        except ValueError as e:
            messagebox.showerror('Validação', str(e))
            return

        self.btn_run.configure(state='disabled')
        self.progress.start(12)
        self.append_log('Iniciando execução...')

        def worker():
            try:
                args = self._build_args()
                os.makedirs(args['dump_music_path'], exist_ok=True)
                runner = M3uDump(args)
                runner.start()
                self.after(0, lambda: self.append_log('Finalizado com sucesso.'))
            except Exception as ex:
                self.after(0, lambda: self.append_log(f'ERRO: {ex}'))
                self.after(0, lambda: messagebox.showerror('Erro', str(ex)))
            finally:
                self.after(0, self._finish_run)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self):
        self.progress.stop()
        self.btn_run.configure(state='normal')

    def save_preset(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._build_args(), f, ensure_ascii=False, indent=2)
        self.append_log(f'Preset salvo: {path}')

    def load_preset(self):
        path = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if not path:
            return
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)

        self.var_source.set(cfg.get('load_m3u_path', ''))
        self.var_output.set(cfg.get('dump_music_path', ''))
        self.var_fix.set(cfg.get('fix_search_path') or '')
        self.var_patterns.set(','.join(cfg.get('playlist_pattern_list', ['*.m3u', '*.m3u8'])))
        self.var_collision.set(cfg.get('collision_strategy', 'path-score'))
        self.var_linkmode.set(cfg.get('link_mode', 'copy'))
        self.var_report_json.set(cfg.get('report_json') or '')
        self.var_report_csv.set(cfg.get('report_csv') or '')
        self.var_skip_existing.set(bool(cfg.get('skip_existing', True)))
        self.var_with_playlist.set(bool(cfg.get('with_playlist', True)))
        self.var_dry_run.set(bool(cfg.get('dry_run', False)))
        self.append_log(f'Preset carregado: {path}')


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
