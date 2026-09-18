import argparse, pandas as pd, numpy as np, math
from pathlib import Path
from collections import deque

SURF={'Hard':0,'Clay':1,'Grass':2,'Carpet':3}

def score(s):
    total=diff=sets=0
    for z in str(s or '').split():
        z=z.split('(')[0]
        if '-' not in z: continue
        try:
            a,b=map(int,z.split('-')[:2]); total+=a+b; diff+=a-b; sets+=1
        except: pass
    return total,diff,sets

def f(v,d=0.):
    try:
        x=float(v); return x if np.isfinite(x) else d
    except: return d

def newp():
    return dict(elo=1500.,glicko=1500.,rd=350.,surf={},wins=0,losses=0,form=deque(maxlen=50),h2h={},
                sv=0.,sw=0.,rv=0.,rw=0., recent=deque(maxlen=60))

def form(p,n,surf,day):
    vals=[]; ws=[]
    for x in reversed(p['form']):
        if surf and x[2]!=surf: continue
        age=max(0,(day-x[0]).days); vals.append(x[1]); ws.append(math.exp(-age/30.))
        if len(vals)>=n: break
    return sum(v*w for v,w in zip(vals,ws))/sum(ws) if ws else .5

def snap(p,rank,age,ht,hand,surf,day):
    days=(day-p['recent'][-1][0]).days if p['recent'] else 365
    return dict(rank=f(rank,999),age=f(age,27),ht=f(ht,185),hand=1. if str(hand)=='L' else 0.,elo=p['elo'],glicko=p['glicko'],rd=p['rd'],surface_elo=p['surf'].get(surf,1500.),
                form5=form(p,5,surf,day),form10=form(p,10,surf,day),form20=form(p,20,surf,day),surface_form=form(p,10,surf,day),
                service=p['sw']/p['sv'] if p['sv'] else .62,return_=p['rw']/p['rv'] if p['rv'] else .38,
                opp_quality=(sum(x[1] for x in p['recent'])/len(p['recent'])) if p['recent'] else 1500.,
                fatigue7=sum(x[2] for x in p['recent'] if (day-x[0]).days<=7),fatigue30=sum(x[2] for x in p['recent'] if (day-x[0]).days<=30),
                matches7=sum(1 for x in p['recent'] if (day-x[0]).days<=7),matches30=sum(1 for x in p['recent'] if (day-x[0]).days<=30),sets30=sum(x[3] for x in p['recent'] if (day-x[0]).days<=30),rest_days=min(days,365),wins=p['wins'],losses=p['losses'])

def row(a,b,n1,n2,day,target,total,diff,surf,bo,round_code,h2h):
    x={'date':day,'p1_name':n1,'p2_name':n2,'target_win':target,'target_total':total,'target_diff':diff,'surface_code':SURF.get(surf,0),'best_of':bo,'round_code':round_code,'h2h_matches':h2h[0],'h2h_p1_rate':h2h[1]}
    for k,v in a.items(): x['p1_'+k]=v
    for k,v in b.items(): x['p2_'+k]=v
    for k in a: x[k+'_diff']=a[k]-b[k]
    return x

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); ap.add_argument('--out',default='data/v42_features.csv'); ap.add_argument('--start-year',type=int,default=2020); args=ap.parse_args()
    cols=['tourney_date','surface','winner_id','winner_name','winner_hand','winner_ht','winner_age','winner_rank','loser_id','loser_name','loser_hand','loser_ht','loser_age','loser_rank','score','best_of','round','minutes','w_svpt','w_1stWon','w_2ndWon','l_svpt','l_1stWon','l_2ndWon','match_num']
    df=pd.read_csv(args.source,usecols=cols,low_memory=False)
    df['date']=pd.to_datetime(df.tourney_date.astype(str).str.split('.').str[0],format='%Y%m%d',errors='coerce')
    df=df[df.date.notna()].sort_values(['date','match_num']).reset_index(drop=True)
    players={}; out=[]; n=len(df)
    for i,r in df.iterrows():
        wn=str(r.winner_name); ln=str(r.loser_name); day=r.date; surf=r.surface if pd.notna(r.surface) else 'Hard'; bo=int(f(r.best_of,3) or 3); total,diff,sets=score(r.score)
        if not total or wn=='nan' or ln=='nan': continue
        w=players.setdefault(wn.lower(),newp()); l=players.setdefault(ln.lower(),newp())
        wa=snap(w,r.winner_rank,r.winner_age,r.winner_ht,r.winner_hand,surf,day); la=snap(l,r.loser_rank,r.loser_age,r.loser_ht,r.loser_hand,surf,day)
        hw=w['h2h'].get(ln.lower(),[]); hl=l['h2h'].get(wn.lower(),[])
        if day.year>=args.start_year:
            hwr=(sum(hw)/len(hw) if hw else .5)
            out.append(row(wa,la,wn,ln,day,1,total,diff,surf,bo,{'R128':1,'R64':2,'R32':3,'R16':4,'QF':5,'SF':6,'F':7}.get(str(r['round']),3),(len(hw),hwr)))
            hwr2=(sum(hl)/len(hl) if hl else .5)
            out.append(row(la,wa,ln,wn,day,0,total,-diff,surf,bo,{'R128':1,'R64':2,'R32':3,'R16':4,'QF':5,'SF':6,'F':7}.get(str(r['round']),3),(len(hl),hwr2)))
        # update ratings after prediction features are captured
        we=1/(1+10**((l['elo']-w['elo'])/400)); k=24.; w['elo']+=k*(1-we); l['elo']+=k*(0-(1-we))
        for p,opp,sc in ((w,l,1.),(l,w,0.)):
            se=p['surf'].get(surf,1500.); oe=1/(1+10**((opp['elo']-se)/400)); p['surf'][surf]=se+k*(sc-oe)
        # Lightweight uncertainty-aware rating update (Glicko-style)
        for p,opp,sc in ((w,l,1.),(l,w,0.)):
            rd=max(30.,min(350.,p['rd'])); g=1/math.sqrt(1+3*(rd/173.7178)**2/(math.pi**2)); E=1/(1+math.exp(-g*(p['glicko']-opp['glicko'])/173.7178)); v=1/max(1e-9,g*g*E*(1-E)); phi=rd/173.7178; phistar=math.sqrt(phi*phi+0.06**2); phip=1/math.sqrt(1/(phistar*phistar)+1/v); mup=(p['glicko']-1500)/173.7178+phip*phip*g*(sc-E); p['glicko']=1500+173.7178*mup; p['rd']=max(30,min(350,173.7178*phip))
        mins=f(r.minutes,0.); wsv=f(r.w_svpt); lsv=f(r.l_svpt); wsw=f(r.w_1stWon)+f(r.w_2ndWon); lsw=f(r.l_1stWon)+f(r.l_2ndWon)
        w['sv']+=max(wsv,1); w['sw']+=wsw; l['sv']+=max(lsv,1); l['sw']+=lsw; w['rv']+=max(lsv,1); w['rw']+=max(0,lsv-lsw); l['rv']+=max(wsv,1); l['rw']+=max(0,wsv-wsw)
        for p,win,opp in ((w,1,l['elo']),(l,0,w['elo'])):
            p['wins']+=win; p['losses']+=1-win; p['form'].append((day,win,surf)); p['recent'].append((day,opp,mins,sets));
            # keep h2h bounded
        w['h2h'].setdefault(ln.lower(),[]).append(1); l['h2h'].setdefault(wn.lower(),[]).append(0)
        if i and i%25000==0: print(i,n,flush=True)
    out=pd.DataFrame(out).replace([np.inf,-np.inf],np.nan).fillna(0)
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.out,index=False); print('[OK]',out.shape,out.date.min(),out.date.max())
if __name__=='__main__': main()
