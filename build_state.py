import argparse,json,math,pandas as pd
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',default='data/all_matches_2015_2025.csv');p.add_argument('--extra',default='');p.add_argument('--out',default='models/player_state_v4.json');a=p.parse_args()
cols=['tourney_date','surface','winner_id','winner_name','winner_rank','loser_id','loser_name','loser_rank','score','minutes','w_svpt','w_1stWon','w_2ndWon','l_svpt','l_1stWon','l_2ndWon','match_num','tour']
df=pd.read_csv(a.source,usecols=cols,low_memory=False);df=df[df.tour.astype(str).str.lower().eq('atp')].copy();df['date']=pd.to_datetime(df.tourney_date.astype(str).str.split('.').str[0],format='%Y%m%d',errors='coerce');df=df[df.date.notna()].sort_values(['date','match_num']);df=df[df.date>=df.date.max()-pd.Timedelta(days=365)]
players={};h2h={}
def num(v):
 try:x=float(v);return 0 if math.isnan(x) else x
 except:return 0
def sets(s):return sum(1 for z in str(s or '').split() if '-' in z)
def get(name,pid='',rank=None):
 k=str(name).strip().lower()
 if k not in players:
  rr=num(rank);elo=max(1200,min(2300,2500-(rr-1)*.55)) if rr>0 else 1500
  players[k]={'name':str(name).strip(),'player_id':str(pid or ''),'elo':elo,'glicko':{'rating':elo,'rd':250.0,'volatility':0.06},'surface_elo':{'Hard':elo,'Clay':elo,'Grass':elo,'Carpet':elo},'wins':0,'losses':0,'surface_wins':{},'surface_losses':{},'recent':[],'h2h':{},'last_match':None,'minutes_7d':0,'minutes_30d':0,'matches_7d':0,'matches_30d':0,'sets_30d':0,'service_points':0,'service_points_won':0,'return_points':0,'return_points_won':0,'opp_elos':[]}
 return players[k]
for r in df.itertuples(index=False):
 w=get(r.winner_name,r.winner_id,r.winner_rank);l=get(r.loser_name,r.loser_id,r.loser_rank);surf=str(r.surface or 'Hard');we,le=w['elo'],l['elo'];exp=1/(1+10**((le-we)/400));w['elo']=we+24*(1-exp);l['elo']=le-24*(1-exp);w['glicko']['rating']=w['elo'];l['glicko']['rating']=l['elo']
 for p,win,opp,svpt,sw1,sw2 in [(w,1,le,r.w_svpt,r.w_1stWon,r.w_2ndWon),(l,0,we,r.l_svpt,r.l_1stWon,r.l_2ndWon)]:
  mins=num(r.minutes);sv=num(svpt);won=num(sw1)+num(sw2);opp_sv=num(r.l_svpt if p is w else r.w_svpt);opp_won=num(r.l_1stWon if p is w else r.w_1stWon)+num(r.l_2ndWon if p is w else r.w_2ndWon);ss=sets(r.score);p['wins']+=win;p['losses']+=1-win;p['surface_wins'][surf]=p['surface_wins'].get(surf,0)+win;p['surface_losses'][surf]=p['surface_losses'].get(surf,0)+1-win;p['recent'].append({'date':str(r.date.date()),'win':win,'surface':surf,'minutes':mins,'opp_elo':opp,'sets':ss});p['recent']=p['recent'][-50:];p['opp_elos'].append(opp);p['opp_elos']=p['opp_elos'][-50:];p['service_points']+=int(sv);p['service_points_won']+=int(won);p['return_points']+=int(opp_sv);p['return_points_won']+=int(max(0,opp_sv-opp_won));p['last_match']=str(r.date.date())
 h2h.setdefault(w['name'].lower(),{}).setdefault(l['name'].lower(),[]).append(1);h2h.setdefault(l['name'].lower(),{}).setdefault(w['name'].lower(),[]).append(0)
for k,p0 in players.items():
 p0['h2h']={kk:vv[-20:] for kk,vv in h2h.get(k,{}).items()};now=df.date.max();rr=p0['recent'];p0['matches_7d']=sum((now-pd.Timestamp(x['date'])).days<=7 for x in rr);p0['matches_30d']=sum((now-pd.Timestamp(x['date'])).days<=30 for x in rr);p0['minutes_7d']=sum(x['minutes'] for x in rr if (now-pd.Timestamp(x['date'])).days<=7);p0['minutes_30d']=sum(x['minutes'] for x in rr if (now-pd.Timestamp(x['date'])).days<=30);p0['sets_30d']=sum(x['sets'] for x in rr if (now-pd.Timestamp(x['date'])).days<=30)
Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps({'max_date':str(df.date.max()),'players':players},ensure_ascii=False),encoding='utf-8');print('[OK]',a.out,len(players),'players through',df.date.max())
