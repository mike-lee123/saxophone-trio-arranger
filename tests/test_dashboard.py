from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

def test_dashboard_library_and_voice_switch():
    app=AppTest.from_file(str(ROOT/'dashboard.py'),default_timeout=30).run()
    next(s for s in app.selectbox if s.label=='曲目').set_value('黃昏的故鄉 · 三 Alto').run()
    assert not app.exception
    assert app.metric[0].value=='67'
    assert len(app.get('download_button'))>=12
    next(r for r in app.radio if r.label=='選擇譜式').set_value('簡譜').run()
    next(s for s in app.selectbox if s.label=='練習聲部').set_value('Alto 2').run()
    assert not app.exception
    assert len(app.get('audio'))==1
    assert app.get('audio')[0].proto.url

def test_dashboard_studio_supports_editorial_export():
    app=AppTest.from_file(str(ROOT/'dashboard.py'),default_timeout=30).run()
    next(s for s in app.selectbox if s.label=='曲目').set_value('黃昏的故鄉 · 三 Alto').run()
    next(r for r in app.radio if r.label=='工作區').set_value('上傳與編曲工作台').run()
    assert not app.exception
    next(b for b in app.button if b.label=='載入完整演出編訂版（免人工確認）').click().run()
    assert not app.exception
    assert app.session_state.project.review_policy=='editorial'
    assert not next(b for b in app.button if b.label=='編曲並建立正式輸出 ZIP').disabled
    next(r for r in app.radio if r.label=='工作區').set_value('演出儀表板').run()
    assert not app.exception
    assert app.metric[0].value=='67'
