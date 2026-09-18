from __future__ import annotations
import os, time, threading, logging
from datetime import datetime, timezone

log = logging.getLogger('vika.livetennis')

class LiveTennisProvider:
    """Live Tennis API adapter with free-tier-aware caching and quota control.

    Free tier strategy:
      * one /matches?status=live request contains the current live board;
      * avoid per-match /score calls unless explicitly needed;
      * keep a small daily reserve for manual commands;
      * usage checks are quota-exempt according to the API docs.
    """
    FREE_DAILY_LIMIT = int(os.getenv('LIVETENNIS_FREE_DAILY_LIMIT', '100'))
    AUTO_DAILY_BUDGET = int(os.getenv('LIVETENNIS_AUTO_DAILY_BUDGET', '80'))
    MANUAL_RESERVE = int(os.getenv('LIVETENNIS_MANUAL_RESERVE', '10'))
    LIVE_CACHE_SECONDS = int(os.getenv('LIVETENNIS_LIVE_CACHE_SECONDS', '30'))
    DAY_CACHE_SECONDS = int(os.getenv('LIVETENNIS_DAY_CACHE_SECONDS', '300'))

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('LIVETENNISAPI_KEY') or os.getenv('LIVE_TENNIS_API_KEY')
        self.client = None
        self.last_error = ''
        self._live_cache = (0.0, [])
        self._day_cache = (0.0, [])
        self._usage_cache = (0.0, None)
        self._lock = threading.Lock()
        self._local_auto_calls = 0
        self._local_day = datetime.now(timezone.utc).date()
        if self.api_key:
            try:
                from livetennisapi import LiveTennisAPI
                self.client = LiveTennisAPI(api_key=self.api_key)
            except Exception as exc:
                self.last_error = str(exc)
                self.client = None

    @property
    def available(self):
        return self.client is not None

    def _reset_local_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self._local_day:
            self._local_day = today
            self._local_auto_calls = 0
            self._usage_cache = (0.0, None)

    def _usage_from_client(self):
        """Best-effort quota-exempt usage lookup using SDK or direct REST.

        The documented endpoint is GET /usage with Bearer auth, but older SDK
        builds and compatible gateways may return the payload under a `data`
        wrapper. Accept both shapes and retry once with X-API-Key as a fallback.
        """
        if not self.api_key:
            return None
        now = time.time()
        if now - self._usage_cache[0] < 120:
            return self._usage_cache[1]

        data = None

        # Prefer the SDK method when it exists.
        try:
            fn = getattr(self.client, 'usage', None) or getattr(self.client, 'get_usage', None)
            if fn:
                data = fn()
        except Exception as exc:
            log.debug('Live Tennis SDK usage() failed: %s', exc)

        # Direct REST fallback. Both auth headers are accepted by the API; Bearer
        # is the documented form for /usage.
        if data is None:
            try:
                import requests
                url = 'https://api.livetennisapi.com/api/public/v1/usage'
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Accept': 'application/json',
                }
                r = requests.get(url, headers=headers, timeout=8)
                if r.ok:
                    data = r.json()
                else:
                    self.last_error = f'usage HTTP {r.status_code}'
                    if r.status_code in (400, 401):
                        # Compatibility fallback for gateways/SDK generations
                        # that still expect the equivalent API-key header.
                        r2 = requests.get(
                            url,
                            headers={'X-API-Key': self.api_key, 'Accept': 'application/json'},
                            timeout=8,
                        )
                        if r2.ok:
                            data = r2.json()
                            self.last_error = ''
                        else:
                            self.last_error = f'usage HTTP {r.status_code}/{r2.status_code}'
            except Exception as exc:
                log.debug('direct usage request failed: %s', exc)
                data = None

        # Some clients return {data: {...}} while the current API reference
        # documents the payload at the root. Normalize the wrapper here.
        if isinstance(data, dict) and isinstance(data.get('data'), dict):
            wrapped = data['data']
            if any(k in wrapped for k in ('today', 'limits', 'tier', 'base_tier')):
                data = wrapped

        self._usage_cache = (now, data)
        return data

    def quota(self, refresh=False):
        """Return current daily quota without consuming it."""
        self._reset_local_day()
        if refresh:
            self._usage_cache = (0.0, None)
        data = self._usage_from_client()
        calls = remaining = None
        tier = None
        as_of = None
        if isinstance(data, dict):
            tier = data.get('tier') or data.get('base_tier')
            today = data.get('today') or {}
            limits = data.get('limits') or {}
            calls = today.get('calls')
            remaining = today.get('remaining_day')
            # Current API docs may return limits.per_day while today.remaining_day is null.
            limit_from_api = limits.get('per_day')
            if limit_from_api is not None:
                try:
                    self.FREE_DAILY_LIMIT = int(limit_from_api)
                except Exception:
                    pass
            as_of = data.get('as_of')
            if remaining is None and calls is not None and self.FREE_DAILY_LIMIT:
                remaining = max(0, self.FREE_DAILY_LIMIT - int(calls))
        if calls is None:
            calls = None
        if remaining is None:
            remaining = None
        return {
            'tier': tier or 'unknown',
            'limit_per_day': self.FREE_DAILY_LIMIT,
            'calls': calls,
            'remaining': remaining,
            'auto_calls_local': self._local_auto_calls,
            'auto_budget': self.AUTO_DAILY_BUDGET,
            'manual_reserve': self.MANUAL_RESERVE,
            'as_of': as_of,
        }

    def _can_auto_call(self):
        q = self.quota()
        if self._local_auto_calls >= self.AUTO_DAILY_BUDGET:
            return False
        if q['remaining'] is not None:
            return int(q['remaining']) > self.MANUAL_RESERVE
        return True

    def mark_auto_call(self):
        self._reset_local_day()
        self._local_auto_calls += 1

    def seconds_until_utc_midnight(self):
        now = datetime.now(timezone.utc)
        midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp() + 86400
        return max(60, midnight - now.timestamp())

    def suggested_auto_interval(self):
        """Compute a quota-safe adaptive interval for the automatic live loop."""
        q = self.quota()
        if q['remaining'] is not None:
            available = max(0, int(q['remaining']) - self.MANUAL_RESERVE)
            available = min(available, max(0, self.AUTO_DAILY_BUDGET - self._local_auto_calls))
        else:
            available = max(1, self.AUTO_DAILY_BUDGET - self._local_auto_calls)
        if available <= 0:
            return None
        # Spread the remaining automatic budget evenly until UTC midnight.
        sec = self.seconds_until_utc_midnight()
        base = sec / available
        # Keep the loop sane even if a key has just reset or usage data is unavailable.
        return max(300, min(1800, int(base)))

    def _list_matches(self, **kw):
        if not self.client:
            return []
        try:
            return list(self.client.list_matches(**kw))
        except Exception as exc:
            self.last_error = str(exc)
            raise

    def live_matches(self, force=False, auto=False):
        if not self.client:
            return []
        now = time.time()
        with self._lock:
            ts, rows = self._live_cache
            if not force and now - ts < self.LIVE_CACHE_SECONDS:
                return list(rows)
            if auto and not self._can_auto_call():
                return list(rows)
            try:
                rows = self._list_matches(status='live')
                self._live_cache = (now, list(rows))
                self.last_error = ''
                if auto:
                    self.mark_auto_call()
                return list(rows)
            except Exception as exc:
                self.last_error = str(exc)
                log.warning('live_matches failed: %s', exc)
                return list(rows)

    def upcoming_matches(self, tour=None, draw='singles', force=False):
        if not self.client:
            return []
        now = time.time()
        cache_key = 'day' if (tour is None and draw == 'singles') else f'{tour}|{draw}'
        if cache_key == 'day' and not force and now - self._day_cache[0] < self.DAY_CACHE_SECONDS:
            return list(self._day_cache[1])
        kw = {'status': 'upcoming'}
        if tour:
            kw['tour'] = tour
        if draw:
            kw['draw'] = draw
        try:
            rows = self._list_matches(**kw)
        except TypeError:
            kw.pop('draw', None)
            try:
                rows = self._list_matches(**kw)
                rows = [m for m in rows if str(getattr(m, 'draw', '') or '').lower() in ('singles', '')]
            except Exception as exc:
                self.last_error = str(exc)
                return []
        except Exception as exc:
            self.last_error = str(exc)
            return []
        if cache_key == 'day':
            self._day_cache = (now, list(rows))
        self.last_error = ''
        return list(rows)

    def current_day(self, force=False):
        return self.upcoming_matches(draw='singles', force=force)

    def search_players(self, name):
        if not self.client or not hasattr(self.client, 'search_players'):
            return []
        try:
            return list(self.client.search_players(search=name))
        except TypeError:
            try: return list(self.client.paginate('search_players', search=name))
            except Exception: return []
        except Exception: return []

    def get_player(self, player_id):
        if not self.client or not hasattr(self.client, 'get_player'): return None
        try: return self.client.get_player(player_id)
        except Exception: return None

    def get_match(self, match_id):
        if not self.client: return None
        try: return self.client.get_match(match_id)
        except Exception: return None

    def h2h(self, p1, p2):
        if not self.client: return []
        return list(self.client.get_h2h(p1, p2)) if hasattr(self.client, 'get_h2h') else []

    def point_page(self, match_id, after_seq=0):
        if not self.client: return {'points': [], 'last_seq': int(after_seq or 0), 'has_more': False}
        fn = getattr(self.client, 'get_match_points', None) or getattr(self.client, 'list_match_points', None)
        if not fn: return {'points': [], 'last_seq': int(after_seq or 0), 'has_more': False}
        try: return fn(match_id, after_seq=after_seq)
        except TypeError: return {'points': list(fn(match_id)), 'last_seq': 0, 'has_more': False}

    def points(self, match_id, after_seq=None):
        if not self.client: return []
        fn = getattr(self.client, 'get_match_points', None) or getattr(self.client, 'list_match_points', None)
        if not fn: return []
        try: return list(fn(match_id, after_seq=after_seq)) if after_seq is not None else list(fn(match_id))
        except TypeError: return list(fn(match_id))

    def stats(self, match_id):
        if not self.client: return None
        for name in ('get_match_stats','get_match_statistics','match_stats','get_live_stats'):
            fn = getattr(self.client, name, None)
            if fn:
                try: return fn(match_id)
                except Exception: pass
        return None
