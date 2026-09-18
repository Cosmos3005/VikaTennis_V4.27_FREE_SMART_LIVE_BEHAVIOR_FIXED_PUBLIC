from __future__ import annotations
import math
from dataclasses import dataclass

SCALE = 173.7178
Q = math.log(10) / 400.0

@dataclass
class Glicko2Rating:
    rating: float = 1500.0
    rd: float = 350.0
    volatility: float = 0.06

    @property
    def mu(self): return (self.rating - 1500.0) / SCALE
    @property
    def phi(self): return self.rd / SCALE

    def _g(self, phi):
        return 1.0 / math.sqrt(1.0 + 3.0 * Q * Q * phi * phi / (math.pi * math.pi))

    def _E(self, mu, mu_j, phi_j):
        g = self._g(phi_j)
        z = g * (mu - mu_j)
        return 1.0 / (1.0 + math.exp(-z))

    def update(self, opponent: 'Glicko2Rating', score: float, tau: float = 0.5):
        # Fast online Glicko-2 update. Volatility is allowed to move modestly
        # without running the expensive full rating-period root finder.
        mu, phi = self.mu, self.phi
        mu_j, phi_j = opponent.mu, opponent.phi
        g = self._g(phi_j); E = self._E(mu, mu_j, phi_j)
        v = 1.0 / max(1e-12, g*g*E*(1-E))
        delta = v*g*(score-E)
        sigma2 = max(0.01**2, min(0.15**2, self.volatility**2 + 0.0025*abs(delta)))
        phi_star = math.sqrt(phi*phi + sigma2)
        phi_p = 1.0 / math.sqrt(1.0/(phi_star*phi_star) + 1.0/v)
        mu_p = mu + phi_p*phi_p*g*(score-E)
        self.rating = 1500.0 + SCALE*mu_p
        self.rd = max(30.0, min(350.0, SCALE*phi_p))
        self.volatility = math.sqrt(sigma2)
        return self

    def expected(self, opponent: 'Glicko2Rating') -> float:
        return self._E(self.mu, opponent.mu, opponent.phi)
