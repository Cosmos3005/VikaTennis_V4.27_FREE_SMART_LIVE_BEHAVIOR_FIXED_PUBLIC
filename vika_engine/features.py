from __future__ import annotations
import pandas as pd
from .data import enrich_targets
from .ratings.player_state import PlayerStateStore

class FeatureBuilder:
    """Leakage-safe pre-match feature builder. Every feature is computed before the match."""
    def __init__(self): self.surface_map={'Hard':0,'Clay':1,'Grass':2,'Carpet':3}
    def _features(self, state, p1, p2, surface, best_of, date):
        s=state.snapshot(p1,p2,surface,date,best_of)
        if s is None: return None
        # Do not feed raw player IDs or post-match statistics to the model.
        s.pop('p1_name',None); s.pop('p2_name',None)
        return s
    def build(self, df):
        df=enrich_targets(df.copy()); df=df[df.valid_target].copy()
        df['match_date']=pd.to_datetime(df.tourney_date.astype(str).str.split('.').str[0],format='%Y%m%d',errors='coerce')
        sort_cols=['match_date'] + (['match_num'] if 'match_num' in df.columns else [])
        df=df.sort_values(sort_cols).reset_index(drop=True)
        state=PlayerStateStore(); rows=[]
        for i,r in enumerate(df.itertuples(index=False)):
            d=getattr(r,'match_date',None); surf=getattr(r,'surface','Hard') or 'Hard'; bo=int(getattr(r,'best_of',3) or 3)
            p1=getattr(r,'winner_name',''); p2=getattr(r,'loser_name','')
            if not p1 or not p2 or pd.isna(d): continue
            a=self._features(state,p1,p2,surf,bo,d); b=self._features(state,p2,p1,surf,bo,d)
            total=getattr(r,'total_games',0); diff=getattr(r,'games_diff',0)
            if a is not None:
                a.update(target_win=1,target_total=total,target_diff=diff,date=d,player1_id=str(getattr(r,'winner_id','')),player2_id=str(getattr(r,'loser_id',''))); rows.append(a)
            if b is not None:
                b.update(target_win=0,target_total=total,target_diff=-diff,date=d,player1_id=str(getattr(r,'loser_id','')),player2_id=str(getattr(r,'winner_id',''))); rows.append(b)
            state._update_row(r)
            if i and i%50000==0: print(f'processed {i:,}/{len(df):,}', flush=True)
        return pd.DataFrame(rows)

    def build_state(self,df,through=None):
        state=PlayerStateStore(); state.ingest(df,through=through); return state
