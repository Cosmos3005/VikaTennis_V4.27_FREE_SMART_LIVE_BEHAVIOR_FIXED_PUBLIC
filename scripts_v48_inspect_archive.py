from __future__ import annotations
import argparse, json, os, requests
BASE='https://api.livetennisapi.com/api/public/v1'

def main():
    ap=argparse.ArgumentParser(description='Inspect historical coverage before downloading V4.8 data')
    ap.add_argument('--start',default='2021-09-08'); ap.add_argument('--end',default='2026-09-08')
    args=ap.parse_args(); key=os.getenv('LIVETENNISAPI_KEY')
    if not key: raise SystemExit('LIVETENNISAPI_KEY is required')
    h={'Authorization':f'Bearer {key}'}
    cov=requests.get(BASE+'/history/coverage',headers=h,timeout=30); cov.raise_for_status()
    print('COVERAGE'); print(json.dumps(cov.json(),ensure_ascii=False,indent=2))
    packs=requests.get(BASE+'/history/packages',headers=h,params={'kind':'archive_tape'},timeout=30)
    print('\nARCHIVE_TAPE_PACKAGES',packs.status_code)
    if packs.ok: print(json.dumps(packs.json(),ensure_ascii=False,indent=2))
    packs2=requests.get(BASE+'/history/packages',headers=h,params={'kind':'tape'},timeout=30)
    print('\nTAPE_PACKAGES',packs2.status_code)
    if packs2.ok:
        data=packs2.json().get('data',[])
        print(json.dumps({'count':len(data),'first':data[:3],'last':data[-3:]},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
