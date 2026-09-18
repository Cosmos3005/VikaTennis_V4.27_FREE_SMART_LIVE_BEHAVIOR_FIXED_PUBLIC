from __future__ import annotations
import ast, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEXT_EXT = {'.py','.md','.txt','.yml','.yaml','.env','.example','.json','.toml'}
SECRET_PATTERNS = [
    re.compile(r'\bbot\d{5,}:[A-Za-z0-9_-]{20,}\b'),
    re.compile(r'\btwjp_[A-Za-z0-9_-]{12,}\b'),
]

def py_compile_all():
    bad=[]
    for p in ROOT.rglob('*.py'):
        try: ast.parse(p.read_text(encoding='utf-8'))
        except Exception as e: bad.append((str(p.relative_to(ROOT)), str(e)))
    return bad

def secret_scan():
    hits=[]
    skip_parts={'__pycache__','.git'}
    for p in ROOT.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT: continue
        if any(x in p.parts for x in skip_parts): continue
        try: text=p.read_text(encoding='utf-8',errors='ignore')
        except Exception: continue
        for rx in SECRET_PATTERNS:
            if rx.search(text): hits.append(str(p.relative_to(ROOT)))
    return sorted(set(hits))

def artifact_check():
    required=['models/vika_models_v42.joblib','models/player_state_v4.json','vikatenis_v3_bot.py','start_bot.py']
    return [x for x in required if not (ROOT/x).exists()]

def run_tests():
    p=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,text=True,capture_output=True)
    return p.returncode, (p.stdout+"\n"+p.stderr).strip()

def main():
    result={
        'python_parse_errors': py_compile_all(),
        'secret_hits': secret_scan(),
        'missing_required_artifacts': artifact_check(),
    }
    code,out=run_tests(); result['pytest_returncode']=code; result['pytest_output']=out
    result['ok']=not result['python_parse_errors'] and not result['secret_hits'] and not result['missing_required_artifacts'] and code==0
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['ok'] else 1)

if __name__=='__main__': main()
