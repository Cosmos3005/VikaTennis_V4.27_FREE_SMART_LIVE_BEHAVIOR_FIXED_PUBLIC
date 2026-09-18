from __future__ import annotations
from pathlib import Path
import pandas as pd
from .features import FeatureBuilder
from .models import VikaModels
from .simulator import MatchSimulator

class VikaEngine:
    def __init__(self, model_path="models/vika_models.joblib"):
        self.model_path=model_path; self.models=None; self.builder=None; self.sim=MatchSimulator()

    def train(self, raw_df):
        self.builder=FeatureBuilder(); ds=self.builder.build(raw_df)
        dates=sorted(ds.date.dropna().unique())
        n=len(dates)
        if n<20: raise ValueError("Need at least ~20 distinct dates for chronological validation.")
        cut1=dates[int(n*.70)]; cut2=dates[int(n*.85)]
        train=ds[ds.date<=cut1]; valid=ds[(ds.date>cut1)&(ds.date<=cut2)]; test=ds[ds.date>cut2]
        self.models=VikaModels(); metrics=self.models.fit(train,valid,test); self.models.save(self.model_path)
        return {"rows":len(ds),"features":len(self.models.feature_columns),"train":len(train),"valid":len(valid),"test":len(test),"metrics":metrics}

    def load(self): self.models=VikaModels.load(self.model_path); return self

    def _synthetic_row(self,p1,p2,surface,best_of):
        # Prediction CLI needs a live feature source. This row maps names to zero-history priors.
        # Production bot should use a PlayerProfile/feature-store adapter; do not silently invent player stats.
        return {"winner_id":p1,"loser_id":p2,"tourney_date":pd.Timestamp.utcnow().normalize(),"surface":surface,"tourney_level":"G" if best_of==5 else "A"}

    def predict_from_features(self, features):
        if self.models is None:self.load()
        out=self.models.predict(pd.DataFrame([features]))
        sim=self.sim.simulate(out["p1_win"],best_of=int(features.get("best_of",3)),n=50000)
        over_sim,cover_sim=self.sim.line_probs(sim)
        out["simulation"]={k:v for k,v in sim.items() if k not in ("total_samples","diff_samples")}
        out["simulation"]["over"]=over_sim; out["simulation"]["cover"]=cover_sim
        return out
