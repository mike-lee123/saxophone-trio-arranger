# coding: utf-8
"""Optional real-service checks. Never mark a real song reviewed in tests."""
import io
import os
from pathlib import Path
import zipfile
import pytest
from trio.model import Project, confirm, confirm_structure
from trio.vision import recognize
from trio.export import export_bundle
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.getenv("RUN_LIVE_VISION")!="1",reason="Opt in with RUN_LIVE_VISION=1 and OPENAI_API_KEY (paid API)")
def test_live_vision_real_image():
    p=recognize((ROOT/"examples/source/huanghun.jpg").read_bytes(),os.environ["OPENAI_API_KEY"],os.getenv("OPENAI_MODEL","gpt-4.1-mini"))
    assert p.measures
    assert not p.source_complete and all(not m.review_hash for m in p.measures)
    with pytest.raises(ValueError): export_bundle(p)

@pytest.mark.skipif(os.getenv("RUN_MUSESCORE")!="1",reason="Opt in with RUN_MUSESCORE=1 after installing MuseScore")
def test_live_musescore_synthetic():
    p=Project.model_validate_json((ROOT/"examples/synthetic.json").read_text(encoding="utf-8"))
    for m in p.measures: confirm(m,p.meter,"Synthetic integration fixture only")
    p.source_complete=True;confirm_structure(p,"Synthetic integration fixture only")
    with zipfile.ZipFile(io.BytesIO(export_bundle(p,True,os.getenv("MUSESCORE_PATH","")))) as z:
        pdfs=[n for n in z.namelist() if n.endswith(".pdf")]
        assert len(pdfs)==4
        assert all(z.read(n).startswith(b"%PDF-") for n in pdfs)
