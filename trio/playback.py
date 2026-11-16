# coding: utf-8
"""Exact sounding-note events shared by MIDI and recorded-sample playback."""
from dataclasses import dataclass, asdict
from pathlib import Path
from fractions import Fraction
import mido

@dataclass(frozen=True)
class SoundingNote:
    channel: int
    midi: int
    start: float
    duration: float
    velocity: int

def score_notes(score,bpm):
    notes=[];unit=60/float(bpm)
    if len(score.parts)!=3: raise ValueError("需要三個薩克斯聲部")
    for channel,part in enumerate(score.parts):
        pending=None
        for n in part.flatten().notesAndRests:
            if n.isRest:
                if pending: raise ValueError("延音線不可跨休止符")
                continue
            if not n.isNote: raise ValueError("只支援單音聲部")
            start=float(n.offset)*unit;duration=float(n.quarterLength)*unit
            midi=int(n.pitch.midi);velocity=n.volume.velocity or [80,62,55][channel]
            typ=n.tie.type if n.tie else ""
            if typ=="start":
                if pending: raise ValueError("延音線重複起點")
                pending=[channel,midi,start,duration,velocity]
            elif typ in ("continue","stop"):
                if pending is None or pending[1]!=midi or abs(start-(pending[2]+pending[3]))>1e-6:
                    raise ValueError("延音線音高或時間不連續")
                pending[3]+=duration
                if typ=="stop":notes.append(SoundingNote(*pending));pending=None
            else:
                if pending: raise ValueError("延音線缺少終點")
                notes.append(SoundingNote(channel,midi,start,duration,velocity))
        if pending: raise ValueError("延音線缺少終點")
    return sorted(notes,key=lambda n:(n.start,n.channel,n.midi))

def write_concert_midi(score,bpm,path):
    notes=score_notes(score,bpm);unit=60/float(bpm);ticks=480
    midi=mido.MidiFile(ticks_per_beat=ticks)
    meta=mido.MidiTrack();meta.append(mido.MetaMessage("set_tempo",tempo=mido.bpm2tempo(bpm),time=0));midi.tracks.append(meta)
    end_tick=round(float(score.duration.quarterLength)*ticks)
    for channel in range(3):
        track=mido.MidiTrack();midi.tracks.append(track)
        track.append(mido.MetaMessage("track_name",name=score.parts[channel].partName or f"Sax {channel+1}",time=0))
        track.append(mido.Message("program_change",channel=channel,program=score.parts[channel].getInstrument().midiProgram if score.parts[channel].getInstrument().midiProgram is not None else 65,time=0))
        schedule=[]
        for n in notes:
            if n.channel!=channel:continue
            on=round(n.start/unit*ticks);off=round((n.start+n.duration)/unit*ticks)
            schedule.extend([(on,1,mido.Message("note_on",channel=channel,note=n.midi,velocity=n.velocity)),(off,0,mido.Message("note_off",channel=channel,note=n.midi,velocity=0))])
        last=0
        for tick,priority,message in sorted(schedule,key=lambda x:(x[0],x[1])):
            message.time=tick-last;track.append(message);last=tick
        track.append(mido.MetaMessage("end_of_track",time=max(0,end_tick-last)))
    midi.save(path)
