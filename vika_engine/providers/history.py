from __future__ import annotations

import os
import time
import requests

BASE = 'https://api.livetennisapi.com/api/public/v1'


class LiveTennisHistoryProvider:
    """Official Live Tennis API history client with pagination and rate-limit handling."""
    def __init__(self, api_key=None, base_url=BASE, timeout=60):
        self.api_key = api_key or os.getenv('LIVETENNISAPI_KEY')
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    @property
    def available(self):
        return bool(self.api_key)

    def _get(self, path, params=None, stream=False):
        if not self.api_key:
            raise RuntimeError('LIVETENNISAPI_KEY is not configured')
        for attempt in range(5):
            r = requests.get(self.base_url + path,
                             headers={'Authorization': f'Bearer {self.api_key}'},
                             params=params or {}, timeout=self.timeout, stream=stream)
            if r.status_code == 429:
                retry = int(r.headers.get('Retry-After', '5') or 5)
                time.sleep(min(max(retry, 2), 120))
                continue
            if r.status_code in (401, 403):
                raise RuntimeError(f'Live Tennis API {r.status_code}: check key and history entitlement')
            r.raise_for_status()
            return r
        raise RuntimeError('Live Tennis API rate limit did not clear')

    def history_tape(self, match_id, complete=False):
        params = {'points': 'complete'} if complete else None
        return self._get(f'/history/matches/{match_id}', params).json()

    def history_matches(self, **params):
        return self._get('/history/matches', params).json()

    def iter_history_matches(self, start, end, tour=None, limit=200):
        offset = 0
        while True:
            params = {'from': str(start), 'to': str(end), 'limit': int(limit), 'offset': offset}
            if tour:
                params['tour'] = tour
            payload = self.history_matches(**params)
            items = payload.get('data', []) if isinstance(payload, dict) else payload
            if not items:
                break
            for item in items:
                yield item
            meta = payload.get('meta', {}) if isinstance(payload, dict) else {}
            if not meta.get('has_more', False) and len(items) < limit:
                break
            offset += len(items)

    def coverage(self):
        return self._get('/history/coverage').json()
