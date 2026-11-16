# coding: utf-8
import io,json,hashlib
from pathlib import Path
import numpy as np
import soundfile as sf
import mido
import pytest
from streamlit.testing.v1 import AppTest
from trio.model import Project,confirm,confirm_structure
from trio.audio import load_bank,preview_score,render_project,render_score,Performance,audio_bundle
from trio.playback import score_notes,write_concert_midi
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module")
def bank():return load_bank()

@pytest.fixture
def p():
    p=Project.model_validate_json((ROOT/"examples/synthetic.json").read_text(encoding="utf-8"))
    p.style="enka";p.tempo=120
    return p

def test_recorded_bank_complete_read_only(bank):
    assert len(bank)==64
    assert all(not data.flags.writeable and np.isfinite(data).all() for data in bank.values())
    assert max(abs(data).max() for data in bank.values())>0

def test_preview_does_not_create_or_alter_confirmation(p):
    before=p.model_dump_json();s=preview_score(p)
    assert len(s.parts)==3 and "DRAFT" in s.metadata.title
    assert p.model_dump_json()==before


def test_formal_audio_blocks_unreviewed_source(p,bank):
    with pytest.raises(ValueError):render_project(p,bank,preview=False)

def test_sampled_audio_has_three_audible_unclipped_stems(p,bank):
    files,report=render_project(p,bank,preview=True)
    assert report["status"]=="UNREVIEWED DRAFT"
    assert report["sample_count"]==64
    assert set(files)=={"mix.wav","alto_1.wav","alto_2.wav","alto_3.wav"}
    for payload in files.values():
        wave,sr=sf.read(io.BytesIO(payload))
        assert sr==44100 and wave.shape==(176400,2)
        assert np.isfinite(wave).all() and 0<abs(wave).max()<.99
    assert report["stats"]["mix"]["clipped_samples"]==0
    import zipfile
    with zipfile.ZipFile(io.BytesIO(audio_bundle(files,report))) as z:
        assert "DRAFT_mix.wav" in z.namelist()
    assert not p.measures[0].review_hash

def test_confirmed_audio_status_and_source_hash(p,bank):
    for m in p.measures:confirm(m,p.meter,"Synthetic fixture only")
    p.source_complete=True;confirm_structure(p,"Synthetic fixture only")
    files,report=render_project(p,bank)
    assert report["status"]=="HUMAN CONFIRMED SOURCE"
    assert report["project_sha256"]==hashlib.sha256(p.model_dump_json().encode()).hexdigest()

def test_enka_expression_changes_waveform_but_not_notes(p,bank):
    before=p.model_dump_json()
    neutral,r1=render_project(p,bank,Performance("neutral",0,0),preview=True)
    enka,r2=render_project(p,bank,Performance("enka",.9,.1),preview=True)
    a,sr=sf.read(io.BytesIO(neutral["mix.wav"]));b,_=sf.read(io.BytesIO(enka["mix.wav"]))
    assert a.shape==b.shape and not np.allclose(a,b)
    assert r1["note_count"]==r2["note_count"]
    assert p.model_dump_json()==before

def test_no_chord_mutes_only_accompaniment(p):
    for event in p.measures[0].events:event.chord=""
    p.measures[0].events[0].chord="N.C."
    s=preview_score(p)
    assert s.parts[0].recurse().notes
    assert all(not part.recurse().notes for part in s.parts[1:])

def test_midi_and_audio_share_three_sound_event_channels(p,tmp_path):
    s=preview_score(p);notes=score_notes(s,p.tempo)
    path=tmp_path/"concert.mid";write_concert_midi(s,p.tempo,path)
    m=mido.MidiFile(path);on=[msg for msg in mido.merge_tracks(m.tracks) if msg.type=="note_on" and msg.velocity]
    assert {msg.channel for msg in on}=={0,1,2}
    assert sorted((msg.channel,msg.note) for msg in on)==sorted((n.channel,n.midi) for n in notes)
    assert abs(m.length-2)<1e-6

def test_preview_bad_beats_and_ties_still_block(p):
    p.measures[0].events[0].duration="2"
    with pytest.raises(ValueError):preview_score(p)
    p.measures[0].events[0].duration="1";p.measures[0].events[0].tie="start"
    with pytest.raises(ValueError):preview_score(p)

def test_performance_duration_guard(p,bank):
    with pytest.raises(ValueError,match="10"):
        render_score(preview_score(p),p.tempo,bank,max_seconds=1)

def test_full_song_has_all_30_audit_entries_and_no_human_confirmation():
    p=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
    audit=json.loads((ROOT/"examples/huanghun.audit.json").read_text(encoding="utf-8"))
    assert len(p.measures)==len(audit["measures"])==30
    assert all(not row["human_confirmed"] for row in audit["measures"])
    assert all(not m.review_hash and all(e.uncertain for e in m.events) for m in p.measures)
    s=preview_score(p)
    assert s.duration.quarterLength==120
    assert not s.parts[1].measure(20).notes
    assert not s.parts[2].measure(20).notes

def test_ui_generates_draft_audio_and_hides_stale_result(p):
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=30)
    app.session_state.project=p
    app.run()
    assert not app.exception
    next(c for c in app.checkbox if c.label=="我知道這只是未確認草稿的校對試聽").check().run()
    next(b for b in app.button if b.label=="以真實薩克斯取樣產生試奏").click().run()
    assert not app.exception
    assert app.session_state.audio_result["report"]["status"]=="UNREVIEWED DRAFT"
    assert len(app.get("audio"))==4
    next(t for t in app.text_input if t.label=="曲名").set_value("Changed title").run()
    assert not app.get("audio")

@pytest.mark.parametrize("settings",[Performance("bad"),Performance("enka",2),Performance("enka",.5,.9)])
def test_invalid_performance_settings(settings):
    with pytest.raises(ValueError):settings.validate()
