===============================
m3u-dump
===============================

CLI para copiar músicas listadas em playlists ``.m3u/.m3u8`` e gerar playlist corrigida.

USO RÁPIDO
----------

.. code-block:: bash

  pip install .
  m3u-dump ~/music/playlist.m3u ~/android-music-sync-dir --fix-search-path ~/music

OPÇÕES IMPORTANTES
------------------

- ``--dry-run``: simula sem copiar arquivos
- ``--with-playlist / --no-with-playlist``: grava (ou não) a playlist corrigida no destino
- ``--fix-search-path <dir>``: tenta corrigir caminhos quebrados por basename
- ``--playlist-pattern-list <glob>``: pode repetir para múltiplos padrões
- ``--collision-strategy [first|shortest|path-score]``: resolve arquivos com mesmo nome em múltiplas pastas
- ``--report-json <arquivo.json>``: gera relatório da execução
- ``--report-csv <arquivo.csv>``: exporta detalhes da execução em CSV
- ``--origin-links-file <arquivo.csv>``: salva URL original, URL final e servidor de origem
- ``--resolve-url-final / --no-resolve-url-final``: resolve redirecionamentos antes de salvar
- ``--skip-existing / --no-skip-existing``: pula arquivos já existentes no destino
- ``--link-mode [copy|hardlink|symlink]``: modo de materialização no destino

Exemplo com múltiplos padrões + relatórios + origem dos links:

.. code-block:: bash

  m3u-dump ./playlists ./out \
    --playlist-pattern-list "*.m3u" \
    --playlist-pattern-list "*.m3u8" \
    --collision-strategy path-score \
    --skip-existing \
    --link-mode hardlink \
    --report-json ./report.json \
    --report-csv ./report.csv \
    --origin-links-file ./origens.csv

APP WINDOWS (GUI)
-----------------

Rodar interface gráfica:

.. code-block:: bash

  m3u-dump-gui

Atualizador integrado (GUI):
- botão ``Verificar atualização``
- consulta ``update.json`` no GitHub
- abre o link do instalador mais recente

Build EXE no Windows:

.. code-block:: powershell

  .\build_windows.ps1

Saída esperada:
- ``dist\\m3u-dump-pro.exe``

Gerar instalador (Inno Setup):

1. Instale o Inno Setup no Windows
2. Abra o script:
   ``installer\\m3u-dump-pro.iss``
3. Compile (Build)

Saída esperada do instalador:
- ``installer\\m3u-dump-pro-installer.exe``

Build automático no GitHub (instalador final)
-------------------------------------------

Este repositório já está configurado para gerar o instalador final via GitHub Actions:

- workflow: ``.github/workflows/windows-installer.yml``
- gera:
  - ``m3u-dump-pro.exe``
  - ``m3u-dump-pro-installer.exe``

Como disparar:

1. Crie e envie uma tag (exemplo ``v1.1.1``)
2. O workflow roda no Windows e publica os arquivos na Release da tag

.. code-block:: bash

  git tag v1.1.1
  git push origin v1.1.1

DESENVOLVIMENTO
---------------

.. code-block:: bash

  python -m venv .venv
  . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
  pip install -r requirements_dev.txt
  pytest

Requer Python 3.10+.
