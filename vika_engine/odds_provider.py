from __future__ import annotations
import os, time, logging, re
from difflib import SequenceMatcher
import requests

log = logging.getLogger('vika.odds')

class OddsProvider:
    """Real-time multi-market odds adapter.

    Primary adapter: The Odds API v4. It supplies live/upcoming tennis
    h2h, spreads and totals when those markets are available from books.
    No odds are ever fabricated here.
    """
    def __init__(self):
        self.key = os.getenv('THE_ODDS_API_KEY', '').strip()
        self.base = os.getenv('THE_ODDS_API_BASE', 'https://api.the-odds-api.com/v4').rstrip('/')
        self.sport = os.getenv('THE_ODDS_API_SPORT', 'tennis').strip()
        self.regions = os.getenv('THE_ODDS_API_REGIONS', 'eu').strip()
        self.markets = os.getenv('THE_ODDS_API_MARKETS', 'h2h,spreads,totals').strip()
        self.ttl = max(5, int(os.getenv('ODDS_CACHE_SECONDS', '20')))
        self.timeout = max(5, int(os.getenv('ODDS_HTTP_TIMEOUT', '12')))
        self._cache = (0.0, [])
        self.last_error = ''
        self.last_ok = 0.0

    @property
    def available(self) -> bool:
        return bool(self.key)

    def live(self):
        if not self.available:
            return []
        now = time.time()
        if now - self._cache[0] < self.ttl:
            return self._cache[1]
        url = f'{self.base}/sports/{self.sport}/odds/'
        params = {
            'apiKey': self.key,
            'regions': self.regions,
            'markets': self.markets,
            'oddsFormat': 'decimal',
            'dateFormat': 'iso',
        }
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise ValueError('odds API returned non-list payload')
            self._cache = (now, data)
            self.last_ok = now
            self.last_error = ''
            return data
        except Exception as e:
            self.last_error = str(e)
            log.warning('The Odds API request failed: %s', e)
            # Keep the last successful cache briefly rather than breaking the bot.
            if self._cache[1] and now - self._cache[0] < max(self.ttl * 5, 120):
                return self._cache[1]
            return []

    @staticmethod
    def _norm(s):
        s = str(s or '').lower()
        s = re.sub(r'[^a-z0-9а-яё ]', ' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    @classmethod
    def _sim(cls, a, b):
        a, b = cls._norm(a), cls._norm(b)
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        if a in b or b in a:
            return 0.94
        return SequenceMatcher(None, a, b).ratio()

    def for_match(self, p1, p2):
        """Return the best live event matching both players, order-independent."""
        a, b = self._norm(p1), self._norm(p2)
        best, best_score = None, 0.0
        for e in self.live():
            h, aw = e.get('home_team'), e.get('away_team')
            if not h or not aw:
                continue
            direct = (self._sim(a, h) + self._sim(b, aw)) / 2
            reverse = (self._sim(a, aw) + self._sim(b, h)) / 2
            score = max(direct, reverse)
            if score > best_score:
                best_score, best = score, e
        # 0.82 is intentionally strict: never attach another match's odds.
        return best if best_score >= 0.82 else None

    @staticmethod
    def _decimal(price):
        try:
            x = float(price)
            return x if 1.01 <= x <= 100 else None
        except Exception:
            return None

    def markets(self, p1, p2):
        e = self.for_match(p1, p2)
        if not e:
            return []
        rows = []
        for book in e.get('bookmakers', []) or []:
            for m in book.get('markets', []) or []:
                mkey = m.get('key')
                if mkey not in ('h2h', 'spreads', 'totals'):
                    continue
                for o in m.get('outcomes', []) or []:
                    price = self._decimal(o.get('price'))
                    if price is None:
                        continue
                    rows.append({
                        'bookmaker': book.get('title') or book.get('key') or 'Book',
                        'bookmaker_key': book.get('key'),
                        'market': mkey,
                        'name': o.get('name'),
                        'point': o.get('point'),
                        'price': price,
                    })
        return rows

    def status(self):
        return {
            'configured': self.available,
            'last_ok': self.last_ok,
            'last_error': self.last_error,
            'regions': self.regions,
            'markets': self.markets,
            'sport': self.sport,
        }
