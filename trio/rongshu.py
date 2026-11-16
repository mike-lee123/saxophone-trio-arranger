"""Explicit editorial route for the supplied Rong Shu Xia numbered score."""
ROUTE=[1,2,1,2]+list(range(3,35))+list(range(11,31))+list(range(35,39))
SECTIONS=[(1,'A','Intro repeats',1,2),(5,'B','Intro theme',3,10),(13,'C','Verse 1',11,30),(33,'D','Interlude',31,34),(37,'E','Verse 2',11,30),(57,'F','Coda',35,38)]

# Sounding pitches; an explicitly requested intro arrangement, not a transcription.
LYRICAL_INTRO=[
    [(67,1),(64,1),(72,1),(67,1)],
    [(67,.5),(69,.5),(71,.5),(72,.5),(71,1),(69,.5),(67,.5)],
    [(64,.5),(67,.5),(72,1),(71,.5),(69,.5),(67,1)],
    [(67,1),(69,.5),(71,.5),(72,.5),(74,.5),(76,1)],
]
FLOWING_INTRO=[
    [(72,.5),(67,.5),(72,.5),(76,.5),(74,.5),(72,.5),(69,.5),(71,.5)],
    [(72,.5),(74,.5),(76,.5),(74,.5),(72,.5),(71,.5),(69,.5),(67,.5)],
    [(72,.5),(76,.5),(74,.5),(72,.5),(74,.5),(76,.5),(77,.5),(76,.5)],
    [(74,.5),(76,.5),(77,.5),(79,.5),(77,.5),(76,.5),(74,.5),(77,.5)],
]

def apply_intro_variation(score,p):
    if p.ensemble!='sat' or p.edition_profile!='rongshu_60' or p.intro_variation not in ('lyrical','flowing'):return score
    from music21 import note,expressions,dynamics
    soprano=score.parts[0]
    flowing=p.intro_variation=='flowing'
    for number,pattern in enumerate(FLOWING_INTRO if flowing else LYRICAL_INTRO,1):
        measure=soprano.measure(number)
        for n in list(measure.notesAndRests):measure.remove(n)
        for i,(midi,beats) in enumerate(pattern):
            n=note.Note(midi,quarterLength=beats)
            n.volume.velocity=((64,67,70,73)[number-1]+(2 if i%2==0 else 0)) if flowing else 55+(i%3)*2
            measure.append(n)
        if number==1:measure.insert(0,expressions.TextExpression('Cantabile · poco a poco cresc.' if flowing else 'Dolce · lyrical intro variation'))
    if flowing:soprano.insert(0,dynamics.Crescendo(soprano.measure(1).notes[0],soprano.measure(4).notes[-1]))
    return score
