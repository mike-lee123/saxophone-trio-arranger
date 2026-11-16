from pathlib import Path
import json,hashlib,io,zipfile,shutil
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

def test_all_repository_files_fit_browser_upload():
    files=[f for f in ROOT.rglob('*') if f.is_file() and not any(s in f.parts for s in ('__pycache__','.pytest_cache'))]
    assert max(f.stat().st_size for f in files)<=8*1024*1024

def test_performance_parts_reconstruct_valid_complete_archive():
    spec=json.loads((ROOT/'assets/complete-performance.zip.parts.json').read_text())
    raw=b''.join((ROOT/'assets'/p['name']).read_bytes() for p in spec['parts'])
    assert hashlib.sha256(raw).hexdigest()==spec['sha256']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        assert all(f'Alto{i}_完整試奏.mp3' in z.namelist() for i in (1,2,3))

def test_missing_part_has_actionable_error(tmp_path):
    (tmp_path/'dashboard.py').write_text((ROOT/'dashboard.py').read_text(encoding='utf-8'),encoding='utf-8')
    (tmp_path/'assets').mkdir()
    shutil.copy2(ROOT/'assets/complete-performance.zip.parts.json',tmp_path/'assets')
    app=AppTest.from_file(str(tmp_path/'dashboard.py'),default_timeout=30).run()
    assert not app.exception
    assert any('分片不完整' in e.value for e in app.error)
    assert not app.metric
