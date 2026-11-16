from pathlib import Path
import json
import pytest
from streamlit.testing.v1 import AppTest
from trio.audio import load_bank,BANK_PATH

ROOT=Path(__file__).resolve().parents[1]

def test_chunked_recorded_bank_loads_all_notes():
    assert not BANK_PATH.exists()
    assert len(load_bank())==64

def test_corrupted_chunk_is_rejected(tmp_path):
    path=tmp_path/'bank.npz'
    (tmp_path/'part000').write_bytes(b'bad')
    (tmp_path/'bank.npz.parts.json').write_text(json.dumps({'sha256':'invalid','parts':[{'name':'part000','sha256':'invalid'}]}))
    with pytest.raises(ValueError,match='checksum'):
        load_bank(path)

def test_cloud_entry_and_private_server_key(monkeypatch):
    secret='test-server-key-not-for-browser'
    monkeypatch.setenv('OPENAI_API_KEY',secret)
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
    assert not app.exception and app.metric[0].value=='60'
    next(r for r in app.radio if r.label=='工作區').set_value('上傳與編曲工作台').run()
    assert not app.exception
    assert all(secret not in str(field.value) for field in app.text_input)
    assert next(field for field in app.text_input if 'OpenAI API Key' in field.label).value==''
