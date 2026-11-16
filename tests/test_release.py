# coding: utf-8
import base64
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import xml.etree.ElementTree as ET
import pytest
from PIL import Image
from music21 import converter
from streamlit.testing.v1 import AppTest
from trio.model import Project, Event, confirm, confirm_structure, clear_reviews, validate_project
from trio.arrange import arrange, written_score
from trio.export import export_bundle
from trio.vision import recognize

ROOT=Path(__file__).resolve().parents[1]

def synthetic(style="enka"):
    p=Project.model_validate_json((ROOT/"examples/synthetic.json").read_text(encoding="utf-8"))
    p.style=style
    return p

def review(p):
    for m in p.measures: confirm(m,p.meter,"Synthetic fixture reviewer")
    p.source_complete=True
    return confirm_structure(p,"Synthetic fixture reviewer")

def test_real_source_manifest_and_unreviewed_draft():
    image=(ROOT/"examples/source/huanghun.jpg").read_bytes()
    manifest=json.loads((ROOT/"examples/source/manifest.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(image).hexdigest()==manifest["sha256"]
    with Image.open(io.BytesIO(image)) as im:
        assert im.size==(875,1181)
        assert im.format=="JPEG"
        im.verify()
    p=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
    assert p.source_sha256==manifest["sha256"]
    assert not p.source_complete and all(e.uncertain for m in p.measures for e in m.events)
    assert sum(e.beats() for e in p.measures[0].events)==4
    with pytest.raises(ValueError): export_bundle(p)

def test_actual_jpg_through_mocked_vision_transport():
    data=(ROOT/"examples/source/huanghun.jpg").read_bytes()
    p=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
    payload={k:p.model_dump()[k] for k in ("title","meter","source_key","tempo","measures","source_notes")}
    def create(**kwargs):
        content=kwargs["input"][0]["content"]
        assert base64.b64decode(content[1]["image_url"].split(",",1)[1])==data
        assert kwargs["store"] is False
        assert kwargs["text"]["format"]["strict"]
        return SimpleNamespace(output_text=json.dumps(payload),status="completed")
    result=recognize(data,"test",client=SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert result.source_sha256==hashlib.sha256(data).hexdigest()
    assert result.style=="enka"
    with pytest.raises(ValueError): export_bundle(result)

def test_truncated_vision_response_never_accepted():
    data=(ROOT/"examples/source/huanghun.jpg").read_bytes()
    fake=SimpleNamespace(responses=SimpleNamespace(create=lambda **k:SimpleNamespace(output_text="{}",status="incomplete")))
    with pytest.raises(ValueError,match="不完整"): recognize(data,"test",client=fake)

@pytest.mark.parametrize("data",[b"not an image",b"%PDF-1.4"])
def test_bad_images_rejected_before_api(data):
    client=SimpleNamespace(responses=SimpleNamespace(create=lambda **k:pytest.fail("API must not be called")))
    with pytest.raises(Exception): recognize(data,"fake",client=client)

def test_complete_bars_still_require_whole_source_review():
    p=synthetic()
    for m in p.measures: confirm(m,p.meter,"Tester")
    with pytest.raises(ValueError,match="完整性"): export_bundle(p)
    p.source_complete=True
    with pytest.raises(ValueError,match="演奏順序"): export_bundle(p)

@pytest.mark.parametrize("field,value",[("meter","2/2"),("style","block"),("source_sha256","other"),("performance_order",[1,1])])
def test_context_change_invalidates_whole_review(field,value):
    p=review(synthetic())
    setattr(p,field,value)
    with pytest.raises(ValueError): export_bundle(p)

def test_import_review_reset():
    p=review(synthetic())
    clear_reviews(p)
    assert not p.source_complete and not p.structure_hash
    assert all(not m.review_hash for m in p.measures)
    with pytest.raises(ValueError): export_bundle(p)

def test_repeat_order_linearized_and_duration_preserved():
    p=synthetic()
    p.measures.append(p.measures[0].model_copy(deep=True));p.measures[1].number=2
    p.measures[1].events[0].degree=2
    p.performance_order=[1,2,1]
    review(p)
    score=arrange(p)
    assert [n.number for n in score.parts[0].getElementsByClass("Measure")]==[1,2,3]
    assert [score.parts[0].measure(i).notes[0].pitch.midi for i in (1,2,3)]==[60,62,60]
    assert score.duration.quarterLength==12

@pytest.mark.parametrize("order",[[0],[99],[-1]])
def test_invalid_playback_order(order):
    p=synthetic();p.performance_order=order
    with pytest.raises(ValueError,match="演奏順序"): review(p)

def test_enka_preserves_lead_and_sustains_lower_parts(tmp_path):
    p=synthetic();m=p.measures[0]
    for e in m.events: e.degree=5
    review(p)
    score=arrange(p)
    assert [(n.pitch.midi,n.quarterLength) for n in score.parts[0].recurse().notes]==[(67,1)]*4
    for part in score.parts[1:]:
        assert [n.tie.type for n in part.recurse().notes]==["start","continue","continue","stop"]
        assert len({n.pitch.midi for n in part.recurse().notes})==1
    assert score.parts[0].recurse().getElementsByClass("Slur")
    with zipfile.ZipFile(io.BytesIO(export_bundle(p))) as z: z.extractall(tmp_path)
    tree=ET.parse(tmp_path/"score.musicxml")
    assert tree.findall(".//notations/slur")
    assert tree.findall(".//notations/tenuto") or tree.findall(".//articulations/tenuto")
    assert tree.findall(".//tie")
    midi=converter.parse(tmp_path/"concert.mid")
    assert len(midi.parts[0].recurse().notes)==4
    assert all(len(part.recurse().notes)==1 for part in midi.parts[1:])

def test_melody_tie_roundtrip(tmp_path):
    p=synthetic("block"); m=p.measures[0]
    for e in m.events: e.degree=5
    for e,t in zip(m.events,["start","continue","continue","stop"]): e.tie=t
    review(p)
    with zipfile.ZipFile(io.BytesIO(export_bundle(p))) as z: z.extractall(tmp_path)
    midi=converter.parse(tmp_path/"concert.mid")
    assert len(midi.parts[0].recurse().notes)==1
    assert midi.parts[0].recurse().notes[0].quarterLength==4

@pytest.mark.parametrize("ties",[["start","","",""],["stop","","",""],["start","stop","continue",""]])
def test_invalid_tie_chains(ties):
    p=synthetic()
    for e,t in zip(p.measures[0].events,ties): e.tie=t
    with pytest.raises(ValueError,match="延音線"): review(p)

def test_mocked_pdf_bundle_contains_all_four_pdfs(monkeypatch):
    def render(source,target,executable): target.write_bytes(b"%PDF-1.4 mock")
    monkeypatch.setattr("trio.export.musescore_path",lambda x:"fake")
    monkeypatch.setattr("trio.export.render_pdf",render)
    with zipfile.ZipFile(io.BytesIO(export_bundle(review(synthetic()),True))) as z:
        assert sorted(n for n in z.namelist() if n.endswith(".pdf"))==["alto_1.pdf","alto_2.pdf","alto_3.pdf","score.pdf"]

def test_sample_ui_cannot_export_and_autoedit_invalidates():
    app=AppTest.from_file(str(ROOT/"app.py")).run()
    next(b for b in app.button if b.label=="載入《黃昏的故鄉》圖片案例").click().run()
    assert not app.exception
    assert app.session_state.project.source_sha256
    assert next(b for b in app.button if b.label=="編曲並建立正式輸出 ZIP").disabled
    assert any("不確定" in x.value for x in app.info)

def test_editor_change_revokes_confirmation():
    p=review(synthetic())
    app=AppTest.from_file(str(ROOT/"app.py"))
    app.session_state.project=p
    app.session_state.revision=1
    app.run()
    assert not app.exception
    app.session_state["notes_1_0"]={"edited_rows":{0:{"degree":2}},"added_rows":[],"deleted_rows":[]}
    app.run()
    assert not app.exception
    assert app.session_state.project.measures[0].events[0].degree==2
    assert not app.session_state.project.measures[0].review_hash
    assert next(b for b in app.button if b.label=="編曲並建立正式輸出 ZIP").disabled

@pytest.mark.parametrize("field,value",[("degree",True),("degree",1.5),("triplet","false")])
def test_strict_input_types(field,value):
    data=synthetic().measures[0].events[0].model_dump();data[field]=value
    with pytest.raises(ValueError): Event.model_validate(data)


def test_enka_low_melody_kept_exact_with_upper_harmony():
    p=synthetic()
    for e in p.measures[0].events:
        e.degree=5;e.octave=-1
    review(p)
    score=arrange(p)
    assert all(n.pitch.midi==55 for n in score.parts[0].recurse().notes)
    assert all(49<=n.pitch.midi<=80 for part in score.parts for n in part.recurse().notes)
    assert all(any(n.pitch.midi>55 for n in part.recurse().notes) for part in score.parts[1:])


def test_musescore_timeout_message(tmp_path,monkeypatch):
    import subprocess
    from trio.export import render_pdf
    def timeout(*args,**kwargs): raise subprocess.TimeoutExpired("musescore",120)
    monkeypatch.setattr("trio.export.subprocess.run",timeout)
    with pytest.raises(RuntimeError,match="120"):
        render_pdf(tmp_path/"x.xml",tmp_path/"x.pdf","fake")

def test_musescore_cannot_start_message(tmp_path,monkeypatch):
    from trio.export import render_pdf
    def failed(*args,**kwargs): raise OSError("missing")
    monkeypatch.setattr("trio.export.subprocess.run",failed)
    with pytest.raises(RuntimeError,match="啟動"):
        render_pdf(tmp_path/"x.xml",tmp_path/"x.pdf","fake")
