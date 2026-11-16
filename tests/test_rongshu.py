from pathlib import Path
import io,json,zipfile,hashlib
import pytest
from music21 import converter
from trio.model import Project,validate_project,seal_editorial_edition
from trio.arrange import arrange,event_pitch,written_score
from trio.playback import score_notes
from trio.audio import load_bank,load_instrument_bank
from trio.library import read_pack,inspect_pack
from trio.rongshu import ROUTE

ROOT=Path(__file__).resolve().parents[1]

def project():return Project.model_validate_json((ROOT/'examples/rongshu.performance.json').read_text(encoding='utf-8'))

def test_rongshu_source_route_and_original_melody_octave():
    p=project();validate_project(p)
    assert len(p.measures)==38 and p.performance_order==ROUTE and len(ROUTE)==60
    assert p.ensemble=='sat' and p.lead_octave==0
    assert p.source_sha256==hashlib.sha256((ROOT/'examples/source/rongshu.jpg').read_bytes()).hexdigest()
    s=arrange(p)
    assert s.duration.quarterLength==240
    for i,source in enumerate(ROUTE,1):
        assert all(part.measure(i).duration.quarterLength==4 for part in s.parts)
        if i<=4 and p.intro_variation in ('lyrical','flowing'):continue
        original=p.measures[source-1].events;actual=list(s.parts[0].measure(i).notesAndRests)
        assert len(original)==len(actual)
        for e,n in zip(original,actual):
            assert e.beats()==n.quarterLength and (e.degree==0)==n.isRest
            if e.degree:assert n.pitch.midi==event_pitch(e).midi
    for number in range(1,5):
        assert all(not list(part.measure(number).notes) for part in s.parts[1:])
    assert len(score_notes(s,p.tempo))==461

def test_rongshu_route_reseal_still_rejects_wrong_song_route():
    p=project();p.performance_order=p.performance_order[:-1]
    with pytest.raises(ValueError,match='60'):seal_editorial_edition(p,p.editorial_authorization,p.editorial_notes)

def test_three_real_instrument_banks_are_distinct_and_immutable():
    banks=[load_instrument_bank('soprano'),load_bank(),load_instrument_bank('tenor')]
    assert [len(b) for b in banks]==[64,64,64]
    hashes=[]
    for bank in banks:
        assert all(not x.flags.writeable for x in bank.values())
        hashes.append(hashlib.sha256(bank[('NoVib',60)].tobytes()).hexdigest())
    assert len(set(hashes))==3
    for name in ('soprano','tenor'):
        meta=json.loads((ROOT/'assets'/f'{name}_recorded_manifest.json').read_text(encoding='utf-8'))
        assert meta['instrument']==name and meta['recorded_source_count']>0
        assert all(abs(m['shift_semitones'])<=2 for m in meta['mapping'])
        assert all(len(m['sha256'])==64 and m['instrument']==name for m in meta['source_files'])

def test_rongshu_shipped_pack_matches_engine_and_reports_real_sources(tmp_path):
    raw=read_pack(ROOT,'rongshu-performance.zip');report,route,names,pdfs,mp3=inspect_pack(raw)
    assert report['notated_measures']==60 and report['stats']['mix']['seconds']==202
    assert report['stats']['mix']['clipped_samples']==0 and report['sample_count']==192
    assert report['human_listening_review'] is False
    assert route['route']==ROUTE and list(names)==['soprano','alto','tenor']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        (tmp_path/'score.musicxml').write_bytes(z.read('score.musicxml'))
        assert all(z.read(name).startswith(b'%PDF') for name in pdfs)
    back=converter.parse(tmp_path/'score.musicxml').toSoundingPitch()
    expected=score_notes(arrange(project()),72);actual=score_notes(back,72)
    assert len(actual)==len(expected)
    for a,b in zip(actual,expected):
        assert (a.channel,a.midi)==(b.channel,b.midi)
        assert abs(a.start-b.start)<1e-6 and abs(a.duration-b.duration)<1e-6

def test_dashboard_switches_songs_and_opens_correct_source():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
    assert not app.exception and app.metric[0].value=='60'
    next(s for s in app.selectbox if s.label=='練習聲部').set_value('Tenor').run()
    assert not app.exception and len(app.get('audio'))==1
    next(b for b in app.button if b.label=='在工作台編輯此曲').click().run()
    assert not app.exception
    p=app.session_state.project
    assert p.edition_profile=='rongshu_60' and p.ensemble=='sat' and len(p.measures)==38
    assert not next(b for b in app.button if b.label=='編曲並建立正式輸出 ZIP').disabled
    next(r for r in app.radio if r.label=='工作區').set_value('演出儀表板').run()
    next(s for s in app.selectbox if s.label=='曲目').set_value('黃昏的故鄉 · 三 Alto').run()
    assert not app.exception and app.metric[0].value=='67'
