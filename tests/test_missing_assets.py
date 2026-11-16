from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

def isolated_dashboard(tmp_path):
    target=tmp_path/'dashboard.py'
    target.write_text((ROOT/'dashboard.py').read_text(encoding='utf-8'),encoding='utf-8')
    return AppTest.from_file(str(target),default_timeout=30)

def test_missing_assets_offer_repair_instead_of_exception(tmp_path):
    app=isolated_dashboard(tmp_path).run()
    assert not app.exception
    assert len(app.get('file_uploader'))==1
    assert any('assets/complete-performance.zip' in c.value for c in app.code)
    assert not app.metric

def test_uploaded_performance_restores_dashboard(tmp_path):
    app=isolated_dashboard(tmp_path)
    app.session_state['performance_upload_bytes']=b''.join((ROOT/'assets'/f'complete-performance.zip.part{i:03d}').read_bytes() for i in range(3))
    app.run()
    assert not app.exception
    assert app.metric[0].value=='67'
    assert len(app.get('audio'))==1

def test_invalid_upload_has_clear_error(tmp_path):
    app=isolated_dashboard(tmp_path)
    app.session_state['performance_upload_bytes']=b'not a zip'
    app.run()
    assert not app.exception
    assert any('無法載入' in e.value for e in app.error)
    assert not app.metric
