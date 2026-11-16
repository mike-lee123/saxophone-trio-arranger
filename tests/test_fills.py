# coding: utf-8
from pathlib import Path
from fractions import Fraction
import copy
import pytest
from trio.model import Project
from trio.audio import preview_score
from trio.fills import enrich_accompaniment,_chords,_active
from trio.playback import score_notes
from music21 import harmony
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module")
def variant():
    p=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
    old=preview_score(p);new,stats=enrich_accompaniment(old,p)
    return p,old,new,stats

def test_fills_preserve_every_melody_event_and_review(variant):
    p,old,new,stats=variant
    before=p.model_dump_json()
    assert [n for n in score_notes(old,p.tempo) if n.channel==0]==[n for n in score_notes(new,p.tempo) if n.channel==0]
    assert p.model_dump_json()==before
    assert all(not m.review_hash for m in p.measures)

def test_both_lower_voices_have_more_varied_movement(variant):
    p,old,new,stats=variant
    a=score_notes(old,p.tempo);b=score_notes(new,p.tempo)
    for channel in (1,2):
        assert len([n for n in b if n.channel==channel])>2*len([n for n in a if n.channel==channel])
    assert stats["passing_notes"]>10 and stats["bass_passing_notes"]>0

def test_fills_range_exact_bars_and_no_chord(variant):
    p,old,new,stats=variant
    for part in new.parts:
        for bar in part.getElementsByClass("Measure"):
            assert Fraction(bar.duration.quarterLength)==4
            assert all(49<=n.pitch.midi<=80 for n in bar.notes)
    for part in new.parts[1:]:
        assert not part.measure(20).notes
        assert all(n.offset<2 for n in part.measure(19).notes)

def test_passing_notes_step_in_and_resolve(variant):
    p,old,new,stats=variant;chords=_chords(p)
    for v in (1,2):
        timed=[]
        for index,bar in enumerate(new.parts[v].getElementsByClass("Measure")):
            for n in bar.notes:
                symbol=_active(chords[index],Fraction(n.offset))
                pcs={pitch.pitchClass for pitch in harmony.ChordSymbol(symbol).pitches}
                timed.append((index,n,pcs))
        for i,(bar,n,pcs) in enumerate(timed):
            if n.pitch.pitchClass in pcs:continue
            assert Fraction(n.offset).denominator!=1
            assert n.quarterLength<=.5
            assert i>0 and i+1<len(timed)
            assert 1<=abs(n.pitch.midi-timed[i-1][1].pitch.midi)<=2
            assert 1<=abs(n.pitch.midi-timed[i+1][1].pitch.midi)<=2
            assert timed[i+1][1].pitch.pitchClass in timed[i+1][2]

def test_lower_voice_order_at_all_attacks(variant):
    p,old,new,stats=variant
    for bar2,bar3 in zip(new.parts[1].getElementsByClass("Measure"),new.parts[2].getElementsByClass("Measure")):
        times=sorted({Fraction(n.offset) for bar in (bar2,bar3) for n in bar.notesAndRests})
        for t in times:
            pitches=[]
            for bar in (bar2,bar3):
                for n in bar.notesAndRests:
                    if Fraction(n.offset)<=t<Fraction(n.offset)+Fraction(n.quarterLength):
                        pitches.append(None if n.isRest else n.pitch.midi);break
            if all(pitch is not None for pitch in pitches):assert pitches[0]-pitches[1]>=3


def test_public_motion_mode_matches_variant(variant):
    p,old,new,stats=variant
    p=p.model_copy(deep=True);p.style="enka_motion"
    public=preview_score(p)
    assert score_notes(public,p.tempo)==score_notes(new,p.tempo)
    assert not p.structure_hash

def test_streamlit_motion_style_choice():
    from streamlit.testing.v1 import AppTest
    p=Project.model_validate_json((ROOT/"examples/synthetic.json").read_text(encoding="utf-8"))
    app=AppTest.from_file(str(ROOT/"app.py"));app.session_state.project=p;app.run()
    next(s for s in app.selectbox if s.label=="編曲風格").select("enka_motion").run()
    assert not app.exception
    assert app.session_state.project.style=="enka_motion"
