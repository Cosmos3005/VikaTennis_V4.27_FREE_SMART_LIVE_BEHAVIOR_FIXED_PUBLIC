from __future__ import annotations
import argparse, gzip, hashlib, json, os, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path
import requests

BASE='https://api.livetennisapi.com/api/public/v1'


def api_get(key, path, params=None, stream=False, timeout=120):
    r=requests.get(BASE+path, headers={'Authorization':f'Bearer {key}'}, params=params or {}, timeout=timeout, stream=stream)
    if r.status_code in (429,):
        retry=int(r.headers.get('Retry-After','10'))
        time.sleep(min(max(retry,2),120))
        r=requests.get(BASE+path, headers={'Authorization':f'Bearer {key}'}, params=params or {}, timeout=timeout, stream=stream)
    r.raise_for_status(); return r


def iso_date(x):
    if not x: return None
    s=str(x)[:10]
    try: return date.fromisoformat(s)
    except Exception: return None


def in_window(obj, start, end):
    m=obj.get('match',obj) if isinstance(obj,dict) else {}
    for k in ('date','event_date','start_time','scheduled_at','played_at'):
        d=iso_date(m.get(k))
        if d: return start <= d <= end
    return True


def download_package(key, period, kind, out_dir, fmt='jsonl', force=False):
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    out=out_dir/f'{kind}_{period}.{fmt}.gz'
    if out.exists() and not force: return out
    r=api_get(key,f'/history/packages/{period}',{'kind':kind,'format':fmt},stream=True)
    # API may return gzip bytes even when content-type says attachment.
    raw=r.raw
    data=raw.read()
    # Always store gzip to keep disk size low.
    if r.headers.get('Content-Encoding') == 'gzip':
        blob=data
    else:
        try: gzip.decompress(data); blob=data
        except Exception: blob=gzip.compress(data,compresslevel=6)
    out.write_bytes(blob)
    return out


def iter_jsonl(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_filtered(srcs, dst, start, end, kind, tours=('atp','wta'), singles_only=True, min_coverage=False):
    Path(dst).parent.mkdir(parents=True,exist_ok=True)
    n=0; kept=0
    with open(dst,'w',encoding='utf-8') as out:
        for src in srcs:
            for obj in iter_jsonl(src):
                n+=1
                m=obj.get('match',obj) if isinstance(obj,dict) else {}
                # Archive records may be winner/loser shaped; archive tapes normally contain match metadata.
                tour=str(m.get('tour',m.get('level',''))).lower()
                if tour and tour not in tours and not (tour in ('atp','wta')): continue
                draw=str(m.get('draw','singles')).lower()
                if singles_only and draw and draw != 'singles': continue
                if not in_window(obj,start,end): continue
                if min_coverage:
                    meta=obj.get('meta',{}) if isinstance(obj,dict) else {}
                    cov=str(meta.get('coverage','')).lower()
                    pc=meta.get('point_complete',meta.get('points_complete'))
                    if pc is False or cov in ('none','partial'): continue
                out.write(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n')
                kept+=1
    return n,kept


def main():
    ap=argparse.ArgumentParser(description='VikaTennis V4.8: download last five years of historical tapes and train live model')
    ap.add_argument('--start',default='2021-09-08')
    ap.add_argument('--end',default='2026-09-08')
    ap.add_argument('--data-dir',default='data/history_v48')
    ap.add_argument('--filtered',default='data/live_history_v48.jsonl')
    ap.add_argument('--skip-download',action='store_true')
    ap.add_argument('--force',action='store_true')
    ap.add_argument('--all-tours',action='store_true')
    ap.add_argument('--include-partial',action='store_true')
    ap.add_argument('--train',action='store_true')
    ap.add_argument('--max-snapshots-per-match',type=int,default=80)
    args=ap.parse_args()
    key=os.getenv('LIVETENNISAPI_KEY')
    if not key: raise SystemExit('LIVETENNISAPI_KEY is required')
    start=date.fromisoformat(args.start); end=date.fromisoformat(args.end)
    years=range(start.year,end.year+1)
    root=Path(args.data_dir)
    package_files=[]
    if not args.skip_download:
        # 2021-2022: reconstructed archive tapes. 2023-end: observed historical tapes.
        for y in (2021,2022):
            if y not in years: continue
            p=download_package(key,str(y),'archive_tape',root/'archive_tape',force=args.force)
            package_files.append(p)
        y=2023
        while y<=end.year:
            first=max(start,date(y,1,1)); last=min(end,date(y,12,31))
            if first<=last:
                d=first.replace(day=1)
                while d<=last:
                    period=f'{d.year:04d}-{d.month:02d}'
                    try:
                        p=download_package(key,period,'tape',root/'tape',force=args.force); package_files.append(p)
                    except requests.HTTPError as e:
                        if e.response is not None and e.response.status_code==404: pass
                        else: raise
                    d=(d.replace(day=28)+timedelta(days=4)).replace(day=1)
            y+=1
    else:
        package_files=list(root.rglob('*.jsonl.gz'))
    tours=('atp','wta') if not args.all_tours else ('atp','wta','challenger','itf','juniors')
    total,kept=write_filtered(package_files,args.filtered,start,end,'mixed',tours=tours,singles_only=True,min_coverage=not args.include_partial)
    print(json.dumps({'start':str(start),'end':str(end),'packages':len(package_files),'source_records':total,'kept_matches':kept,'filtered':args.filtered,'tours':tours,'singles_only':True},indent=2))
    if args.train:
        from scripts_v47_train_live import main as train_main
        old=sys.argv; sys.argv=['scripts_v47_train_live.py','--history-jsonl',args.filtered,'--output','models/vika_live_v48.joblib','--max-snapshots-per-match',str(args.max_snapshots_per_match)]
        try: train_main()
        finally: sys.argv=old

if __name__=='__main__': main()
