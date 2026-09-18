import argparse
from vika_engine.prediction import PredictionEngine
p=argparse.ArgumentParser(); p.add_argument('--player1',required=True); p.add_argument('--player2',required=True); p.add_argument('--surface',default='Hard'); p.add_argument('--best-of',type=int,default=3); p.add_argument('--p1-odds',type=float); p.add_argument('--p2-odds',type=float); a=p.parse_args()
e=PredictionEngine(); r=e.predict(a.player1,a.player2,a.surface,a.best_of,a.p1_odds,a.p2_odds); print(f"{a.player1}: {r['p1_win']*100:.2f}% | {a.player2}: {r['p2_win']*100:.2f}%"); print('total',r['expected_total'],'diff',r['expected_diff']); print('confidence',r['confidence'],'quality',r['data_quality']); print(r['simulation'])
