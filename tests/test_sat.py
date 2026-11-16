from pathlib import Path
import io,zipfile
from fractions import Fraction
import pytest
import mido
from music21 import converter
from trio.model import Project,seal_editorial_edition,validate_project
from trio.performance_edition import create_edition,performance_with_fermata
from trio.arrange import arrange,written_score,event_pitch
from trio.sat import RANGES
from trio.playback import score_notes
from trio.export import export_bundle

ROOT=Path(__file__).resolve().parents[1]

def sat(style='ballad'):
    p=Project.model_validate_json((ROOT/'examples/huanghun.draft.json').read_text(encoding='utf-8'))
    p.ensemble='sat';p.lead_octave=1;p.sat_style=style
    return create_edition(p,'User requests SAT editorial arrangement')[0]

@pytest.mark.parametrize('style',['ballad','classical','soft_jazz'])
def test_sat_range_rhythm_roles_and_explicit_octave(style):
    p=sat(style);s=arrange(p)
    assert [part.partName for part in s.parts]==['Soprano Sax','Alto Sax','Tenor Sax']
    for i,part in enumerate(s.parts):
        assert len(part.getElementsByClass('Measure'))==67
        assert all(RANGES[i][0]<=n.pitch.midi<=RANGES[i][1] for n in part.recurse().notes)
        assert all(Fraction(b.duration.quarterLength)==4 for b in part.getElementsByClass('Measure'))
    for number,source in enumerate(p.performance_order,1):
        actual=list(s.parts[0].measure(number).notesAndRests)
        for e,n in zip(p.measures[source-1].events,actual):
            assert e.beats()==Fraction(n.quarterLength)
            if e.degree:assert n.pitch.midi==event_pitch(e).midi+12
        measures=[part.measure(number) for part in s.parts]
        times=sorted({n.offset for bar in measures for n in bar.notes})
        for time in times:
            current=[next((n for n in bar.notes if n.offset<=time<n.offset+n.quarterLength),None) for bar in measures]
            if all(n is not None for n in current):assert current[2].pitch.midi<current[1].pitch.midi<current[0].pitch.midi
    score_notes(s,p.tempo)  # Validate merged ties, including the changed ending.
    assert performance_with_fermata(s).duration.quarterLength==269

def test_sat_transposes_each_instrument_once_and_roundtrips(tmp_path):
    p=sat();s=arrange(p);w=written_score(s)
    assert [list(part.recurse().getElementsByClass('KeySignature'))[0].sharps for part in w.parts]==[2,3,2]
    for i,offset in enumerate((2,9,14)):
        assert all(b.pitch.midi-a.pitch.midi==offset for a,b in zip(s.parts[i].recurse().notes,w.parts[i].recurse().notes))
    with zipfile.ZipFile(io.BytesIO(export_bundle(p))) as z:
        assert all(n+'.musicxml' in z.namelist() for n in ('soprano','alto','tenor'))
        z.extractall(tmp_path)
    parsed=converter.parse(tmp_path/'score.musicxml').toSoundingPitch()
    expected=score_notes(s,p.tempo);actual=score_notes(parsed,p.tempo)
    assert [(n.channel,n.midi,round(n.start,6),round(n.duration,6)) for n in actual]==[(n.channel,n.midi,round(n.start,6),round(n.duration,6)) for n in expected]
    midi=mido.MidiFile(tmp_path/'concert.mid')
    assert [msg.program for track in midi.tracks for msg in track if msg.type=='program_change']==[64,65,66]
    assert [msg.name for track in midi.tracks for msg in track if msg.type=='track_name']==['Soprano Sax','Alto Sax','Tenor Sax']

def test_sat_out_of_range_rejects_instead_of_secret_octave_change():
    p=sat();p.lead_octave=0
    seal_editorial_edition(p,p.editorial_authorization,p.editorial_notes)
    with pytest.raises(ValueError,match='Soprano'):arrange(p)

def test_ensemble_change_invalidates_editorial_seal():
    p=sat();p.ensemble='alto_trio'
    with pytest.raises(ValueError,match='封存'):validate_project(p)

def test_sat_rest_no_chord_and_approximate_audio_labels():
    from trio.audio import render_project,load_bank,Performance
    p=sat();p.edition_profile='';p.performance_order=[1];p.measures=p.measures[:1]
    for e in p.measures[0].events:e.chord='N.C.'
    seal_editorial_edition(p,p.editorial_authorization,'Single-bar SAT audio test')
    s=arrange(p)
    assert not list(s.parts[1].recurse().notes) and not list(s.parts[2].recurse().notes)
    files,report=render_project(p,load_bank(),Performance('neutral',0,0))
    assert set(files)=={'mix.wav','soprano.wav','alto.wav','tenor.wav'}
    assert 'Actual recorded Soprano / Alto / Tenor' in report['kind']
    assert set(report['instrument_sources'])=={'soprano','alto','tenor'}
    assert report['sample_count']==192

def test_sat_ui_one_click_and_reseal():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    next(b for b in app.button if b.label=='載入組合 C · SAT 完整演出編訂版').click().run()
    assert not app.exception
    assert app.session_state.project.ensemble=='sat'
    assert app.session_state.project.lead_octave==1
    assert not next(b for b in app.button if b.label=='編曲並建立正式輸出 ZIP').disabled

    next(s for s in app.selectbox if s.label=='SAT 音樂風格').set_value('classical').run()
    assert next(b for b in app.button if b.label=='編曲並建立正式輸出 ZIP').disabled
    next(b for b in app.button if b.label=='重新封存編訂路線（免人工確認）').click().run()
    assert not app.exception
    assert not next(b for b in app.button if b.label=='編曲並建立正式輸出 ZIP').disabled


def test_sat_derived_audio_handles_high_soprano_and_low_tenor():
    from trio.audio import render_project,load_bank,Performance
    import soundfile as sf
    p=sat();p.edition_profile=''
    p.measures=[p.measures[23].model_copy(deep=True),p.measures[29].model_copy(deep=True)]
    for i,m in enumerate(p.measures,1):m.number=i
    # A separate low phrase forces tenor below the recorded Alto bank.
    for e in p.measures[1].events:
        e.degree=1;e.octave=-1;e.accidental=0;e.chord='C';e.tie=''
    p.performance_order=[1,2]
    seal_editorial_edition(p,p.editorial_authorization,'Two-bar high/low derived SAT audio check')
    s=arrange(p)
    assert max(n.pitch.midi for n in s.parts[0].recurse().notes)>80
    assert min(n.pitch.midi for n in s.parts[2].recurse().notes)<49
    files,report=render_project(p,load_bank(),Performance('neutral',0,0))
    assert report['stats']['mix']['clipped_samples']==0
    for name in ('soprano.wav','alto.wav','tenor.wav'):
        audio,rate=sf.read(io.BytesIO(files[name]))
        assert abs(audio).max()>0 and abs(audio).max()<1
