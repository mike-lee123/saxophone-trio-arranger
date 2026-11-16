from pathlib import Path
import io
import numpy as np
import pytest
import soundfile as sf
from trio.model import Project,seal_editorial_edition,validate_project
from trio.arrange import arrange
from trio.playback import score_notes
from trio.audio import render_score,load_bank,load_instrument_bank,Performance

ROOT=Path(__file__).resolve().parents[1]
def edition(mode='lyrical'):
    p=Project.model_validate_json((ROOT/'examples/rongshu.performance.json').read_text(encoding='utf-8'))
    if p.intro_variation!=mode:
        p.intro_variation=mode
        seal_editorial_edition(p,p.editorial_authorization,'Explicit intro mode for musical regression comparison')
    return p
def source_version():
    p=edition();p.intro_variation='source'
    seal_editorial_edition(p,p.editorial_authorization,'Reference original intro for regression comparison')
    return p

def test_intro_varies_pitch_in_lower_register_and_preserves_rest_of_song():
    p=edition();before=[m.digest() for m in p.measures]
    score=arrange(p)
    new=score_notes(score,72);old=score_notes(arrange(source_version()),72)
    boundary=16*60/72
    intro=[n for n in new if n.channel==0 and n.start<boundary]
    original=[n for n in old if n.channel==0 and n.start<boundary]
    assert len(intro)==23 and len({n.midi for n in intro})>=7
    assert np.mean([n.midi for n in intro])<np.mean([n.midi for n in original])-3
    assert max(n.midi for n in intro)<max(n.midi for n in original)
    assert all(n.velocity<=59 for n in intro)
    assert [n for n in new if n.channel>0 or n.start>=boundary]==[n for n in old if n.channel>0 or n.start>=boundary]
    assert all(score.parts[0].measure(i).duration.quarterLength==4 for i in (1,2,3,4))
    assert [m.digest() for m in p.measures]==before

def test_intro_option_is_bound_to_release_hash():
    p=edition();p.intro_variation='source'
    with pytest.raises(ValueError,match='封存'):validate_project(p)

def test_soft_intro_reduces_high_frequency_ratio_without_clipping():
    p=edition();s=arrange(p)
    for part in s.parts:
        for measure in list(part.getElementsByClass('Measure')):
            if measure.number>4:part.remove(measure)
    banks=(load_instrument_bank('soprano'),load_bank(),load_instrument_bank('tenor'))
    raw,_=render_score(s,72,banks[1],Performance('neutral',0,0),channel_banks=banks,soft_intro=False)
    soft,report=render_score(s,72,banks[1],Performance('neutral',0,0),channel_banks=banks,soft_intro=True)
    def high_ratio(blob):
        data,sr=sf.read(io.BytesIO(blob));mono=data[:8*sr].mean(axis=1)
        power=abs(np.fft.rfft(mono))**2;freq=np.fft.rfftfreq(len(mono),1/sr)
        return power[freq>4000].sum()/power.sum()
    assert high_ratio(soft['mix.wav'])<high_ratio(raw['mix.wav'])*.8
    assert report['stats']['mix']['clipped_samples']==0

def test_flowing_intro_builds_into_theme_without_changing_later_music():
    p=edition('flowing');new=score_notes(arrange(p),72);old=score_notes(arrange(source_version()),72)
    boundary=16*60/72
    intro=[n for n in new if n.channel==0 and n.start<boundary]
    theme=next(n for n in new if n.channel==0 and n.start>=boundary)
    assert len(intro)==32 and len({n.midi for n in intro})>=7
    assert 0<theme.midi-intro[-1].midi<=2
    assert abs(theme.velocity-intro[-1].velocity)<=5
    means=[np.mean([n.velocity for n in intro if bar*4*60/72<=n.start<(bar+1)*4*60/72]) for bar in range(4)]
    assert all(a<b for a,b in zip(means,means[1:]))
    assert [n for n in new if n.channel>0 or n.start>=boundary]==[n for n in old if n.channel>0 or n.start>=boundary]

def test_trio_intro_adds_real_middle_bass_and_register_variety():
    p=edition('trio');s=arrange(p)
    new=score_notes(s,72);old=score_notes(arrange(source_version()),72);boundary=16*60/72
    intro=[n for n in new if n.start<boundary]
    assert {n.channel for n in intro}=={0,1,2}
    assert len([n for n in intro if n.channel==1])>=20
    assert len([n for n in intro if n.channel==2])==8
    lead=[n for n in intro if n.channel==0]
    assert max(n.midi for n in lead)-min(n.midi for n in lead)>=15
    assert 0<next(n for n in new if n.channel==0 and n.start>=boundary).midi-lead[-1].midi<=2
    for measure in range(1,5):
        bars=[part.measure(measure) for part in s.parts]
        assert all(bar.duration.quarterLength==4 for bar in bars)
        for beat in sorted({n.offset for bar in bars for n in bar.notes}):
            active=[next(n for n in bar.notes if n.offset<=beat<n.offset+n.quarterLength) for bar in bars]
            assert active[2].pitch.midi<active[1].pitch.midi<active[0].pitch.midi
    assert [n for n in new if n.start>=boundary]==[n for n in old if n.start>=boundary]
