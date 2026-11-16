"""Open shipped performance packs in memory and check their required contents."""
from pathlib import Path
import hashlib,io,json,zipfile

def pack_available(root,name):
    base=Path(root)/'assets'/name
    return base.is_file() or base.with_name(base.name+'.parts.json').is_file()

def read_pack(root,name):
    base=Path(root)/'assets'/name
    manifest=base.with_name(base.name+'.parts.json')
    if not manifest.is_file():return base.read_bytes()
    spec=json.loads(manifest.read_text(encoding='utf-8'));pieces=[]
    for item in spec['parts']:
        if Path(item['name']).name!=item['name']:raise ValueError('Invalid part filename')
        content=(base.parent/item['name']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=item['sha256']:raise ValueError('Part checksum mismatch: '+item['name'])
        pieces.append(content)
    payload=b''.join(pieces)
    if hashlib.sha256(payload).hexdigest()!=spec['sha256']:raise ValueError('Performance archive checksum mismatch')
    return payload

def inspect_pack(data):
    if len(data)>40*1024*1024:raise ValueError('演出資料包限40MB')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sum(item.file_size for item in z.infolist())>100*1024*1024:raise ValueError('資料包解壓大小過大')
        report=json.loads(z.read('演出與聲音檢查.json'));route=json.loads(z.read('演出路線.json'))
        sat=report.get('ensemble')=='sat'
        names=('soprano','alto','tenor') if sat else ('alto_1','alto_2','alto_3')
        pdfs=['三部總譜_正式演出.pdf']+([x+' 分譜_正式演出.pdf' for x in ('Soprano','Alto','Tenor')] if sat else [f'Alto {i} 分譜_正式演出.pdf' for i in (1,2,3)])
        mp3s=['mix.mp3']+[x+'.mp3' for x in names] if sat else ['三部合奏_完整演出.mp3']+[f'Alto{i}_完整試奏.mp3' for i in (1,2,3)]
        required=pdfs+mp3s+['來源簡譜.jpg','演出路線與編訂說明.pdf','score.musicxml','concert.mid']+[x+'.musicxml' for x in names]
        if not sat:required+=['簡譜總譜_Alto_A調_正式演出.pdf']+[f'Alto{i}_簡譜_A調_正式演出.pdf' for i in (1,2,3)]
        if any(name not in z.namelist() for name in required):raise ValueError('缺少必要樂譜或音檔，請使用完整演出資料包')
        if len(route['route'])!=report['notated_measures'] or not route['sections']:raise ValueError('演出路線與小節數不符')
        if report['notation_musicxml_roundtrip'] is not True:raise ValueError('缺少樂譜回讀驗證')
    return report,route,names,pdfs,mp3s
