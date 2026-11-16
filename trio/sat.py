"""Concert-pitch Soprano / Alto / Tenor voicing with explicit melody octave."""
from music21 import stream,instrument,clef,key,meter,tempo,metadata,harmony,note,tie,dynamics,expressions,duration

RANGES=((56,87),(49,80),(44,75))  # Written Bb3-F6 for each transposing sax.
NAMES=('Soprano','Alto','Tenor')
FILES=('soprano','alto','tenor')

def build_sat(p):
    from .arrange import event_pitch,rhythm
    score=stream.Score()
    score.metadata=metadata.Metadata(title=p.title+' — Soprano · Alto · Tenor')
    score.metadata.add('arranger','Saxophone Trio Arranger')
    parts=[]
    for name,klass in zip(NAMES,(instrument.SopranoSaxophone,instrument.AltoSaxophone,instrument.TenorSaxophone)):
        part=stream.Part(id=name);part.partName=name+' Sax'
        for obj in (clef.TrebleClef(),klass(),key.Key('C'),meter.TimeSignature(p.meter),tempo.MetronomeMark(number=p.tempo),dynamics.Dynamic('mp' if name=='Soprano' else 'p')):
            part.insert(0,obj)
        part.insert(0,expressions.TextExpression({'ballad':'Cantabile · dolce','classical':'Legato · espressivo','soft_jazz':'Soft jazz · straight eighths'}[p.sat_style]))
        part.atSoundingPitch=True;parts.append(part)
    previous=None;active='C'
    for number,source in enumerate(p.performance_order or range(1,len(p.measures)+1),1):
        bar=p.measures[source-1];bars=[stream.Measure(number=number) for _ in range(3)]
        for e in bar.events:
            if e.chord:active=e.chord
            if not e.degree:
                ns=[note.Rest() for _ in range(3)]
            else:
                lead=int(event_pitch(e).midi)+12*p.lead_octave
                if not RANGES[0][0]<=lead<=RANGES[0][1]:
                    raise ValueError(f'小節 {source}: Soprano 主旋律超出音域，請明確選擇主旋律八度')
                if active in ('NC','N.C.'):
                    ns=[note.Note(lead),note.Rest(),note.Rest()];previous=None
                else:
                    chord=harmony.ChordSymbol(active);pcs={n.pitchClass for n in chord.pitches};root=chord.root().pitchClass
                    middle_pcs=set(pcs)
                    if p.sat_style=='soft_jazz':
                        # Restrained 6th/9th colour over major/minor triads; no swing rewrite.
                        middle_pcs.update({(root+2)%12,(root+9)%12})
                    pairs=[(a,t) for a in range(RANGES[1][0],RANGES[1][1]+1)
                           for t in range(RANGES[2][0],RANGES[2][1]+1)
                           if a%12 in middle_pcs and t%12 in pcs and t<a<lead and a-t<=19 and lead-a<=19
                           and (lead-a)%12 not in (1,11)]
                    if not pairs:raise ValueError(f'小節 {source}: SAT 音域無法配置，請調整主旋律八度')
                    def cost(pair):
                        a,t=pair
                        motion=sum(abs(x-y) for x,y in zip(pair,previous)) if previous else 0
                        root_cost=0 if t%12==root else 2 if t%12==(root+7)%12 else 5
                        spacing=abs(lead-a-7)*.2+abs(a-t-9)*.2
                        colour=0 if a%12 in pcs else (1 if p.sat_style=='soft_jazz' else 8)
                        parallel=0
                        if previous and p.sat_style=='classical':
                            parallel=6 if (a-t)%12 in (0,7) and (previous[0]-previous[1])%12==(a-t)%12 and (a-previous[0])*(t-previous[1])>0 else 0
                        return motion*1.3+root_cost+spacing+colour+parallel+max(0,t-55)*1.2+abs(t-50)*.15
                    previous=min(pairs,key=cost)
                    ns=[note.Note(lead),note.Note(previous[0]),note.Note(previous[1])]
                if e.tie:ns[0].tie=tie.Tie(e.tie)
            for i,(b,n) in enumerate(zip(bars,ns)):
                n.duration=rhythm(e)
                if n.isNote:n.volume.velocity=(76,58,53)[i]
                b.append(n)
        if number==1:
            for b in bars:b.paddingLeft=meter.TimeSignature(p.meter).barDuration.quarterLength-b.duration.quarterLength
        for part,b in zip(parts,bars):part.append(b)
    # Let middle/bass breathe on melody rests; merge repeated tones within each phrase.
    for part in parts[1:]:
        run=[]
        def finish():
            if len(run)>1:
                for i,n in enumerate(run):n.tie=tie.Tie('start' if i==0 else 'stop' if i==len(run)-1 else 'continue')
        for n in part.recurse().notesAndRests:
            if n.isRest or (run and n.pitch.midi!=run[-1].pitch.midi):finish();run=[]
            if n.isNote:run.append(n)
        finish()
    for part in parts:score.insert(0,part)
    score.atSoundingPitch=True
    # Collapse within-bar repeats that already sound as one tied note.
    # Keep incoming/outgoing ties at bar boundaries, so timing stays unchanged.
    for part in score.parts[1:]:
        for measure in part.getElementsByClass(stream.Measure):
            groups=[]
            for n in list(measure.notesAndRests):
                if groups and n.isNote and not n.duration.tuplets and not any(old.duration.tuplets for old in groups[-1]) and groups[-1][-1].isNote and n.pitch.midi==groups[-1][-1].pitch.midi and groups[-1][-1].tie and groups[-1][-1].tie.type in ('start','continue'):
                    groups[-1].append(n)
                else:groups.append([n])
            for group in groups:
                if len(group)<2:continue
                first,last=group[0],group[-1]
                incoming=first.tie and first.tie.type in ('continue','stop')
                outgoing=last.tie and last.tie.type in ('continue','start')
                first.duration=duration.Duration(sum((n.quarterLength for n in group),0))
                first.tie=tie.Tie('continue' if incoming and outgoing else 'stop' if incoming else 'start') if incoming or outgoing else None
                for n in group[1:]:measure.remove(n)
    if p.edition_profile in ('huanghun_67','rongshu_60'):
        if p.edition_profile=='huanghun_67':
            from .performance_edition import SECTIONS
        else:
            from .rongshu import SECTIONS
        from music21 import bar as barline
        for start,letter,label,a,b in SECTIONS:
            for part in score.parts:part.measure(start).insert(0,expressions.RehearsalMark(letter+' '+label))
        # Explicit C/E/G close, below the raised soprano G.
        last=len(p.performance_order)
        for i,pitch in ((1,'E4'),(2,'C3')):
            final=score.parts[i].measure(last)
            for n in list(final.notesAndRests):final.remove(n)
            final.append(note.Note(pitch,quarterLength=4))
        # Reset any accompaniment tie that previously ran into a changed final bar.
        for part in score.parts[1:]:
            prev=list(part.measure(last-1).notes)
            if prev and prev[-1].tie and prev[-1].tie.type in ('start','continue'):
                if prev[-1].tie.type=='continue':prev[-1].tie=tie.Tie('stop')
                else:prev[-1].tie=None
        for part in score.parts:
            final=part.measure(last);final.rightBarline=barline.Barline('final')
            if p.edition_profile=='huanghun_67' and final.notes:final.notes[-1].expressions.append(expressions.Fermata())
    if p.edition_profile=='rongshu_60':
        from .rongshu import apply_intro_variation
        score=apply_intro_variation(score,p)
    return score
