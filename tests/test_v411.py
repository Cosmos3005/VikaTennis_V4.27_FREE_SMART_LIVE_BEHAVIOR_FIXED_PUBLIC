import gzip,csv
from pathlib import Path
from scripts_v411_archive_fusion import parse_date, archive_audit

def test_parse_date():
    assert str(parse_date('20250106.0'))=='2025-01-06'

def test_archive_window():
    p=Path('tests/_mini_archive.csv.gz')
    rows=[{'tourney_date':'20141229.0','tour':'atp'},{'tourney_date':'20150104.0','tour':'atp'},{'tourney_date':'20251229.0','tour':'wta'},{'tourney_date':'20260101.0','tour':'wta'}]
    with gzip.open(p,'wt',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['tourney_date','tour']);w.writeheader();w.writerows(rows)
    r=archive_audit(p); assert r['rows_in_window']==2 and r['years']=={'2015':1,'2025':1}
    p.unlink()
