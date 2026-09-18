from __future__ import annotations
import argparse, csv, gzip, json, os, re, time
from datetime import date
from pathlib import Path
import requests

PB_BASE='https://raw.githubusercontent.com/JeffSackmann/tennis_slam_pointbypoint/master'
SLAMS=('ausopen','frenchopen','wimbledon','usopen')

def parse_date(v):
    s=str(v).strip()
    m=re.match(r'^(\d{4})(\d{2})(\d{2})',s)
    return date(int(m.group(1)),int(m.group(2)),int(m.group(3))) if m else None

def archive_audit(path, start='2015-01-01', end='2025-12-31'):
    st=date.fromisoformat(start); en=date.fromisoformat(end); years={}; tours={}; rows=0; kept=0; bad=0
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            rows+=1; d=parse_date(r.get('tourney_date',''))
            if not d: bad+=1; continue
            if st<=d<=en:
                kept+=1; years[str(d.year)]=years.get(str(d.year),0)+1
                t=(r.get('tour') or '').lower(); tours[t]=tours.get(t,0)+1
    return {'source':str(path),'start':start,'end':end,'rows_total':rows,'rows_in_window':kept,'bad_dates':bad,'years':years,'tours':tours}

def download_slam_pbp(out_dir, start_year=2015, end_year=2025, sleep=0.15):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); results=[]
    for y in range(start_year,end_year+1):
        for slam in SLAMS:
            name=f'{y}-{slam}-points.csv'; dest=out/name
            if dest.exists() and dest.stat().st_size>1000:
                results.append({'file':name,'status':'exists','bytes':dest.stat().st_size}); continue
            url=f'{PB_BASE}/{name}'
            try:
                r=requests.get(url,timeout=30)
                if r.status_code==200 and len(r.content)>1000:
                    dest.write_bytes(r.content); results.append({'file':name,'status':'downloaded','bytes':len(r.content)})
                else: results.append({'file':name,'status':f'http_{r.status_code}','bytes':0})
            except Exception as e: results.append({'file':name,'status':'error','error':str(e)})
            time.sleep(sleep)
    return results

def main():
    ap=argparse.ArgumentParser(description='V4.11: fuse the supplied 2015-2025 archive with public point-by-point Grand Slam data')
    ap.add_argument('--archive',default='data/archive/all_matches_2015_2025.csv.gz')
    ap.add_argument('--pbp-dir',default='data/pbp_public')
    ap.add_argument('--audit-only',action='store_true'); ap.add_argument('--download-pbp',action='store_true')
    a=ap.parse_args(); report=archive_audit(a.archive)
    if a.download_pbp: report['pbp_download']=download_slam_pbp(a.pbp_dir)
    Path('models').mkdir(exist_ok=True); Path('models/archive_fusion_v411.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
