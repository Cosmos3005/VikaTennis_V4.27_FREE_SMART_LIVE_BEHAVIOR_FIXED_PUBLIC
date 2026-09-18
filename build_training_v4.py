import argparse,pandas as pd,numpy as np
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--source",default="data/all_matches_2015_2025.csv");p.add_argument("--extra",default="");p.add_argument("--out",default="data/v4_features.csv");a=p.parse_args()
cols=["tourney_date","surface","winner_id","winner_name","winner_rank","winner_age","winner_ht","winner_hand","loser_id","loser_name","loser_rank","loser_age","loser_ht","loser_hand","score","best_of","round","minutes","w_svpt","w_1stWon","w_2ndWon","l_svpt","l_1stWon","l_2ndWon","match_num","tour"]
df=pd.read_csv(a.source,usecols=cols,low_memory=False);df=df[df.tour.astype(str).str.lower().eq("atp")].copy()
if a.extra:
 try:
  ex=pd.read_csv(a.extra,usecols=[c for c in cols if c!="tour"],low_memory=False);ex["tour"]="atp";df=pd.concat([df,ex],ignore_index=True)
 except FileNotFoundError:pass
def dt(v):
 try:return pd.to_datetime(str(v).split(".")[0],format="%Y%m%d")
 except:return pd.NaT
def score(s):
 t=d=sets=0
 for z in str(s or "").split():
  if "-" not in z:continue
  try:x,y=map(int,z.split("(")[0].split("-")[:2]);t+=x+y;d+=x-y;sets+=1
  except:pass
 return t,d,sets
df["date"]=df.tourney_date.map(dt);df=df[df.date.notna() & (df.date.dt.year>=2022)].sort_values(["date","match_num"]).reset_index(drop=True)
ss=df.score.map(score);df["target_total"]=[x[0] for x in ss];df["target_diff"]=[x[1] for x in ss];df=df[df.target_total>0].copy();df["surface_code"]=df.surface.map({"Hard":0,"Clay":1,"Grass":2,"Carpet":3}).fillna(0);df["round_code"]=df["round"].map({"R128":1,"R64":2,"R32":3,"R16":4,"QF":5,"SF":6,"F":7}).fillna(3);df["best_of"]=pd.to_numeric(df.best_of,errors="coerce").fillna(3)
w=pd.DataFrame({"date":df.date,"idx":df.index,"player":df.winner_name,"surface":df.surface.fillna("Hard"),"win":1,"rank":df.winner_rank,"age":df.winner_age,"ht":df.winner_ht,"hand":(df.winner_hand=="L").astype(int),"svpt":df.w_svpt.fillna(0),"serve_won":df.w_1stWon.fillna(0)+df.w_2ndWon.fillna(0),"opp_rank":df.loser_rank,"minutes":df.minutes.fillna(0),"sets":df.score.str.count(r"\d+-\d+")})
l=pd.DataFrame({"date":df.date,"idx":df.index,"player":df.loser_name,"surface":df.surface.fillna("Hard"),"win":0,"rank":df.loser_rank,"age":df.loser_age,"ht":df.loser_ht,"hand":(df.loser_hand=="L").astype(int),"svpt":df.l_svpt.fillna(0),"serve_won":df.l_1stWon.fillna(0)+df.l_2ndWon.fillna(0),"opp_rank":df.winner_rank,"minutes":df.minutes.fillna(0),"sets":df.score.str.count(r"\d+-\d+")})
long=pd.concat([w,l],ignore_index=True).sort_values(["player","date","idx"]).reset_index(drop=True);g=long.groupby("player",sort=False)
long["matches_before"]=g.cumcount();long["wins_before"]=g.win.cumsum()-long.win;long["winrate_before"]=long.wins_before/long.matches_before.replace(0,np.nan);long["serve_points_before"]=g.svpt.cumsum()-long.svpt;long["serve_won_before"]=g.serve_won.cumsum()-long.serve_won;long["serve_rate_before"]=long.serve_won_before/long.serve_points_before.replace(0,np.nan)
long["form5"]=g.win.transform(lambda s:s.shift(1).rolling(5,min_periods=1).mean());long["form10"]=g.win.transform(lambda s:s.shift(1).rolling(10,min_periods=1).mean());long["form20"]=g.win.transform(lambda s:s.shift(1).rolling(20,min_periods=1).mean());long["surface_form"]=long.groupby(["player","surface"]).win.transform(lambda s:s.shift(1).rolling(10,min_periods=1).mean());long["opp_quality"]=g.opp_rank.transform(lambda s:s.shift(1).rolling(20,min_periods=1).mean())
# Fast workload proxies from the previous 10/20 matches. The live state engine uses exact calendar windows.
long["minutes30"]=g.minutes.transform(lambda s:s.shift(1).rolling(10,min_periods=1).sum())
long["matches30"]=g.win.transform(lambda s:s.shift(1).rolling(10,min_periods=1).count())
long["sets30"]=g.sets.transform(lambda s:s.shift(1).rolling(10,min_periods=1).sum())
long["elo_seed"]=np.clip(2500-(long["rank"].fillna(999)-1)*.55,1200,2300);long["glicko_seed"]=long.elo_seed;long["rd_seed"]=np.clip(80+long.matches_before.pow(-0.5).fillna(1)*170,80,350)
key=long[["idx","player","rank","age","ht","hand","elo_seed","glicko_seed","rd_seed","winrate_before","serve_rate_before","form5","form10","form20","surface_form","opp_quality","minutes30","matches30","sets30"]]
wa=key.rename(columns={"player":"winner_name","rank":"p1_rank","age":"p1_age","ht":"p1_ht","hand":"p1_hand","elo_seed":"p1_elo","glicko_seed":"p1_glicko","rd_seed":"p1_rd","winrate_before":"p1_winrate","serve_rate_before":"p1_serve","form5":"p1_form5","form10":"p1_form10","form20":"p1_form20","surface_form":"p1_surface_form","opp_quality":"p1_opp_quality","minutes30":"p1_minutes30","matches30":"p1_matches30","sets30":"p1_sets30"});la=key.rename(columns={"player":"loser_name","rank":"p2_rank","age":"p2_age","ht":"p2_ht","hand":"p2_hand","elo_seed":"p2_elo","glicko_seed":"p2_glicko","rd_seed":"p2_rd","winrate_before":"p2_winrate","serve_rate_before":"p2_serve","form5":"p2_form5","form10":"p2_form10","form20":"p2_form20","surface_form":"p2_surface_form","opp_quality":"p2_opp_quality","minutes30":"p2_minutes30","matches30":"p2_matches30","sets30":"p2_sets30"})
base=df.reset_index().rename(columns={"index":"idx"}).merge(wa,on=["idx","winner_name"],how="left").merge(la,on=["idx","loser_name"],how="left")
rows=[]
for flip in (False,True):
 x=base.copy();pairs=[("p1","p2")];
 if flip:
  for c in ["rank","age","ht","hand","elo","glicko","rd","winrate","serve","form5","form10","form20","surface_form","opp_quality","minutes30","matches30","sets30"]:x[f"p1_{c}"],x[f"p2_{c}"]=x[f"p2_{c}"].copy(),x[f"p1_{c}"].copy()
 x["p1_name"]=x["winner_name"]; x["p2_name"]=x["loser_name"]; x["target_win"]=0 if flip else 1
 for d,a1,b1 in [("diff","elo","elo"),("diff","glicko","glicko"),("diff","rd","rd")]:pass
 for name in ["elo","glicko","rd","rank","age","ht","hand","winrate","serve","form5","form10","form20","surface_form","opp_quality","minutes30","matches30","sets30"]:x[f"{name}_diff"]=x[f"p1_{name}"]-x[f"p2_{name}"]
 rows.append(x[["date","p1_name","p2_name","target_win","target_total","target_diff","p1_rank","p2_rank","rank_diff","p1_age","p2_age","age_diff","p1_ht","p2_ht","ht_diff","p1_hand","p2_hand","hand_diff","p1_elo","p2_elo","elo_diff","p1_glicko","p2_glicko","glicko_diff","p1_rd","p2_rd","rd_diff","p1_winrate","p2_winrate","winrate_diff","p1_serve","p2_serve","serve_diff","p1_form5","p2_form5","form5_diff","p1_form10","p2_form10","form10_diff","p1_form20","p2_form20","form20_diff","p1_surface_form","p2_surface_form","surface_form_diff","p1_opp_quality","p2_opp_quality","opp_quality_diff","p1_minutes30","p2_minutes30","minutes30_diff","p1_matches30","p2_matches30","matches30_diff","p1_sets30","p2_sets30","sets30_diff","surface_code","best_of","round_code"]])
out=pd.concat(rows,ignore_index=True).replace([np.inf,-np.inf],np.nan).fillna(0);Path(a.out).parent.mkdir(parents=True,exist_ok=True);out.to_csv(a.out,index=False);print("[OK]",a.out,out.shape,out.date.min(),out.date.max())
