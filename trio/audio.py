# coding: utf-8
"""Offline performance made from actual University of Iowa Alto Sax recordings."""
from dataclasses import dataclass, asdict
from pathlib import Path
import io
import hashlib
import json
import zipfile
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve
from .model import validate_measure, validate_ties
from .arrange import arrange, _style_score
from .playback import score_notes

SAMPLE_RATE=44100
BANK_PATH=Path(__file__).resolve().parents[1]/"assets/iowa_alto_mf.npz"

@dataclass(frozen=True)
class Performance:
    mode: str = "enka"
    expression: float = .7
    room: float = .10
    def validate(self):
        if self.mode not in ("enka","neutral") or not 0<=self.expression<=1 or not 0<=self.room<=.3:
            raise ValueError("試奏設定不合法")

def load_bank(path=BANK_PATH):
    result={}
    path=Path(path)
    source=path
    if not path.is_file():
        manifest=path.with_name(path.name+'.parts.json')
        spec=json.loads(manifest.read_text(encoding='utf-8'))
        pieces=[]
        for item in spec['parts']:
            chunk=(path.parent/item['name']).read_bytes()
            if hashlib.sha256(chunk).hexdigest()!=item['sha256']:
                raise ValueError("Alto sample chunk checksum mismatch")
            pieces.append(chunk)
        payload=b''.join(pieces)
        if hashlib.sha256(payload).hexdigest()!=spec['sha256']:
            raise ValueError("Alto sample bank checksum mismatch")
        source=io.BytesIO(payload)
    with np.load(source,allow_pickle=False) as data:
        for key in data.files:
            style,pitch=key.rsplit("_",1)
            sample=np.array(data[key],dtype=np.float32,copy=True)
            if sample.ndim!=1 or not np.isfinite(sample).all() or len(sample)<22050:raise ValueError("錄音取樣檔損壞")
            sample.setflags(write=False);result[(style,int(pitch))]=sample
    expected={(style,pitch) for style in ("NoVib","Vib") for pitch in range(49,81)}
    if set(result)!=expected:raise ValueError("需要完整 64 個 Alto 錄音單音")
    return result

def preview_score(project):
    """Validate musical structure, never create or change a human confirmation."""
    if not project.measures:raise ValueError("沒有可試奏小節")
    if [m.number for m in project.measures]!=list(range(1,len(project.measures)+1)):raise ValueError("小節編號不連續")
    order=project.performance_order or list(range(1,len(project.measures)+1))
    if len(order)>2000 or any(n<1 or n>len(project.measures) for n in order):raise ValueError("演奏順序不合法")
    for m in project.measures:
        copy=m.model_copy(deep=True)
        for event in copy.events:event.uncertain=False
        validate_measure(copy,project.meter)
    validate_ties(project,order)
    score=_style_score(project)
    score.metadata.title="DRAFT / UNREVIEWED - "+project.title
    return score

def extend_sample(sample,frames):
    if frames<=len(sample):return sample[:frames].copy()
    lo=int(.55*SAMPLE_RATE);hi=min(len(sample)-int(.25*SAMPLE_RATE),int(1.75*SAMPLE_RATE))
    def crossing(pos):
        a=max(1,pos-150);b=min(len(sample)-1,pos+150)
        crossings=np.where((sample[a-1:b-1]<=0)&(sample[a:b]>0))[0]
        return a+int(crossings[np.argmin(abs(a+crossings-pos))]) if len(crossings) else pos
    lo=crossing(lo);hi=crossing(hi);loop=sample[lo:hi].copy()
    if len(loop)<1000:raise ValueError("持續取樣太短")
    fade=min(int(.055*SAMPLE_RATE),len(loop)//5);ramp=np.linspace(0,1,fade,dtype=np.float32)
    output=sample[:hi].copy()
    while len(output)<frames:
        output[-fade:]=output[-fade:]*(1-ramp)+loop[:fade]*ramp
        output=np.concatenate((output,loop[fade:]))
    return output[:frames]

def wav_bytes(data):
    buffer=io.BytesIO();sf.write(buffer,data,SAMPLE_RATE,format="WAV",subtype="PCM_16");return buffer.getvalue()

def render_score(score,bpm,bank,settings=Performance(),max_seconds=600):
    settings.validate();notes=score_notes(score,bpm)
    seconds=float(score.duration.quarterLength)*60/bpm
    if seconds+2>max_seconds:raise ValueError("試奏最長 10 分鐘，請分段產生")
    if not notes:raise ValueError("沒有可試奏的音符")
    length=int((seconds+2)*SAMPLE_RATE);stems=[np.zeros(length,dtype=np.float32) for _ in range(3)]
    for n in notes:
        style="Vib" if settings.mode=="enka" and n.channel==0 and n.duration>=.78 else "NoVib"
        if (style,n.midi) not in bank:raise ValueError("音高超出錄音取樣範圍 Db3-Ab5")
        release=.065 if n.duration<.5 else .10;frames=round((n.duration+release)*SAMPLE_RATE)
        sound=extend_sample(bank[(style,n.midi)],frames)
        attack=min(int(.004*SAMPLE_RATE),len(sound)//8);sound[:attack]*=np.linspace(0,1,attack)
        off=round(n.duration*SAMPLE_RATE);sound[off:]*=np.cos(np.linspace(0,np.pi/2,len(sound)-off))**2
        if settings.mode=="enka":
            strength=settings.expression;t=np.linspace(0,1,len(sound))
            # Phrase-level arc, restrained long-note swell, and gentle release.
            phrase=1+strength*.12*np.sin(n.start*(2*np.pi/(16*60/bpm))-.8)
            sound*=phrase*(1+strength*.10*np.sin(np.pi*np.minimum(t*1.1,1)))
            if n.channel>0 and n.duration>6.4:
                for breath in np.arange(5.8,n.duration,5.8):
                    center=int(breath*SAMPLE_RATE);width=int(.04*SAMPLE_RATE)
                    lo=max(0,center-width);hi=min(len(sound),center+width)
                    shape=np.abs(np.linspace(-1,1,hi-lo))
                    sound[lo:hi]*=1-strength*.65*(1-shape)**2
        gain=(n.velocity/80)**1.25*[1,.76,.70][n.channel]
        sound*=gain;start=round(n.start*SAMPLE_RATE)+[0,176,352][n.channel]
        count=min(len(sound),length-start);stems[n.channel][start:start+count]+=sound[:count]
    ir=np.zeros(int(.25*SAMPLE_RATE),dtype=np.float32)
    for delay,gain in ((.023,.18),(.047,.13),(.083,.095),(.137,.06),(.211,.035)):ir[int(delay*SAMPLE_RATE)]=gain
    mix=np.zeros((length,2),dtype=np.float32)
    for channel,stem in enumerate(stems):
        room=stem+settings.room*fftconvolve(stem,ir)[:length]
        pan=[.5,.28,.72][channel];mix[:,0]+=room*np.cos(pan*np.pi/2);mix[:,1]+=room*np.sin(pan*np.pi/2)
    peak=float(np.max(abs(mix)))
    if not peak or not np.isfinite(mix).all():raise ValueError("試奏未產生有效聲音")
    # Preserve relative dynamics; only prevent digital clipping and very quiet output.
    largest=max(peak,*(float(np.max(abs(stem)))*.707 for stem in stems))
    gain=min(3.5,.86/largest);mix*=gain
    files={"mix.wav":wav_bytes(mix)}
    stats={"mix":{"seconds":length/SAMPLE_RATE,"peak":float(np.max(abs(mix))),"rms":float(np.sqrt(np.mean(mix**2))),"clipped_samples":int(np.sum(abs(mix)>=.999))}}
    for channel,stem in enumerate(stems):
        solo=np.stack((stem,stem),axis=1)*gain*.707
        files[f"alto_{channel+1}.wav"]=wav_bytes(solo)
        stats[f"alto_{channel+1}"]={"peak":float(np.max(abs(solo))),"rms":float(np.sqrt(np.mean(solo**2)))}
    report={"source":"University of Iowa MIS / Michael Giles, November 1997","source_url":"https://theremin.music.uiowa.edu/MISaltosaxophone.html","kind":"actual recorded-note samples sequenced by computer; not a continuous human performance","settings":asdict(settings),"sample_count":len(bank),"note_count":len(notes),"stats":stats,"human_listening_review":False}
    return files,report

def render_project(project,bank,settings=Performance(),preview=False):
    score=preview_score(project) if preview else arrange(project)
    if project.edition_profile=="huanghun_67":
        from .performance_edition import performance_with_fermata
        score=performance_with_fermata(score)
    files,report=render_score(score,project.tempo,bank,settings)
    report["status"]="UNREVIEWED DRAFT" if preview else "EDITORIAL PERFORMANCE EDITION" if project.review_policy=="editorial" else "HUMAN CONFIRMED SOURCE"
    report["project_sha256"]=hashlib.sha256(project.model_dump_json().encode()).hexdigest()
    return files,report

def audio_bundle(files,report):
    buffer=io.BytesIO();prefix="DRAFT_" if report["status"]=="UNREVIEWED DRAFT" else ""
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(prefix+name,data)
        z.writestr("audio_report.json",json.dumps(report,ensure_ascii=False,indent=2))
    return buffer.getvalue()
