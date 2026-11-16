# coding: utf-8
from pathlib import Path
from fractions import Fraction
import io,zipfile
import pytest
from music21 import converter
from trio.model import Project,validate_project,clear_reviews
from trio.performance_edition import create_edition,performance_with_fermata,ROUTE,SECTIONS
from trio.arrange import arrange
from trio.playback import score_notes
from trio.export import export_bundle
ROOT=Path(__file__).resolve().parents[1]
AUTH="請幫完成完整演出路線的正式樂譜 不須人工確認"
@pytest.fixture(scope="module")
def edition():
    p=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
    before=p.model_dump_json();result,score=create_edition(p,AUTH)
    assert p.model_dump_json()==before
    return result,score

def test_explicit_editorial_authority_does_not_fake_human_review(edition):
    p,s=edition;validate_project(p)
    assert p.review_policy=="editorial" and p.editorial_authorization==AUTH
    assert all(not m.reviewer and not m.review_hash for m in p.measures)
    assert all(e.uncertain for m in p.measures for e in m.events)

def test_editorial_content_tamper_rejected(edition):
    p,s=edition;p=p.model_copy(deep=True);p.tempo=80
    with pytest.raises(ValueError,match="編訂"):validate_project(p)

def test_import_resets_editorial_authorization(edition):
    p,s=edition;p=p.model_copy(deep=True);clear_reviews(p)
    assert p.review_policy=="human" and not p.editorial_authorization
    with pytest.raises(ValueError):validate_project(p)

def test_three_verses_coda_and_intro_route(edition):
    p,s=edition
    assert len(ROUTE)==67 and s.duration.quarterLength==268
    assert ROUTE[:5]==list(range(1,6))
    assert ROUTE[5:27]==ROUTE[27:49]==list(range(6,28))
    assert ROUTE[49:64]==list(range(6,21)) and ROUTE[64:]==[28,29,30]
    assert [x[0] for x in SECTIONS]==[1,6,22,28,44,50,65]
    for part in s.parts:
        bars=list(part.getElementsByClass("Measure"));assert len(bars)==67
        assert all(Fraction(b.duration.quarterLength)==4 for b in bars)
        assert all(49<=n.pitch.midi<=80 for n in part.recurse().notes)

def test_all_original_large_note_melodies_preserved(edition):
    from trio.arrange import event_pitch
    p,s=edition
    for number,source in enumerate(ROUTE,1):
        original=p.measures[source-1].events;actual=list(s.parts[0].measure(number).notesAndRests)
        assert len(original)==len(actual)
        for e,n in zip(original,actual):
            assert Fraction(n.quarterLength)==e.beats()
            assert n.isRest==(e.degree==0)
            if e.degree:assert n.pitch.midi==event_pitch(e).midi

def test_printed_small_notes_are_orchestrated_in_alto2(edition):
    p,s=edition
    for number,source in enumerate(ROUTE,1):
        if source in (5,27):
            notes=list(s.parts[1].measure(number).notesAndRests)
            assert [n.pitch.midi for n in notes[1:4]]==[55,55,55]
            assert all(n.duration.tuplets for n in notes[1:4])
        if source==17:
            assert [n.pitch.midi for n in s.parts[1].measure(number).notes]==[65,67,67,67,74,55,55,55]

def test_fermata_audio_realization_is_shared(edition):
    p,s=edition;performance=performance_with_fermata(s)
    assert performance.duration.quarterLength==269
    before=score_notes(s,p.tempo);after=score_notes(performance,p.tempo)
    assert len(before)==len(after)
    for a,b in zip(before,after):
        assert (a.channel,a.midi,a.start)==(b.channel,b.midi,b.start)
        assert b.duration>=a.duration
    assert all(p.measure(67).notes[-1].expressions for p in s.parts)

def test_formal_editorial_bundle_roundtrip(edition,tmp_path):
    p,s=edition
    with zipfile.ZipFile(io.BytesIO(export_bundle(p))) as z:z.extractall(tmp_path)
    result=converter.parse(tmp_path/"score.musicxml").toSoundingPitch()
    actual=score_notes(result,p.tempo);expected=score_notes(s,p.tempo)
    assert len(actual)==len(expected)
    assert [(n.channel,n.midi) for n in actual]==[(n.channel,n.midi) for n in expected]
    assert all(abs(a.start-b.start)<1e-6 and abs(a.duration-b.duration)<1e-6 for a,b in zip(actual,expected))


def test_final_sounding_chord_has_complete_tonic(edition):
    p,s=edition;pitches=[]
    for part in s.parts:
        for n in part.measure(67).notes:
            if n.offset<=3<n.offset+n.quarterLength:pitches.append(n.pitch.pitchClass)
    assert set(pitches)=={0,4,7}
    assert s.metadata.composer is None


def test_ui_editorial_button_enables_formal_without_fake_confirmation():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=30).run()
    next(b for b in app.button if b.label=="載入完整演出編訂版（免人工確認）").click().run()
    assert not app.exception
    p=app.session_state.project
    assert p.review_policy=="editorial" and len(p.performance_order)==67
    assert all(not m.reviewer for m in p.measures)
    assert not next(b for b in app.button if b.label=="編曲並建立正式輸出 ZIP").disabled

def test_ui_editorial_change_requires_explicit_reseal():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=30).run()
    next(b for b in app.button if b.label=="載入完整演出編訂版（免人工確認）").click().run()
    next(t for t in app.text_input if t.label=="曲名").set_value("Edited performance edition").run()
    assert next(b for b in app.button if b.label=="編曲並建立正式輸出 ZIP").disabled
    next(b for b in app.button if b.label=="重新封存編訂路線（免人工確認）").click().run()
    assert not app.exception
    assert not next(b for b in app.button if b.label=="編曲並建立正式輸出 ZIP").disabled


def test_profile_route_change_is_rejected_even_with_new_seal(edition):
    from trio.model import seal_editorial_edition
    p,s=edition;p=p.model_copy(deep=True);p.performance_order=p.performance_order[:-1]
    with pytest.raises(ValueError,match="67"):
        seal_editorial_edition(p,AUTH,p.editorial_notes)
