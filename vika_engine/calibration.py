from __future__ import annotations
import numpy as np

def confidence(probability: float, data_quality: float, uncertainty: float = 0.0) -> str:
    strength=abs(float(probability)-0.5)*2
    score=0.60*strength+0.30*float(data_quality)-0.10*min(1.0,float(uncertainty))
    return 'HIGH' if score>=0.68 else ('MEDIUM' if score>=0.43 else 'LOW')
