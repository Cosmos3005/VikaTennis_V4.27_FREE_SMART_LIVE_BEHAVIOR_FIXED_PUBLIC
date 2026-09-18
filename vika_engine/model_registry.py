from __future__ import annotations
import json, shutil
from pathlib import Path

class ModelRegistry:
    """Small filesystem champion/challenger registry with rollback."""
    def __init__(self, root='models/registry'):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.meta=self.root/'registry.json'
    def _read(self): return json.loads(self.meta.read_text()) if self.meta.exists() else {'champion':None,'history':[]}
    def promote(self, model_path, version, metrics):
        data=self._read(); src=Path(model_path); dest=self.root/f'{version}.joblib'; shutil.copy2(src,dest)
        if data.get('champion'):
            data['history'].append(data['champion'])
        data['champion']={'version':version,'path':str(dest),'metrics':metrics}
        self.meta.write_text(json.dumps(data,indent=2,ensure_ascii=False))
        return data['champion']
    def champion(self): return self._read().get('champion')
