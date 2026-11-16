# coding: utf-8
"""Exact rhythm and content-bound human review records."""
import hashlib
import json
from fractions import Fraction
from typing import Literal, List
from pydantic import BaseModel, Field, ConfigDict
from music21 import harmony

class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    degree: int = Field(ge=0, le=7, description="0=rest; 1..7=C major degree")
    octave: int = Field(ge=-2, le=2, description="relative to C4")
    accidental: int = Field(ge=-1, le=1)
    duration: Literal["1/16", "1/8", "1/4", "1/2", "1", "2", "4", "8"]
    dots: int = Field(ge=0, le=2)
    triplet: bool
    chord: str
    tie: Literal["", "start", "continue", "stop"] = ""
    uncertain: bool

    def beats(self):
        return Fraction(self.duration) * sum((Fraction(1, 2)**i for i in range(self.dots+1))) * (Fraction(2,3) if self.triplet else 1)

class Measure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    number: int = Field(ge=1)
    capacity: str = Field(description="quarter-note beats, e.g. 4 or 1 for pickup")
    events: List[Event]
    annotation: str = ""
    review_hash: str = ""
    reviewer: str = ""
    reviewed_at: str = ""

    def digest(self):
        body=self.model_dump(exclude={"review_hash","reviewer","reviewed_at"})
        return hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()

class Project(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    title: str
    meter: str
    source_key: Literal["C"]
    tempo: int = Field(ge=30,le=240)
    source_sha256: str = ""
    measures: List[Measure]
    style: Literal["enka", "enka_motion", "block"] = "enka"
    ensemble: Literal["alto_trio", "sat"] = "alto_trio"
    sat_style: Literal["ballad", "classical", "soft_jazz"] = "ballad"
    lead_octave: Literal[0, 1] = 0
    intro_variation: Literal["source", "lyrical", "flowing", "trio"] = "source"
    source_notes: str = ""
    performance_order: List[int] = Field(default_factory=list)
    source_complete: bool = False
    structure_hash: str = ""
    structure_reviewer: str = ""
    structure_reviewed_at: str = ""

    review_policy: Literal["human", "editorial"] = "human"
    edition_profile: Literal["", "huanghun_67", "rongshu_60"] = ""
    editorial_authorization: str = ""
    editorial_notes: str = ""
    editorial_hash: str = ""
    editorial_at: str = ""

    def editorial_digest(self):
        body=self.model_dump(exclude={"editorial_hash"})
        for field,default in (("ensemble","alto_trio"),("sat_style","ballad"),("lead_octave",0),("intro_variation","source")):
            if body.get(field)==default:body.pop(field,None)
        return hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()

    def structure_digest(self):
        body=self.model_dump(exclude={"structure_hash", "structure_reviewer", "structure_reviewed_at"})
        for field,default in (("ensemble","alto_trio"),("sat_style","ballad"),("lead_octave",0),("intro_variation","source")):
            if body.get(field)==default:body.pop(field,None)
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

class VisionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)
    title: str
    meter: str
    source_key: Literal["C"]
    tempo: int = Field(ge=30,le=240)
    measures: List[Measure]
    source_notes: str = ""

def validate_measure(m, meter="4/4", require_review=False, allow_uncertain=False):
    from music21 import meter as met
    maximum=Fraction(str(met.TimeSignature(meter).barDuration.quarterLength))
    capacity=Fraction(m.capacity)
    if capacity <= 0 or capacity > maximum:
        raise ValueError(f"小節 {m.number}: 小節拍數不合法")
    if not m.events or sum((e.beats() for e in m.events),Fraction()) != capacity:
        raise ValueError(f"小節 {m.number}: 拍值不符（需要 {capacity} 拍）")
    for e in m.events:
        if e.degree == 0 and (e.octave or e.accidental):
            raise ValueError("休止符不可設定八度或升降記號")
        if e.chord and e.chord not in ("N.C.","NC"):
            try: harmony.ChordSymbol(e.chord)
            except Exception as exc: raise ValueError(f"不支援和弦: {e.chord}") from exc
        if e.uncertain and not allow_uncertain:
            raise ValueError(f"小節 {m.number}: 尚有不確定音符，請人工校正並取消 uncertain")
    if require_review and (m.review_hash != m.digest() or not m.reviewer.strip() or not m.reviewed_at):
        raise ValueError(f"小節 {m.number}: 尚未確認或確認後已修改")

def confirm(m, meter, reviewer):
    from datetime import datetime, timezone
    validate_measure(m,meter)
    if not reviewer.strip(): raise ValueError("請填寫校對者")
    m.review_hash=m.digest(); m.reviewer=reviewer.strip()
    m.reviewed_at=datetime.now(timezone.utc).isoformat()
    return m

def validate_project(p):
    if not p.measures: raise ValueError("沒有可輸出的已確認小節")
    if [m.number for m in p.measures] != list(range(1,len(p.measures)+1)):
        raise ValueError("小節編號須由 1 連續排列")
    for m in p.measures:
        validate_measure(m,p.meter,p.review_policy=="human",allow_uncertain=p.review_policy=="editorial")
        from music21 import meter
        full=Fraction(str(meter.TimeSignature(p.meter).barDuration.quarterLength))
        if Fraction(m.capacity)!=full and m.number not in (1,len(p.measures)):
            raise ValueError("只有首尾小節可以是不完整小節")

    order = p.performance_order or [m.number for m in p.measures]
    if len(order)>2000 or any(n<1 or n>len(p.measures) for n in order):
        raise ValueError("演奏順序須使用現有小節編號，最多 2000 個小節")
    if p.review_policy=="editorial":
        if p.edition_profile=="huanghun_67":
            from .performance_edition import ROUTE
            if order!=ROUTE:raise ValueError("此編訂配置需要完整67小節路線")
        if p.edition_profile=="rongshu_60":
            from .rongshu import ROUTE
            if order!=ROUTE:raise ValueError("榕樹下編訂需要完整60小節路線")
        if not p.performance_order or not p.editorial_authorization.strip() or not p.editorial_notes.strip() or not p.editorial_at:
            raise ValueError("編訂模式需要明確授權、路線及編訂說明")
        if p.editorial_hash!=p.editorial_digest():raise ValueError("編訂內容已修改，需重新封存編訂紀錄")
        validate_ties(p,order)
        return
    if not p.source_complete:
        raise ValueError("請核對來源完整性、反覆／跳轉與演奏順序")
    if (p.structure_hash != p.structure_digest() or not p.structure_reviewer.strip() or not p.structure_reviewed_at):
        raise ValueError("整曲來源與演奏順序尚未確認或已修改")
    validate_ties(p, order)


def validate_ties(p, order):
    from .arrange import event_pitch
    active = None
    for number in order:
        for event in p.measures[number-1].events:
            current = event_pitch(event).midi if event.degree else None
            if active is not None:
                if event.tie not in ("continue", "stop") or current != active:
                    raise ValueError(f"小節 {number}: 延音線必須連接同音高，且不可跨休止符")
            elif event.tie in ("continue", "stop"):
                raise ValueError(f"小節 {number}: 延音線缺少起點")
            if event.tie == "start": active = current
            if event.tie == "stop": active = None
            if event.tie and current is None: raise ValueError("休止符不可使用延音線")
    if active is not None: raise ValueError("延音線缺少終點")


def confirm_structure(p, reviewer):
    from datetime import datetime, timezone
    if not reviewer.strip(): raise ValueError("請填寫校對者")
    if not p.source_complete: raise ValueError("請先確認已完整對照原圖與反覆記號")
    for m in p.measures: validate_measure(m,p.meter,True)
    p.structure_reviewer=reviewer.strip()
    p.structure_reviewed_at=datetime.now(timezone.utc).isoformat()
    p.structure_hash=p.structure_digest()
    validate_project(p)
    return p


def clear_reviews(p):
    p.review_policy="human"
    p.editorial_authorization=p.editorial_notes=p.editorial_hash=p.editorial_at=""
    for m in p.measures: m.review_hash=m.reviewer=m.reviewed_at=""
    p.source_complete=False
    p.structure_hash=p.structure_reviewer=p.structure_reviewed_at=""
    return p


def seal_editorial_edition(p, authorization, notes):
    """Explicit editorial release; never fabricate a human review record."""
    from datetime import datetime,timezone
    if not authorization.strip():raise ValueError("需要使用者明確授權")
    if not notes.strip():raise ValueError("需要編訂說明")
    p.review_policy="editorial"
    p.editorial_authorization=authorization.strip();p.editorial_notes=notes.strip()
    p.editorial_at=datetime.now(timezone.utc).isoformat()
    p.editorial_hash=p.editorial_digest()
    validate_project(p)
    return p
