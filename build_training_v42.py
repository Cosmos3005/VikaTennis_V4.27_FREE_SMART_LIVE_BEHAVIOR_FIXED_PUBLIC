import argparse, pandas as pd, numpy as np
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',default='data/v4_features.csv'); ap.add_argument('--out',default='data/v42_features.csv'); args=ap.parse_args()
    df=pd.read_csv(args.source,parse_dates=['date'],low_memory=False).sort_values('date').reset_index(drop=True)
    # The previous generator created a winner-oriented row plus a broken flipped row.
    # Rebuild both perspectives from canonical winner rows, so p1/p2 and target are consistent.
    df=df[df.target_win==1].copy().reset_index(drop=True)
    player_elo={}; player_glicko={}; player_rd={}
    rows=[]
    def swap_row(r):
        x=r.copy()
        for c in list(r.index):
            if c.startswith('p1_'): 
                c2='p2_'+c[3:]
                if c2 in r.index: x[c]=r[c2]
            elif c.startswith('p2_'):
                c2='p1_'+c[3:]
                if c2 in r.index: x[c]=r[c2]
            elif c.endswith('_diff') and c not in ('target_diff',): x[c]=-r[c]
        x['p1_name']=r['p2_name']; x['p2_name']=r['p1_name']; x['target_win']=0; x['target_diff']=-r['target_diff']
        return x
    for _,r in df.iterrows():
        a=str(r.p1_name); b=str(r.p2_name)
        ea=player_elo.setdefault(a,float(r.p1_elo) if np.isfinite(r.p1_elo) else 1500.)
        eb=player_elo.setdefault(b,float(r.p2_elo) if np.isfinite(r.p2_elo) else 1500.)
        ga=player_glicko.setdefault(a,float(r.p1_glicko) if np.isfinite(r.p1_glicko) else ea)
        gb=player_glicko.setdefault(b,float(r.p2_glicko) if np.isfinite(r.p2_glicko) else eb)
        ra=player_rd.setdefault(a,float(r.p1_rd) if np.isfinite(r.p1_rd) else 250.)
        rb=player_rd.setdefault(b,float(r.p2_rd) if np.isfinite(r.p2_rd) else 250.)
        # Snapshot ratings BEFORE this match.
        r=r.copy(); r['p1_elo_dyn']=ea; r['p2_elo_dyn']=eb; r['elo_dyn_diff']=ea-eb; r['p1_glicko_dyn']=ga; r['p2_glicko_dyn']=gb; r['glicko_dyn_diff']=ga-gb; r['p1_rd_dyn']=ra; r['p2_rd_dyn']=rb; r['rd_dyn_diff']=ra-rb
        rows.append(r); s=swap_row(r); rows.append(s)
        # Update after outcome (winner row is always player a).
        expected=1/(1+10**((eb-ea)/400)); k=24.; player_elo[a]=ea+k*(1-expected); player_elo[b]=eb+k*(0-(1-expected))
        # Lightweight uncertainty-aware update, used as a state feature only.
        for name,opp,sc,rd in ((a,gb,1.,ra),(b,ga,0.,rb)):
            g=1/(1+3*(rd/173.7178)**2/(np.pi**2))**0.5
            E=1/(1+np.exp(-g*((player_glicko[name]-opp)/173.7178)))
            v=1/max(1e-9,g*g*E*(1-E)); phi=rd/173.7178; phistar=np.sqrt(phi*phi+0.06**2); phip=1/np.sqrt(1/(phistar*phistar)+1/v)
            mu=(player_glicko[name]-1500)/173.7178+phip*phip*g*(sc-E); player_glicko[name]=1500+173.7178*mu; player_rd[name]=max(30,min(350,173.7178*phip))
    out=pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan).fillna(0)
    # Remove identifiers from model features later; keep names for journal/debugging.
    Path(args.out).parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.out,index=False)
    print('[OK]',out.shape,out.date.min(),out.date.max())
if __name__=='__main__': main()
