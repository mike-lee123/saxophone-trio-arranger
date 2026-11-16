# coding: utf-8
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from .arrange import arrange, written_score
from . import __version__

def musescore_path(configured=""):
    if configured:
        p=Path(configured)
        if not p.is_file(): raise ValueError("MuseScore 路徑不存在")
        return str(p)
    configured=os.getenv("MUSESCORE_PATH","")
    if configured: return musescore_path(configured)
    for name in ("MuseScore4.exe","MuseScore4","mscore","musescore"):
        p=shutil.which(name)
        if p: return p
    for version in ("MuseScore 4","MuseScore 3"):
        p=Path(os.getenv("ProgramFiles","C:/Program Files"))/version/"bin"/("MuseScore4.exe" if version.endswith("4") else "MuseScore3.exe")
        if p.is_file(): return str(p)
    raise ValueError("找不到 MuseScore，請指定 MuseScore4.exe 完整路徑")

def render_pdf(source,target,executable):
    try:
        result=subprocess.run([executable,"-o",str(target),str(source)],capture_output=True,timeout=120, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("MuseScore 轉檔超過 120 秒，請檢查是否有首次啟動畫面或檔案問題") from exc
    except OSError as exc:
        raise RuntimeError("無法啟動 MuseScore，請檢查執行檔路徑與安裝") from exc
    if result.returncode or not target.is_file() or not target.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("MuseScore PDF 轉檔失敗: "+result.stderr.decode(errors="replace")[-500:])

def export_bundle(p, pdf=False, executable=""):
    concert=arrange(p); written=written_score(concert)
    with tempfile.TemporaryDirectory(prefix="sax-trio-") as tmp:
        folder=Path(tmp)
        from music21 import expressions,stream
        full=copy.deepcopy(written)
        # One rehearsal mark in the full score; every independent part keeps it.
        for part in full.parts[1:]:
            for measure in part.getElementsByClass(stream.Measure):
                for mark in list(measure.getElementsByClass(expressions.RehearsalMark)):measure.remove(mark)
        full.write("musicxml",fp=str(folder/"score.musicxml"))
        from music21 import stream
        for i,part in enumerate(written.parts,1):
            s=stream.Score(); s.metadata=copy.deepcopy(written.metadata)
            s.insert(0,copy.deepcopy(part)); s.atSoundingPitch=False
            s.write("musicxml",fp=str(folder/f"alto_{i}.musicxml"))
        from .playback import write_concert_midi
        playback=concert
        if p.edition_profile=="huanghun_67":
            from .performance_edition import performance_with_fermata
            playback=performance_with_fermata(concert)
        write_concert_midi(playback,p.tempo,folder/"concert.mid")
        (folder/("edition_project.json" if p.review_policy=="editorial" else "reviewed_project.json")).write_text(p.model_dump_json(indent=2),encoding="utf-8")
        if pdf:
            exe=musescore_path(executable)
            for source in folder.glob("*.musicxml"): render_pdf(source,source.with_suffix(".pdf"),exe)
        manifest={"version":__version__,"title":p.title,"style":p.style,"review_policy":p.review_policy,"editorial_notes":p.editorial_notes,"source_sha256":p.source_sha256,"structure_reviewer":p.structure_reviewer,"performance_order":p.performance_order or [m.number for m in p.measures],"musicxml":"Alto written A major; Eb transposition","midi":"Concert C major","pdf":pdf,"files":sorted(x.name for x in folder.iterdir())}
        (folder/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        import io
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
            for f in folder.iterdir(): z.write(f,f.name)
        return buf.getvalue()
