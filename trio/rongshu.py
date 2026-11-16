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
TRIO_SOPRANO=[
    [(67,.5),(72,.5),(76,.5),(72,.5),(69,.5),(67,.5),(64,.5),(67,.5)],
    FLOWING_INTRO[1],
    [(72,.5),(74,.5),(77,.5),(76,.5),(77,.5),(76,.5),(74,.5),(76,.5)],
    FLOWING_INTRO[3],
]
TRIO_ALTO=[
    [(60,.5),(64,.5),(55,.5),(60,.5),(64,.5),(60,1),(64,.5)],
    [(60,1),(64,.5),(67,.5),(64,1),(62,.5),(59,.5)],
    [(65,1),(69,.5),(72,.5),(69,.5),(65,.5),(64,.5),(62,.5)],
    [(62,.5),(65,.5),(67,1),(65,.5),(62,.5),(59,1)],
]
TRIO_TENOR=[[(48,2),(55,2)],[(45,2),(52,2)],[(50,2),(45,2)],[(55,2),(50,2)]]

def apply_intro_variation(score,p):
    if p.ensemble!='sat' or p.edition_profile!='rongshu_60' or p.intro_variation not in ('lyrical','flowing','trio'):return score
    from music21 import note,expressions,dynamics
    soprano=score.parts[0]
    flowing=p.intro_variation in ('flowing','trio')
    patterns=TRIO_SOPRANO if p.intro_variation=='trio' else FLOWING_INTRO if flowing else LYRICAL_INTRO
    for number,pattern in enumerate(patterns,1):
        measure=soprano.measure(number)
        for n in list(measure.notesAndRests):measure.remove(n)
        for i,(midi,beats) in enumerate(pattern):
            n=note.Note(midi,quarterLength=beats)
            n.volume.velocity=((64,67,70,73)[number-1]+(2 if i%2==0 else 0)) if flowing else 55+(i%3)*2
            measure.append(n)
        if number==1:measure.insert(0,expressions.TextExpression('Cantabile · poco a poco cresc.' if flowing else 'Dolce · lyrical intro variation'))
    if flowing:soprano.insert(0,dynamics.Crescendo(soprano.measure(1).notes[0],soprano.measure(4).notes[-1]))
    if p.intro_variation=='trio':
        for voice,patterns,label in ((1,TRIO_ALTO,'Broken chords · sotto voce'),(2,TRIO_TENOR,'Warm bass · legato')):
            for number,pattern in enumerate(patterns,1):
                measure=score.parts[voice].measure(number)
                for n in list(measure.notesAndRests):measure.remove(n)
                for index,(midi,beats) in enumerate(pattern):
                    n=note.Note(midi,quarterLength=beats)
                    n.volume.velocity=(50 if voice==2 else 52)+(number-1)*2+(2 if index==0 else 0)
                    measure.append(n)
                if number==1:measure.insert(0,expressions.TextExpression(label))
    return score
