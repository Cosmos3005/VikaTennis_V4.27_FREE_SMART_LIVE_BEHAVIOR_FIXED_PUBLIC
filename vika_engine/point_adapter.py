from __future__ import annotations
import pandas as pd
import numpy as np

class PointByPointAdapter:
    """Normalize point-by-point CSVs into deep pre-match aggregates."""
    REQUIRED={"match_id","point_no","server","winner"}
    def load(self,path):
        df=pd.read_csv(path)
        missing=self.REQUIRED-set(df.columns)
        if missing: raise ValueError(f"Missing required columns: {sorted(missing)}")
        return df.sort_values(["match_id","point_no"])

    def aggregate_match(self, df):
        rows=[]
        for mid,g in df.groupby("match_id",sort=False):
            r={"match_id":mid,"points":len(g)}
            r["p1_point_win_rate"]=np.mean(g.winner.eq("p1"))
            r["p1_serve_point_win_rate"]=np.mean(g.loc[g.server.eq("p1"),"winner"].eq("p1")) if np.any(g.server.eq("p1")) else .5
            r["p2_serve_point_win_rate"]=np.mean(g.loc[g.server.eq("p2"),"winner"].eq("p2")) if np.any(g.server.eq("p2")) else .5
            for p in ("p1","p2"):
                sp=g[g.server.eq(p)]
                r[f"{p}_serve_pressure_loss_rate"]=np.mean(sp.winner.ne(p)) if len(sp) else .5
            # rolling momentum: longest win/loss streak in points.
            seq=g.winner.eq("p1").astype(int).to_numpy()
            best=cur=0
            for x in seq:
                if x: cur+=1; best=max(best,cur)
                else: cur=0
            r["p1_max_point_streak"]=best
            # pressure proxy when score columns exist.
            if "point_score" in g.columns:
                txt=g.point_score.astype(str)
                pressure=txt.str.contains(r"30-30|40-40|A-40|40-A|BP",case=False,regex=True)
                r["pressure_points"] = int(pressure.sum())
                if pressure.any(): r["p1_pressure_win_rate"]=np.mean(g.loc[pressure,"winner"].eq("p1"))
                else:r["p1_pressure_win_rate"]=.5
            else:r["pressure_points"]=0; r["p1_pressure_win_rate"]=.5
            rows.append(r)
        return pd.DataFrame(rows)
