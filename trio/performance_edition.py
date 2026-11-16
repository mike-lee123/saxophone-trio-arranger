# coding: utf-8
"""Explicit three-verse concert route and source small-note orchestration."""
from fractions import Fraction
import copy
from music21 import note,duration,expressions,metadata,bar as barline
from .model import seal_editorial_edition
from .arrange import arrange

ROUTE=list(range(1,6))+list(range(6,28))+list(range(6,28))+list(range(6,21))+list(range(28,31))
SECTIONS=[(1,"A","Intro",1,5),(6,"B","Verse 1",6,21),(22,"C","Interlude 1",22,27),(28,"D","Verse 2",6,21),(44,"E","Interlude 2",22,27),(50,"F","Verse 3",6,20),(65,"G","Coda",28,30)]
EDITION_NOTES="三段歌詞演出編訂：1–5；6–27；6–27；6–20；28–30，共67小節。Segno作來源定位，未另加未註明的D.S.命令；第三段從原20接28尾奏。原5/27小字555、10及原17小字555、高2、低555轉配Alto2；大字主旋律保留。末小節Alto2持E4、Alto3持C4，與旋律末音G4收束C大三和弦；末拍Fermata採兩拍長度演奏。"

def create_edition(project,authorization):
    p=project.model_copy(deep=True)
    if len(p.measures)!=30:raise ValueError("此路線專用於這張30小節簡譜")
    p.title="黃昏的故鄉 - Alto 三重奏演出編訂版"
    p.style="enka_motion";p.performance_order=ROUTE.copy();p.edition_profile="huanghun_67"
    seal_editorial_edition(p,authorization,EDITION_NOTES)
    return p,arrange(p)

def apply_edition_profile(score,p):
    if p.performance_order!=ROUTE:raise ValueError("67小節編訂設定與演出路線不符")
    score.metadata=metadata.Metadata(title=p.title)
    score.metadata.add("arranger","Saxophone Trio Arranger - performance edition")
    for start,letter,label,a,b in SECTIONS:
        for part in score.parts:
            part.measure(start).insert(0,expressions.RehearsalMark(letter+" "+label))
    # Small printed notes are an instrumental counterline, not a replacement
    # for the held large-note vocal melody.
    for performed,source in enumerate(ROUTE,1):
        if source not in (5,17,27):continue
        upper=score.parts[1].measure(performed);bass=score.parts[2].measure(performed)
        for bar in (upper,bass):
            for n in list(bar.notesAndRests):bar.remove(n)
        if source in (5,27):
            pattern=[(64,1,False),(55,Fraction(1,3),True),(55,Fraction(1,3),True),(55,Fraction(1,3),True),(60,Fraction(1,2),False),(None,Fraction(1,2),False),(64,1,False)]
            foundation=[(52,2),(55,1),(52,1)]
        else:
            pattern=[(65,1,False),(67,Fraction(1,3),True),(67,Fraction(1,3),True),(67,Fraction(1,3),True),(74,1,False),(55,Fraction(1,3),True),(55,Fraction(1,3),True),(55,Fraction(1,3),True)]
            foundation=[(50,2),(57,1),(50,1)]
        for pitch,beats,triplet in pattern:
            n=note.Rest() if pitch is None else note.Note(pitch)
            if triplet:
                n.duration=duration.Duration("eighth");n.duration.appendTuplet(duration.Tuplet(3,2))
            else:n.duration=duration.Duration(beats)
            if pitch is not None:n.volume.velocity=61
            upper.append(n)
        for pitch,beats in foundation:
            n=note.Note(pitch,quarterLength=beats);n.volume.velocity=54;bass.append(n)
    # The source ends with melody G over C; give the trio an explicit C-root
    # foundation instead of ending with only the duplicated third E.
    for voice,pitch in ((1,"E4"),(2,"C4")):
        final=score.parts[voice].measure(67)
        for n in list(final.notesAndRests):final.remove(n)
        tonic=note.Note(pitch,quarterLength=4);tonic.volume.velocity=58 if voice==1 else 54;final.append(tonic)
    for part in score.parts:
        final=part.measure(67);final.rightBarline=barline.Barline("final")
        if final.notes:final.notes[-1].expressions.append(expressions.Fermata())
    return score

def performance_with_fermata(score):
    """Playback realization: extend the final notated beat from one to two beats."""
    performed=copy.deepcopy(score)
    for part in performed.parts:
        final=part.measure(67)
        for n in final.notesAndRests:
            start=Fraction(n.offset);end=start+Fraction(n.quarterLength)
            if end>3:
                extra=end-max(start,Fraction(3))
                n.duration=duration.Duration(Fraction(n.quarterLength)+extra)
                if start>3:n.offset=start+(start-3)
    return performed
