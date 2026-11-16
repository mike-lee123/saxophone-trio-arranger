# coding: utf-8
import io
import json
import zipfile
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import pytest
from music21 import converter, note
from trio.model import Project, Event, confirm, validate_project, validate_measure, confirm_structure
from trio.arrange import arrange, written_score, CONCERT_LOW, CONCERT_HIGH
from trio.export import export_bundle, render_pdf, musescore_path
from trio.vision import recognize

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def draft():
    return Project.model_validate_json((ROOT/"examples/synthetic.json").read_text(encoding="utf-8"))

@pytest.fixture
def reviewed(draft):
    for m in draft.measures: confirm(m,draft.meter,"Test reviewer (synthetic only)")
    draft.source_complete=True
    confirm_structure(draft,"Synthetic source reviewer")
    return draft

def test_unconfirmed_block(draft):
    with pytest.raises(ValueError,match="確認"): export_bundle(draft)

def test_changed_content_blocks(reviewed):
    reviewed.measures[0].events[0].degree=2
    with pytest.raises(ValueError,match="確認"): export_bundle(reviewed)

@pytest.mark.parametrize("field,value",[("uncertain",True),("duration","2")])
def test_invalid_draft(draft,field,value):
    setattr(draft.measures[0].events[0],field,value)
    with pytest.raises(ValueError): confirm(draft.measures[0],draft.meter,"Tester")

def test_empty_reviewer(draft):
    with pytest.raises(ValueError): confirm(draft.measures[0],draft.meter,"")

def test_rational_triplets(draft):
    e=draft.measures[0].events[0].model_copy(update={"duration":"1/2","triplet":True})
    assert e.beats()==Fraction(1,3)
    m=draft.measures[0]; m.events=[e.model_copy() for _ in range(12)]
    confirm(m,draft.meter,"Tester")
    draft.source_complete=True; confirm_structure(draft,"Tester")
    score=arrange(draft)
    assert sum(n.quarterLength for n in score.parts[0].recurse().notesAndRests)==4
    assert score.parts[0].recurse().notes[0].duration.tuplets
    assert e.model_copy(update={"triplet":False,"dots":2}).beats()==Fraction(7,8)

def test_transposition_range_and_voices(reviewed):
    c=arrange(reviewed); w=written_score(c)
    assert c.parts[0].recurse().notes[0].nameWithOctave=="C4"
    assert w.parts[0].recurse().notes[0].nameWithOctave=="A4"
    for cp,wp in zip(c.parts,w.parts):
        for cn,wn in zip(cp.recurse().notes,wp.recurse().notes):
            assert wn.pitch.midi-cn.pitch.midi==9
            assert CONCERT_LOW<=cn.pitch.midi<=CONCERT_HIGH
    voices=[list(p.recurse().notes) for p in c.parts]
    for ns in zip(*voices): assert ns[0].pitch.midi>ns[1].pitch.midi>ns[2].pitch.midi
    assert all(len(p.recurse().getElementsByClass(note.Rest))==1 for p in c.parts)

@pytest.mark.parametrize("octave",[-2,2])
def test_range_reject(reviewed,octave):
    reviewed.measures[0].events[0].octave=octave
    confirm(reviewed.measures[0],reviewed.meter,"Tester")
    with pytest.raises(ValueError): arrange(reviewed)

def test_exports_roundtrip(reviewed,tmp_path):
    data=export_bundle(reviewed)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert set(z.namelist())=={"score.musicxml","alto_1.musicxml","alto_2.musicxml","alto_3.musicxml","concert.mid","reviewed_project.json","manifest.json"}
        z.extractall(tmp_path)
    tree=ET.parse(tmp_path/"score.musicxml")
    assert len(tree.findall(".//part"))==3
    assert [k.text for k in tree.findall(".//key/fifths")]==["3"]*3
    assert [x.text for x in tree.findall(".//transpose/chromatic")]==["-9"]*3
    parsed=converter.parse(tmp_path/"score.musicxml")
    assert parsed.parts[0].recurse().notes[0].nameWithOctave=="A4"
    sounding=parsed.toSoundingPitch()
    assert sounding.parts[0].recurse().notes[0].pitch.midi==60
    midi=converter.parse(tmp_path/"concert.mid")
    assert midi.parts[0].recurse().notes[0].pitch.midi==60
    for i in range(1,4):
        part=converter.parse(tmp_path/f"alto_{i}.musicxml")
        assert len(part.parts)==1
        assert part.parts[0].recurse().getElementsByClass("KeySignature")[0].sharps==3

def test_musescore_failure(tmp_path,monkeypatch):
    monkeypatch.setattr("trio.export.subprocess.run",lambda *a,**k: SimpleNamespace(returncode=1,stderr=b"failed"))
    with pytest.raises(RuntimeError): render_pdf(tmp_path/"x.xml",tmp_path/"x.pdf","fake")
    with pytest.raises(ValueError): musescore_path(str(tmp_path/"missing.exe"))

def test_pdf_invocation(tmp_path,monkeypatch):
    def fake(args,**kwargs):
        assert args[1]=="-o"
        Path(args[2]).write_bytes(b"%PDF-1.4 simulated")
        return SimpleNamespace(returncode=0,stderr=b"")
    monkeypatch.setattr("trio.export.subprocess.run",fake)
    render_pdf(tmp_path/"x.xml",tmp_path/"x.pdf","fake")

def test_vision_strips_review(reviewed):
    from PIL import Image
    data=io.BytesIO(); Image.new("RGB",(20,20)).save(data,format="PNG")
    payload={k:reviewed.model_dump()[k] for k in ("title","meter","source_key","tempo","measures","source_notes")}
    def create(**kwargs):
        schema=kwargs["text"]["format"]["schema"]
        assert "review_hash" in schema["$defs"]["Measure"]["required"]
        return SimpleNamespace(output_text=json.dumps(payload))
    client=SimpleNamespace(responses=SimpleNamespace(create=create))
    result=recognize(data.getvalue(),"fake",client=client)
    assert result.source_sha256
    assert all(not m.review_hash and not m.reviewer for m in result.measures)
    with pytest.raises(ValueError): validate_project(result)

def test_app_smoke():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"app.py")).run()
    assert not app.exception
    next(b for b in app.button if b.label=="建立空白人工輸入專案").click().run()
    assert not app.exception
    assert app.session_state.project.title=="黃昏的故鄉"


def test_triplet_xml_and_rest_roundtrip(draft,tmp_path):
    e=draft.measures[0].events[0].model_copy(update={"duration":"1/2","triplet":True})
    draft.measures[0].events=[e.model_copy() for _ in range(9)] + [e.model_copy(update={"degree":0,"duration":"1","triplet":False})]
    confirm(draft.measures[0],draft.meter,"Tester")
    draft.source_complete=True; confirm_structure(draft,"Tester")
    with zipfile.ZipFile(io.BytesIO(export_bundle(draft))) as z: z.extractall(tmp_path)
    tree=ET.parse(tmp_path/"score.musicxml")
    assert len(tree.findall(".//time-modification"))==27
    score=converter.parse(tmp_path/"score.musicxml")
    for part in score.parts:
        assert sum(n.quarterLength for n in part.recurse().notesAndRests)==4


def test_pickup_and_middle_capacity(draft):
    m=draft.measures[0]
    m.events=m.events[:1]; m.capacity="1"
    confirm(m,draft.meter,"Tester")
    draft.source_complete=True; confirm_structure(draft,"Tester")
    assert arrange(draft).parts[0].measure(1).paddingLeft==3
    draft.measures=[m.model_copy(deep=True) for _ in range(3)]
    for i,bar in enumerate(draft.measures,1):
        bar.number=i; confirm(bar,draft.meter,"Tester")
    with pytest.raises(ValueError,match="首尾"): validate_project(draft)


def test_accidentals_and_octave(draft):
    from trio.arrange import event_pitch
    e=draft.measures[0].events[0].model_copy(update={"degree":4,"accidental":1,"octave":1})
    assert event_pitch(e).nameWithOctave=="F#5"
    e.accidental=-1
    assert event_pitch(e).nameWithOctave=="F-5"
