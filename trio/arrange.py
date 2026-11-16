# coding: utf-8
"""Deterministic chord-tone lower voices with nearest-motion selection."""
from itertools import combinations
from music21 import stream, note, pitch, duration, instrument, key, meter, tempo, metadata, harmony, dynamics, articulations, spanner, expressions, tie, clef
from .model import validate_project

CONCERT_LOW, CONCERT_HIGH = 49, 80  # written Bb3..F6, conservative alto range

def event_pitch(e):
    p=pitch.Pitch(["C","D","E","F","G","A","B"][e.degree-1]+str(4+e.octave))
    if e.accidental: p.accidental=e.accidental
    return p

def rhythm(e):
    from fractions import Fraction
    d=duration.Duration(Fraction(e.duration))
    d.dots=e.dots
    if e.triplet: d.appendTuplet(duration.Tuplet(3,2))
    return d

def arrange(p):
    validate_project(p)
    return _style_score(p)


def _style_score(p):
    score=_build_score(p)
    if p.style=="enka_motion":
        from .fills import enrich_accompaniment
        score,_=enrich_accompaniment(score,p)
    if p.edition_profile=="huanghun_67":
        from .performance_edition import apply_edition_profile
        score=apply_edition_profile(score,p)
    return score


def _build_score(p):
    """Internal score builder; formal exports must use arrange()."""
    score=stream.Score(); score.metadata=metadata.Metadata(title=p.title+" — Alto Trio", composer="Saxophone Trio Arranger 1.5")
    parts=[]
    for i in range(3):
        part=stream.Part(id=f"Alto{i+1}"); part.partName=f"Alto Sax {i+1}"
        part.insert(0,clef.TrebleClef()); part.insert(0,instrument.AltoSaxophone()); part.insert(0,key.Key("C")); part.insert(0,meter.TimeSignature(p.meter))
        part.insert(0,tempo.MetronomeMark(number=p.tempo)); part.atSoundingPitch=True; parts.append(part)
    active="C"; previous=None
    order=p.performance_order or list(range(1,len(p.measures)+1))
    previous_lead=None
    for playback_number,source_number in enumerate(order,1):
        bar=p.measures[source_number-1]
        bars=[stream.Measure(number=playback_number) for _ in range(3)]
        for e in bar.events:
            if e.chord: active=e.chord
            if not e.degree: ns=[note.Rest() for _ in range(3)]
            else:
                lead=event_pitch(e)
                if not CONCERT_LOW<=lead.midi<=CONCERT_HIGH: raise ValueError(f"小節 {bar.number}: 主旋律超出 Alto 音域，請人工調整八度")
                if active in ("N.C.","NC"):
                    ns=[note.Note(lead),note.Rest(),note.Rest()]
                    previous=None; previous_lead=None
                else:
                    pcs={x.pitchClass for x in harmony.ChordSymbol(active).pitches}
                    pool=[x for x in range(CONCERT_LOW,int(lead.midi)) if x%12 in pcs]
                    pairs=[(hi,lo) for lo,hi in combinations(pool,2) if lead.midi-lo<=24 and hi-lo<=12]
                    if not pairs and p.style in ("enka","enka_motion"):
                        # A low melody (e.g. concert G3) may not leave room for
                        # two lower altos. Keep it exact and place harmony above.
                        pool=[x for x in range(CONCERT_LOW,CONCERT_HIGH+1) if x%12 in pcs and x!=lead.midi]
                        pairs=[(hi,lo) for lo,hi in combinations(pool,2)
                               if hi-lo<=12 and max(abs(lead.midi-hi),abs(lead.midi-lo))<=19]
                    if not pairs: raise ValueError(f"小節 {bar.number}: 無法在 Alto 音域內配置和聲，請調整音域或使用演歌模式")
                    def cost(pair):
                        movement=sum(abs(a-b) for a,b in zip(pair,previous)) if previous else 0
                        if p.style == "block":
                            return movement + abs(lead.midi-pair[0]-4)*.4 + abs(pair[0]-pair[1]-5)*.2
                        # Enka preset: singing thirds/sixths, root/fifth foundation,
                        # restrained inner movement, penalty for exposed parallels.
                        interval_to_second=(int(lead.midi)-pair[0])%12
                        consonance=0 if interval_to_second in (3,4,8,9) else 3
                        symbol=harmony.ChordSymbol(active)
                        foundation={symbol.root().pitchClass, (symbol.root().pitchClass+7)%12}
                        bass_penalty=0 if pair[1]%12 in foundation else 2
                        leaps=sum(max(0,abs(a-b)-5) for a,b in zip(pair,previous)) if previous else 0
                        parallels=0
                        if previous and previous_lead is not None:
                            for voice,old in zip(pair,previous):
                                if ((lead.midi-voice)%12 in (0,7)
                                    and (previous_lead-old)%12==(lead.midi-voice)%12
                                    and (lead.midi-previous_lead)*(voice-old)>0): parallels+=7
                        return movement*1.6 + leaps*2 + consonance + bass_penalty + parallels + abs(lead.midi-pair[0]-5)*.15
                    pair=min(pairs,key=cost); previous=pair; previous_lead=int(lead.midi)
                    ns=[note.Note(lead),note.Note(pair[0]),note.Note(pair[1])]
            if e.tie: ns[0].tie=tie.Tie(e.tie)
            for b,n in zip(bars,ns): n.duration=rhythm(e); b.append(n)
        if playback_number==1:
            for b in bars:
                b.paddingLeft = meter.TimeSignature(p.meter).barDuration.quarterLength - b.duration.quarterLength
        for part,b in zip(parts,bars): part.append(b)
    if p.style in ("enka","enka_motion"):
        for i,part in enumerate(parts):
            part.insert(0,dynamics.Dynamic("mp" if i==0 else "p"))
            part.insert(0,expressions.TextExpression("Enka · cantabile, dolce" if i==0 else "Legato · sotto voce"))
            for n in part.recurse().notes:
                if n.duration.quarterLength>=1:
                    n.articulations.append(articulations.Tenuto())
                n.volume.velocity=80 if i==0 else (62 if i==1 else 55)
            if i>0:
                # Keep notation on the original rhythm grid; tied repeated
                # accompaniment tones sound as a single sustained note.
                run=[]
                def finish_run():
                    if len(run)>1:
                        for j,n in enumerate(run):
                            n.tie=tie.Tie("start" if j==0 else "stop" if j==len(run)-1 else "continue")
                for n in part.recurse().notesAndRests:
                    if n.isRest or (run and run[-1].pitch.midi!=n.pitch.midi):
                        finish_run(); run=[]
                    if not n.isRest: run.append(n)
                finish_run()
            else:
                # Phrase slurs restart at rests and at two-bar boundaries.
                phrase=[]
                for j,b in enumerate(part.getElementsByClass(stream.Measure),1):
                    for n in b.notesAndRests:
                        if n.isRest:
                            if len(phrase)>1: part.insert(0,spanner.Slur(phrase))
                            phrase=[]
                        else: phrase.append(n)
                    if j%2==0:
                        if len(phrase)>1: part.insert(0,spanner.Slur(phrase))
                        phrase=[]
                if len(phrase)>1: part.insert(0,spanner.Slur(phrase))
    for part in parts: score.insert(0,part)
    score.atSoundingPitch=True
    return score

def written_score(concert):
    written=concert.toWrittenPitch(inPlace=False)
    for part in written.parts:
        for measure in part.getElementsByClass(stream.Measure):
            measure.makeAccidentals(useKeySignature=key.KeySignature(3), overrideStatus=True, inPlace=True)
    return written
