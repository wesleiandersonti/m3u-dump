# -*- coding: utf-8 -*-
import json
from urllib.request import urlopen

UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/wesleiandersonti/m3u-dump/master/update.json"


def _normalize(v: str):
    v = (v or '').strip().lower().replace('v', '')
    parts = []
    for p in v.split('.'):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update(current_version: str, timeout: int = 6):
    try:
        with urlopen(UPDATE_MANIFEST_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))

        remote_version = str(data.get('version', '')).strip()
        has_update = _normalize(remote_version) > _normalize(current_version)

        return {
            'ok': True,
            'has_update': has_update,
            'current_version': current_version,
            'remote_version': remote_version,
            'release_url': data.get('release_url', ''),
            'installer_url': data.get('installer_url', ''),
            'notes': data.get('notes', ''),
        }
    except Exception as exc:
        return {
            'ok': False,
            'error': str(exc),
            'has_update': False,
            'current_version': current_version,
        }
