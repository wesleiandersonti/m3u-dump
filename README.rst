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

Exemplo com múltiplos padrões + relatório JSON:

.. code-block:: bash

  m3u-dump ./playlists ./out \
    --playlist-pattern-list "*.m3u" \
    --playlist-pattern-list "*.m3u8" \
    --collision-strategy path-score \
    --report-json ./report.json

DESENVOLVIMENTO
---------------

.. code-block:: bash

  python -m venv .venv
  . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
  pip install -r requirements_dev.txt
  pytest

Requer Python 3.10+.
