from pathlib import Path
import scripts_v420_production_audit as audit

def test_required_artifacts():
    assert audit.artifact_check() == []

def test_no_secret_patterns_in_text_sources():
    assert audit.secret_scan() == []

def test_all_python_sources_parse():
    assert audit.py_compile_all() == []
