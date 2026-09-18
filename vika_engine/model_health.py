from __future__ import annotations
import json, math
from pathlib import Path
from datetime import datetime, timezone
from .paths import root_path

class ModelHealth:
    def __init__(self, model_path='models/vika_models_v42.joblib', live_paths=None):
        self.model_path=root_path(model_path)
        self.live_paths=[root_path(p) for p in (live_paths or ['models/vika_live_v417.joblib','models/vika_live_v416.joblib','models/vika_live_v47.joblib'])]
    def report(self):
        live=next((p for p in self.live_paths if p.exists()),None)
        reports=[]
        for p in [self.model_path, live]:
            if p:
                reports.append({'path':str(p),'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else 0,
                                'modified_utc':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat() if p.exists() else None})
        return {'ok':self.model_path.exists(),'checked_utc':datetime.now(timezone.utc).isoformat(),'artifacts':reports,
                'live_artifact':str(live) if live else None}
