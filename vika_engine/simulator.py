from __future__ import annotations
import math
import numpy as np

class MatchSimulator:
    """Monte Carlo score simulator. Uses model probabilities plus optional point-derived hold rates."""
    def __init__(self, seed=42): self.rng=np.random.default_rng(seed)

    def _game_winner(self,p): return self.rng.random() < p

    def _set(self,p1_game,p2_game):
        a=b=0
        while True:
            if self._game_winner(p1_game): a+=1
            else: b+=1
            if (a>=6 or b>=6) and abs(a-b)>=2: return a,b
            if a==6 and b==6:
                # simple tiebreak with slightly amplified serve/strength edge
                p_tb=min(.95,max(.05,0.5+(p1_game-p2_game)*0.45))
                if self._game_winner(p_tb): return 7,6
                return 6,7

    def simulate(self,p1_win,p1_game_prob=None,p2_game_prob=None,best_of=3,n=100000):
        # Infer game-win probability from match win if no serve/return layer exists.
        if p1_game_prob is None:
            p1_game_prob=min(.70,max(.30,.5+(p1_win-.5)*.22))
        if p2_game_prob is None:
            p2_game_prob=min(.70,max(.30,1-p1_game_prob))
        sets_to_win=2 if best_of==3 else 3
        totals=[]; diffs=[]; wins=sets2=sets3=0; score_counts={}
        for _ in range(n):
            s1=s2=0; tg=0; gd=0; score=[]
            while s1<sets_to_win and s2<sets_to_win:
                a,b=self._set(p1_game_prob,p2_game_prob); tg+=a+b; gd+=a-b; score.append(f"{a}-{b}")
                if a>b:s1+=1
                else:s2+=1
                if s1==sets_to_win or s2==sets_to_win: break
            # Above loop has max_sets+1 sets-to-win for BO3 => 2, BO5 =>3.
            totals.append(tg); diffs.append(gd)
            if s1>s2:wins+=1
            if len(score)==2:sets2+=1
            if len(score)==3:sets3+=1
            key=" ".join(score); score_counts[key]=score_counts.get(key,0)+1
        totals=np.asarray(totals); diffs=np.asarray(diffs)
        top_scores=sorted(score_counts.items(),key=lambda x:x[1],reverse=True)[:10]
        return {"simulations":n,"p1_win":wins/n,"p2_win":1-wins/n,"p2_sets_0":sets2/n,"p3_sets":sets3/n,
                "total_mean":float(totals.mean()),"total_p50":float(np.quantile(totals,.5)),
                "total_p10":float(np.quantile(totals,.1)),"total_p90":float(np.quantile(totals,.9)),
                "diff_mean":float(diffs.mean()),"top_scores":[(s,c/n) for s,c in top_scores],"total_samples":totals,"diff_samples":diffs}

    @staticmethod
    def line_probs(result, totals=None, diffs=None):
        totals=result["total_samples"] if totals is None else totals; diffs=result["diff_samples"] if diffs is None else diffs
        over={float(line):float(np.mean(totals>line)) for line in np.arange(17.5,40.5,1)}
        cover={float(line):float(np.mean(diffs+line>0)) for line in np.arange(-8.5,8.6,1)}
        return over,cover
