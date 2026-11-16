# coding: utf-8
"""Moving enka accompaniment: chord tones, diatonic links and melodic responses.

The confirmed or draft melody is copied exactly. This is an arrangement variant,
not a change to source-note review or a claim of complete contrapuntal correctness.
"""
from fractions import Fraction
import copy,math
from itertools import product
from music21 import stream,note,harmony,duration

WHITE={0,2,4,5,7,9,11}

def _lead_at(bar,t):
    for n in bar.notesAndRests:
        if Fraction(n.offset)<=t<Fraction(n.offset)+Fraction(n.quarterLength):
            return None if n.isRest else int(n.pitch.midi)
    return None

def _chords(project):
    active="C";result=[]
    for number in project.performance_order or list(range(1,len(project.measures)+1)):
        changes=[];offset=Fraction()
        for event in project.measures[number-1].events:
            if event.chord:active=event.chord;changes.append((offset,active))
            offset+=event.beats()
        if not changes or changes[0][0]!=0:changes.insert(0,(Fraction(),result[-1][-1][1] if result else "C"))
        result.append(changes)
    return result

def _active(changes,t):
    return next(chord for onset,chord in reversed(changes) if onset<=t)

def _long_window(bar):
    spans=[]
    for n in bar.notesAndRests:
        start=Fraction(n.offset);end=start+Fraction(n.quarterLength)
        if n.isRest:continue
        if spans and spans[-1][1]==start and spans[-1][2]==n.pitch.midi and n.tie:
            spans[-1]=(spans[-1][0],end,n.pitch.midi)
        else:spans.append((start,end,n.pitch.midi))
    candidates=[(end-start,start,end) for start,end,pitch in spans if end-start>=Fraction(3,2)]
    if not candidates:return None
    length,start,end=max(candidates)
    begin=Fraction(math.ceil(float(start+Fraction(1,2))*2),2)
    finish=min(end,begin+2)
    return (begin,finish) if finish-begin>=1 else None

def enrich_accompaniment(concert,project):
    """Return a new score; leave the melody, project and its reviews untouched."""
    score=copy.deepcopy(concert)
    if len(score.parts)!=3:raise ValueError("需要三個聲部")
    lead_bars=list(score.parts[0].getElementsByClass(stream.Measure))
    chord_bars=_chords(project)
    if len(lead_bars)!=len(chord_bars):raise ValueError("小節數與演奏順序不符")
    previous=[None,None];last_lead=None;bass_resolution=None;resolution=None;statistics={"bass_passing_notes":0,"passing_notes":0,"alto2_notes":0,"alto3_notes":0,"response_measures":[]}
    sounding_started=False
    for index,lead in enumerate(lead_bars):
        capacity=Fraction(lead.duration.quarterLength);changes=chord_bars[index]
        p2={Fraction(0),min(Fraction(2),capacity),min(Fraction(3),capacity),capacity}
        window=_long_window(lead)
        if window and index%4!=3 and index!=len(lead_bars)-1:
            start,end=window
            p2={p for p in p2 if not start<p<end}
            p2.update(start+Fraction(j,2) for j in range(int((end-start)*2)+1))
            statistics["response_measures"].append(index+1)
        if index%4==1:p3={Fraction(0),Fraction(3,2),Fraction(2),Fraction(3),capacity}
        elif index%4==2:p3={Fraction(0),Fraction(2),Fraction(3),Fraction(7,2),capacity}
        elif index%4==3:p3={Fraction(0),Fraction(1),Fraction(2),capacity}
        else:p3={Fraction(0),Fraction(1),Fraction(2),Fraction(3),capacity}
        if index==len(lead_bars)-1:p2={Fraction(0),Fraction(2),capacity};p3=set(p2)
        for onset,chord in changes:p2.add(onset);p3.add(onset)
        first=next((Fraction(n.offset) for n in lead.notes),None)
        if not sounding_started and first is not None:
            p2.add(first);p3.add(first);cue=first;sounding_started=True
        elif not sounding_started:cue=capacity
        else:cue=Fraction(0)
        p2=sorted(p for p in p2 if 0<=p<=capacity);p3=sorted(p for p in p3 if 0<=p<=capacity)
        bars=[score.parts[v].measure(index+1) for v in (1,2)]
        for bar in bars:
            for n in list(bar.notesAndRests):bar.remove(n)
        schedules=[p2,p3];attacks=sorted(set(p2+p3)-{capacity});held=[None,None];events=[[],[]];current=[None,None]
        for t in attacks:
            changing=[t in schedule for schedule in schedules]
            chord_name=_active(changes,t)
            lead_pitch=_lead_at(lead,t)
            if t<cue or chord_name in ("NC","N.C."):
                for v in range(2):
                    if changing[v]:events[v].append((t,None));held[v]=None
                if chord_name in ("NC","N.C."):previous=[None,None];resolution=None;bass_resolution=None
                continue
            symbol=harmony.ChordSymbol(chord_name);pcs={p.pitchClass for p in symbol.pitches}
            root=symbol.root().pitchClass
            ordered=list(dict.fromkeys(p.pitchClass for p in symbol.pitches))
            third=ordered[1] if len(ordered)>1 else root;fifth=ordered[2] if len(ordered)>2 else root
            beat=int(t);weak=t.denominator!=1
            high_choices=[p for p in range(55,73) if p%12 in pcs]
            allow_passing=changing[0] and weak and previous[0] is not None and window is not None and window[0]<=t<window[1]
            if resolution is not None and changing[0]:
                high_choices=[pitch for pitch in high_choices if 1<=abs(pitch-resolution)<=2]
                allow_passing=False
            if allow_passing:
                next_attack=next(at for at in p2 if at>t)
                next_chord=(_active(chord_bars[index+1],Fraction(0)) if next_attack==capacity and index+1<len(chord_bars) else _active(changes,min(next_attack,capacity-Fraction(1,1000))))
                if next_chord not in ("NC","N.C."):
                    next_pcs={p.pitchClass for p in harmony.ChordSymbol(next_chord).pitches}
                    high_choices += [p for p in range(55,73) if p%12 in WHITE-pcs and 1<=abs(p-previous[0])<=2 and any(1<=abs(p-target)<=2 for target in range(55,73) if target%12 in next_pcs)]
            low_choices=[p for p in range(50,63) if p%12 in pcs]
            if bass_resolution is not None and changing[1]:
                low_choices=[p for p in low_choices if 1<=abs(p-bass_resolution)<=2]
            elif changing[1] and t==Fraction(7,2) and index+1<len(chord_bars) and previous[1] is not None:
                upcoming=_active(chord_bars[index+1],Fraction(0))
                if upcoming not in ("NC","N.C."):
                    next_pcs={p.pitchClass for p in harmony.ChordSymbol(upcoming).pitches}
                    low_choices += [p for p in range(50,63) if p%12 in WHITE-pcs and 1<=abs(p-previous[1])<=2 and any(1<=abs(p-target)<=2 for target in range(50,63) if target%12 in next_pcs)]
            # Explicit shapes vary by phrase, rather than always choosing the
            # nearest common tone (which produces the original static pads).
            hi_pref=[third,fifth,root,third][(beat+index)%4]
            lo_pref=[root,fifth,third,fifth][(beat+index%2)%4]
            hi_pool=high_choices if changing[0] else [held[0]]
            lo_pool=low_choices if changing[1] else [held[1]]
            choices=[]
            for hi,lo in product(hi_pool,lo_pool):
                if hi is None or lo is None:continue
                if not 3<=hi-lo<=17:continue
                cost=0
                for v,pitch in enumerate((hi,lo)):
                    old=previous[v]
                    if changing[v] and old is not None:
                        step=abs(pitch-old);cost+=.45*step+max(0,step-7)*4
                        if step==0:cost+=5 if v==0 else 4
                cost+=0 if hi%12==hi_pref else 2.7
                cost+=0 if lo%12==lo_pref else 3.2
                cost+=abs(hi-62)*.12+abs(lo-55)*.14
                if lo%12 not in pcs:cost-=5
                if hi%12 not in pcs:
                    cost+=1.0
                    # Passing notes are privileged only on the eighth-note
                    # response grid, and remain stepwise from the prior tone.
                    cost-=2.5
                if lead_pitch is not None:
                    for pitch in (hi,lo):
                        interval=abs(lead_pitch-pitch)%12
                        if interval==0:cost+=10
                        if interval in (1,11):cost+=35
                        if interval in (2,10):cost+=3 if weak else 10
                    if hi>lead_pitch:cost+=2
                    if lo>lead_pitch:cost+=3
                    # Prefer a singing third/sixth to the lead on strong beats.
                    if not weak and (lead_pitch-hi)%12 not in (3,4,8,9):cost+=2
                    if last_lead is not None:
                        for old,pitch in zip(previous,(hi,lo)):
                            if old is not None and (lead_pitch-pitch)%12 in (0,7) and (last_lead-old)%12==(lead_pitch-pitch)%12 and (lead_pitch-last_lead)*(pitch-old)>0:cost+=5
                choices.append((cost,hi,lo))
            if not choices:raise ValueError(f"第 {index+1} 小節 {t} 拍無法配置流動和聲")
            _,hi,lo=min(choices)
            if changing[0]:resolution=hi if hi%12 not in pcs else None
            if changing[1]:bass_resolution=lo if lo%12 not in pcs else None
            for v,pitch in enumerate((hi,lo)):
                if changing[v]:
                    events[v].append((t,pitch));held[v]=pitch;previous[v]=pitch
                    statistics["alto2_notes" if v==0 else "alto3_notes"]+=1
                    if v==0 and pitch%12 not in pcs:statistics["passing_notes"]+=1
                    if v==1 and pitch%12 not in pcs:statistics["bass_passing_notes"]+=1
            last_lead=lead_pitch
        for v,bar in enumerate(bars):
            for j,(onset,pitch) in enumerate(events[v]):
                end=events[v][j+1][0] if j+1<len(events[v]) else capacity
                n=note.Rest() if pitch is None else note.Note(pitch)
                n.duration=duration.Duration(end-onset)
                if pitch is not None:n.volume.velocity=(62 if v==0 else 54)+(4 if onset.denominator==1 else -3)
                bar.insert(onset,n)
            if not events[v]:bar.append(note.Rest(quarterLength=capacity))
            if Fraction(bar.duration.quarterLength)!=capacity:raise AssertionError("填充聲部拍值錯誤")
    return score,statistics
