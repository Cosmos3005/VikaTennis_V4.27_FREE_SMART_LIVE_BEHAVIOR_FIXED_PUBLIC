from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, math
import pandas as pd
from .models import VikaModels
from .simulator import MatchSimulator
from .ratings.player_state import PlayerStateStore
from .calibration import confidence
from .live.model import LiveWinModel
from .live.monte_carlo import LiveMonteCarlo
from .live.ml import LiveMLAdapterV47
from .paths import root_path
from .point_simulator import simulate_match as simulate_point_match

class HistoricalPlayerMissingError(ValueError):
    def __init__(self, players):
        self.players=tuple(players)
        super().__init__('Игрок не найден в исторической базе: '+', '.join(self.players))

class PredictionEngine:
    def __init__(self, model_path='models/vika_models_v42.joblib', state_path=None):
        self.model_path=str(root_path(model_path))
        self.state_path=str(root_path(state_path)) if state_path else str(next((p for p in ('models/player_state_v422.json','models/player_state_v414.json','models/player_state_v4.json') if root_path(p).exists()), 'models/player_state_v4.json'))
        self.models=VikaModels.load(model_path); self.state=PlayerStateStore.load(self.state_path); self.sim=MatchSimulator(seed=42); self.live_sim=LiveMonteCarlo(seed=20260908)
        live_candidates=(str(root_path('models/vika_live_v417.joblib')),str(root_path('models/vika_live_v416.joblib')),str(root_path('models/vika_live_v47.joblib')))
        self.live_model_path=next((p for p in live_candidates if Path(p).exists()), live_candidates[-1])
        self.live_ml=LiveMLAdapterV47(self.live_model_path)
    def predict(self,p1,p2,surface='Hard',best_of=3,odds1=None,odds2=None,simulations=100000):
        snap=self.state.snapshot(p1,p2,surface,pd.Timestamp.utcnow().tz_localize(None),best_of)
        if snap is None:
            missing=[name for name in (p1,p2) if self.state.get(name) is None]
            raise HistoricalPlayerMissingError(missing or (p1,p2))
        X=pd.DataFrame([snap])
        # Map the live/player-state vocabulary to the v4.2 training vocabulary.
        aliases={
            'p1_service':'p1_serve','p2_service':'p2_serve','service_diff':'serve_diff',
            'p1_return':'p1_return','p2_return':'p2_return','return_diff':'return_diff',
            'p1_fatigue':'p1_minutes30','p2_fatigue':'p2_minutes30','fatigue_diff':'minutes30_diff',
            'p1_matches_30d':'p1_matches30','p2_matches_30d':'p2_matches30','matches30_diff':'matches30_diff',
            'p1_sets_30d':'p1_sets30','p2_sets_30d':'p2_sets30','sets30_diff':'sets30_diff',
            'p1_surface_elo':'p1_elo','p2_surface_elo':'p2_elo','surface_elo_diff':'elo_diff',
        }
        for src,dst in aliases.items():
            if src in X.columns and dst not in X.columns: X[dst]=X[src]
        out=self.models.predict(X)
        sim=self.sim.simulate(out['p1_win'],best_of=best_of,n=simulations)
        out['simulation']={k:v for k,v in sim.items() if k not in ('total_samples','diff_samples')}
        # Point-level Monte Carlo is an additional layer when historical service evidence is available.
        # It does not replace the calibrated winner model.
        ps1=float(snap.get('p1_service',0) or 0); ps2=float(snap.get('p2_service',0) or 0)
        if ps1 > 0 and ps2 > 0:
            point_mc=simulate_point_match(ps1,ps2,float(snap.get('p1_return',0) or 0),float(snap.get('p2_return',0) or 0),best_of=best_of,simulations=min(int(simulations),20000),seed=20260909)
            out['point_simulation']=point_mc
            out['simulation']['point_model_available']=True
        else:
            out['point_simulation']=None
            out['simulation']['point_model_available']=False
        out['data_quality']=self._quality(snap)
        out['confidence_score']=round(abs(out['p1_win']-.5)*2,3)
        out['confidence']=confidence(out['p1_win'],out['data_quality'],(snap.get('p1_rd',350)+snap.get('p2_rd',350))/700)
        out['timestamp']=datetime.now(timezone.utc).isoformat(); out['model_version']=getattr(self.models,'version','v4'); out['features']=snap
        out['live_prior']=out['p1_win']
        if odds1 and odds2:
            from .value import ValueEngine
            out['value']=ValueEngine().evaluate(out['p1_win'],float(odds1),float(odds2))
        return out

    def update_live(self, pre_match_result, frame):
        model=LiveWinModel(pre_match_result['p1_win'])
        lf=model.from_frame(pre_match_result['p1_win'], frame)
        live=model.predict(lf)
        # V4.7 historical ML is optional. If the trained artifact is present it becomes
        # the primary live estimator; otherwise the fully-tested V4.5 live model remains
        # the automatic fallback.
        ml_p=self.live_ml.predict(pre_match_result['p1_win'], frame)
        if ml_p is not None:
            live['p1_win_ml_v47']=ml_p
            live['p1_win_hand']=live['p1_win']
            live['p1_win']=0.70*ml_p+0.30*float(live['p1_win'])
            live['p2_win']=1-live['p1_win']
            live['model_version']=getattr(self.models,'version','v4.2')+'+'+Path(self.live_model_path).stem
        else:
            live['model_version']=getattr(self.models,'version','v4.2')+'+live-v4.5-fallback'
        # Simulate only the remainder of the current match. The live model remains
        # the probability estimator; MC is an independent state-consistency layer.
        live_mc=self.live_sim.simulate(
            prior=pre_match_result['p1_win'],
            live_features=lf,
            momentum_pressure=float(live.get('momentum',{}).get('pressure',0.0)),
            simulations=100000,
            best_of=int(pre_match_result.get('best_of',3)),
        )
        # Blend conservatively: live model 70%, remainder-MC 30%. If the API supplies
        # an official live probability, LiveWinModel already accounts for it.
        blended=0.70*float(live['p1_win'])+0.30*float(live_mc['p1_win'])
        live['p1_win']=max(.001,min(.999,blended)); live['p2_win']=1-live['p1_win']
        live['live_monte_carlo']=live_mc
        live['match_id']=(frame.get('match_id') if isinstance(frame,dict) else getattr(frame,'match_id',''))
        live['p1']=pre_match_result.get('p1',pre_match_result.get('features',{}).get('p1_name','P1'))
        live['p2']=pre_match_result.get('p2',pre_match_result.get('features',{}).get('p2_name','P2'))
        live['timestamp']=datetime.now(timezone.utc).isoformat()
        return live

    @staticmethod
    def _confidence(s,p):
        base=abs(p-.5)*2; q=min(1,(s.get('p1_wins',0)+s.get('p1_losses',0)+s.get('p2_wins',0)+s.get('p2_losses',0))/100); return round(.7*base+.3*q,3)
    @staticmethod
    def _quality(s):
        counts=s.get('p1_wins',0)+s.get('p1_losses',0)+s.get('p2_wins',0)+s.get('p2_losses',0); rd=(s.get('p1_rd',350)+s.get('p2_rd',350))/2; return round(min(1,.45*min(1,counts/120)+.55*max(0,1-rd/400)),3)
