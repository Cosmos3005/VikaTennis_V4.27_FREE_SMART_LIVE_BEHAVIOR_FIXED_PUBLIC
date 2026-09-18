from __future__ import annotations
from pathlib import Path
import json, sqlite3
from datetime import datetime, timezone

class PredictionJournal:
    def __init__(self,path='data/predictions.sqlite'):
        self.path=path; Path(path).parent.mkdir(parents=True,exist_ok=True); self._init()
    def _init(self):
        with sqlite3.connect(self.path) as c:
            c.execute('''create table if not exists predictions (id integer primary key autoincrement, ts text, match_key text, p1 text, p2 text, surface text, p1_prob real, model_version text, data_quality real, confidence real, odds1 real, odds2 real, actual_winner text, payload text)''')
    def log(self,result):
        with sqlite3.connect(self.path) as c:
            c.execute('insert into predictions(ts,match_key,p1,p2,surface,p1_prob,model_version,data_quality,confidence,odds1,odds2,payload) values(?,?,?,?,?,?,?,?,?,?,?,?)',(result.get('timestamp',datetime.now(timezone.utc).isoformat()),f"{result['p1']}::{result['p2']}",result['p1'],result['p2'],result.get('surface',''),result['p1_win'],result.get('model_version',''),result.get('data_quality',0),result.get('confidence',0),result.get('odds1'),result.get('odds2'),json.dumps(result,ensure_ascii=False,default=str)))
    def settle(self,p1,p2,winner):
        with sqlite3.connect(self.path) as c: c.execute('update predictions set actual_winner=? where p1=? and p2=? and actual_winner is null',(winner,p1,p2))

    def settle_by_match(self, match_key, winner):
        with sqlite3.connect(self.path) as c:
            c.execute('update predictions set actual_winner=? where match_key=? and actual_winner is null',(winner,match_key))

    def error_report(self):
        with sqlite3.connect(self.path) as c:
            rows=c.execute('select p1,p2,surface,p1_prob,actual_winner,model_version from predictions where actual_winner is not null').fetchall()
        if not rows: return {'n':0}
        n=len(rows); brier=0.0; acc=0
        by_surface={}
        for p1,p2,s,p,actual,ver in rows:
            y=1 if actual==p1 else 0
            brier+=(p-y)**2; acc+=int((p>=.5)==bool(y))
            z=by_surface.setdefault(s,{'n':0,'brier':0.0,'accuracy':0})
            z['n']+=1; z['brier']+=(p-y)**2; z['accuracy']+=int((p>=.5)==bool(y))
        for z in by_surface.values(): z['brier']/=z['n']; z['accuracy']/=z['n']
        return {'n':n,'accuracy':acc/n,'brier':brier/n,'by_surface':by_surface}
