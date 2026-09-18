from __future__ import annotations
import json, os, time
from typing import Callable, Optional

class LiveWebSocket:
    """ULTRA score/point WebSocket with reconnect-safe REST point catch-up."""
    def __init__(self, api_key=None, base_url='https://api.livetennisapi.com/api/public/v1'):
        self.api_key=api_key or os.getenv('LIVETENNISAPI_KEY')
        self.base_url=base_url.rstrip('/'); self.ws=None

    def _token(self):
        import requests
        r=requests.get(self.base_url+'/ws-token',headers={'Authorization':f'Bearer {self.api_key}'},timeout=15)
        r.raise_for_status(); return r.json()

    def catch_up_points(self, match_id: str, after_seq: int = 0, return_meta: bool = False):
        import requests
        rows=[]; cursor=max(0,int(after_seq or 0)); meta={}
        while True:
            r=requests.get(f'{self.base_url}/matches/{match_id}/points',
                           headers={'Authorization':f'Bearer {self.api_key}'},
                           params={'after_seq':cursor},timeout=20)
            if r.status_code == 404: return (rows, meta) if return_meta else rows
            r.raise_for_status(); payload=r.json() if r.content else {}
            if isinstance(payload,dict):
                meta['basis']=payload.get('basis'); meta['quality']=payload.get('quality'); meta['pbp_coverage']=payload.get('pbp_coverage')
            page=payload.get('points',[]) if isinstance(payload,dict) else []
            rows.extend(page)
            last=int(payload.get('last_seq',cursor) or cursor) if isinstance(payload,dict) else cursor
            if not payload.get('has_more') or last <= cursor: break
            cursor=last
        return (rows, meta) if return_meta else rows

    def stream_match(self, match_id: str, on_frame: Callable[[dict], None], stop_after: Optional[float]=None,
                     include_points: bool=True, reconnects: int=3, on_point: Callable[[dict], None]|None=None):
        if not self.api_key: raise RuntimeError('LIVETENNISAPI_KEY is required')
        import websocket
        started=time.time(); attempts=0; last_seq=0
        while True:
            if stop_after is not None and time.time()-started >= stop_after: break
            try:
                info=self._token(); ws_url=info['ws_url']; token=info['token']
                ws=websocket.create_connection(ws_url,timeout=30); self.ws=ws
                ws.send(json.dumps({'connect':{'token':token},'id':1}))
                signals=['points'] if include_points else []
                # Native protocol currently supports match channels; the public docs
                # also describe topic subscriptions. We use the raw channel protocol.
                ws.send(json.dumps({'subscribe':{'channel':f'match:{match_id}'},'id':2}))
                if include_points:
                    ws.send(json.dumps({'subscribe':{'channel':f'point:match:{match_id}'},'id':3}))
                    caught, meta = self.catch_up_points(match_id,last_seq,return_meta=True)
                    for row in caught:
                        p=row.get('point',row) if isinstance(row,dict) else row
                        if isinstance(p,dict) and int(p.get('seq',0) or 0)>last_seq:
                            last_seq=int(p['seq']); (on_point or on_frame)(row)
                while True:
                    if stop_after is not None and time.time()-started >= stop_after: return
                    raw=ws.recv()
                    if raw is None: break
                    for line in str(raw).splitlines():
                        if not line.strip(): continue
                        msg=json.loads(line)
                        if msg == {}: ws.send('{}'); continue
                        payload=((msg.get('push') or {}).get('pub') or {}).get('data')
                        if payload is None: continue
                        p=payload.get('point') if isinstance(payload,dict) else None
                        if isinstance(p,dict) and p.get('seq') is not None:
                            seq=int(p['seq'])
                            if seq<=last_seq: continue
                            last_seq=seq; (on_point or on_frame)(payload)
                        else: on_frame(payload)
            except Exception:
                attempts += 1
                if attempts > reconnects: raise
                time.sleep(min(2 ** attempts, 10))
            finally:
                try: ws.close()
                except Exception: pass
                self.ws=None
