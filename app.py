# coding: utf-8
"""Editing workspace with human and explicitly authorized editorial modes."""
import hashlib
import json
import io
from pathlib import Path
import zipfile
import pandas as pd
import streamlit as st
from trio.model import Project, Measure, confirm, confirm_structure, clear_reviews, validate_project, seal_editorial_edition
from trio.performance_edition import create_edition
from trio.vision import recognize
from trio.export import export_bundle, musescore_path
from trio.audio import Performance, load_bank, render_project, audio_bundle
import os

ROOT=Path(__file__).parent
st.set_page_config(page_title="Saxophone Trio Arranger 1.6.2",page_icon="🎷",layout="wide")
st.title("🎷 Saxophone Trio Arranger v1.6.2")
st.caption("Concert C → 三 Alto／組合 C：Soprano + Alto + Tenor · MusicXML · Concert MIDI · MuseScore PDF")
if st.session_state.get("project") and st.session_state.project.review_policy=="editorial":
    st.info("目前為使用者授權的演出編訂模式：演奏路線已展開，不要求逐小節人工確認。")
else:
    st.warning("辨識內容都是待校對草稿。一般模式須逐小節確認；本曲也可明確選擇完整演出編訂版，免人工簽認。")

def load_project(project, source=None):
    if source and not project.source_sha256:
        project.source_sha256=hashlib.sha256(source).hexdigest()
    st.session_state.pop("case_audit",None)
    st.session_state.pop("audio_result",None)
    st.session_state.project=clear_reviews(project)
    st.session_state.revision=st.session_state.get("revision",0)+1
    st.session_state.invalid_bars={}
    st.session_state.pop("bundle",None)
    st.session_state.source_image=source

with st.sidebar:
    st.header("辨識與輸出")
    entered_api=st.text_input("OpenAI API Key（僅供本次連線）",type="password")
    # Server credentials are never placed into a browser widget.
    try:
        server_api=st.secrets.get("OPENAI_API_KEY","")
    except FileNotFoundError:
        server_api=""
    api=entered_api or server_api or os.getenv("OPENAI_API_KEY","")
    if not entered_api and api:st.caption("已使用站台金鑰；圖片辨識會使用站台的 API 額度。")
    model=st.text_input("Vision 模型",value=os.getenv("OPENAI_MODEL","gpt-4.1-mini"))
    reviewer=st.text_input("人工校對者姓名")
    pdf=st.checkbox("同時產生 MuseScore PDF")
    exe=st.text_input("MuseScore 執行檔（留空自動搜尋）",value=os.getenv("MUSESCORE_PATH",""))
    try:
        detected=musescore_path(exe)
        st.caption("MuseScore：已找到執行檔")
    except ValueError:
        st.caption("MuseScore：尚未設定；仍可輸出 XML / MIDI")
    st.divider()
    if st.button("載入《黃昏的故鄉》圖片案例"):
        project=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
        load_project(project,(ROOT/"examples/source/huanghun.jpg").read_bytes())
        st.session_state.case_audit=json.loads((ROOT/"examples/huanghun.audit.json").read_text(encoding="utf-8"))
        st.rerun()
    st.caption("內附 30 小節 AI 初校草稿與逐小節核對重點，人工確認仍為 0/30。")
    if st.button("載入完整演出編訂版（免人工確認）"):
        base=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
        edition,_=create_edition(base,"使用者明確選擇完整演出編訂版，免逐小節人工確認")
        load_project(base,(ROOT/"examples/source/huanghun.jpg").read_bytes())
        st.session_state.project=edition
        st.session_state.case_audit=json.loads((ROOT/"examples/huanghun.audit.json").read_text(encoding="utf-8"))
        st.rerun()


    if st.button("載入組合 C · SAT 完整演出編訂版"):
        base=Project.model_validate_json((ROOT/"examples/huanghun.draft.json").read_text(encoding="utf-8"))
        base.ensemble="sat";base.lead_octave=1;base.sat_style="ballad"
        edition,_=create_edition(base,"使用者選擇組合 C 完整演出編訂，免逐小節人工確認")
        seal_editorial_edition(edition,edition.editorial_authorization,"67小節演出路線；SAT改編：主旋律明確提高一個八度，Alto中音和聲、Tenor低音支撐。SAT不套用原三Alto版小字填充；結尾C大三和弦及Fermata。")
        load_project(base,(ROOT/"examples/source/huanghun.jpg").read_bytes())
        st.session_state.project=edition
        st.session_state.case_audit=json.loads((ROOT/"examples/huanghun.audit.json").read_text(encoding="utf-8"))
        st.rerun()


    if st.button("載入《榕樹下》· SAT 演出編訂版"):
        edition=Project.model_validate_json((ROOT/"examples/rongshu.performance.json").read_text(encoding="utf-8"))
        load_project(edition.model_copy(deep=True),(ROOT/"examples/source/rongshu.jpg").read_bytes())
        st.session_state.project=edition
        st.rerun()


upload_image=st.file_uploader("上傳簡譜 JPG / PNG（最多 20 MB）",type=["jpg","jpeg","png"])
source=upload_image.getvalue() if upload_image else st.session_state.get("source_image")
if source:
    if len(source)>20*1024*1024:
        st.error("圖片限 20 MB"); st.stop()
    with st.expander("查看原始簡譜",expanded=True):
        st.image(source,caption="校對時請逐音對照原圖；不要把歌詞、跳轉記號當成程式指令",width=850)
    if st.button("以 AI Vision 辨識整張圖片",disabled=not api):
        try:
            with st.spinner("辨識中；回傳後仍需逐小節人工校對…"):
                result=recognize(source,api,model)
                load_project(result,source)
            st.rerun()
        except Exception as exc:
            st.error(f"辨識未完成（{type(exc).__name__}）。請檢查 API 金鑰、模型權限與圖片清晰度；不完整回應不會取代現有草稿。")

with st.expander("匯入 / 建立草稿"):
    upload_json=st.file_uploader("匯入 JSON（重新清除全部確認）",type="json")
    if st.button("載入 JSON",disabled=upload_json is None):
        try:
            project=Project.model_validate_json(upload_json.getvalue())
            load_project(project,source)
            st.rerun()
        except Exception as exc: st.error(str(exc))
    if st.button("建立空白人工輸入專案"):
        project=Project(title="黃昏的故鄉",meter="4/4",source_key="C",tempo=80,measures=[Measure(number=1,capacity="4",events=[])])
        load_project(project,source)
        st.rerun()

if "project" not in st.session_state:
    st.info("可在左側載入附圖案例，或上傳簡譜進行辨識。沒有 API 金鑰也可手動輸入、校對與匯出。")
    if (ROOT/"examples/演歌取樣試聽.mp3").exists():
        st.caption("先聽實錄取樣的演歌表情示範（未確認草稿）：")
        st.audio((ROOT/"examples/演歌取樣試聽.mp3").read_bytes(),format="audio/mpeg")
    st.stop()
p=st.session_state.project
revision=st.session_state.get("revision",0)
invalid=st.session_state.setdefault("invalid_bars",{})
if source and p.source_sha256 and hashlib.sha256(source).hexdigest()!=p.source_sha256:
    st.error("目前圖片與草稿來源不同，請切回原圖或重新辨識。")
    st.stop()

st.subheader("1 · 曲目設定")
p.ensemble=st.selectbox("樂器組合",["alto_trio","sat"],index=0 if p.ensemble=="alto_trio" else 1,format_func=lambda v:"三支 Alto Sax" if v=="alto_trio" else "組合 C：Soprano + Alto + Tenor",key=f"ensemble_{revision}")
if p.ensemble=="sat":
    p.sat_style=st.selectbox("SAT 音樂風格",["ballad","classical","soft_jazz"],index=["ballad","classical","soft_jazz"].index(p.sat_style),format_func=lambda v:{"ballad":"抒情 · 歌唱旋律與柔和長音","classical":"古典 · 和弦配置與聲部連接","soft_jazz":"柔和爵士 · 六度與九度色彩（直八分）"}[v],key=f"sat_style_{revision}")
    p.lead_octave=st.selectbox("Soprano 主旋律八度",[1,0],index=0 if p.lead_octave==1 else 1,format_func=lambda v:"來源主旋律提高一個八度" if v else "保留來源主旋律實音八度",key=f"lead_octave_{revision}")
    st.caption("Soprano 高音主旋律 · Alto 中音和聲 · Tenor 低音支撐。Concert C → Soprano D、Alto A、Tenor D；Tenor 記譜提高大九度。來源低於 Soprano 音域時請明確選擇提高八度。")
    if p.edition_profile=="rongshu_60":
        intro_options=["flowing","lyrical","source"]
        p.intro_variation=st.selectbox("榕樹下前奏",intro_options,index=intro_options.index(p.intro_variation),format_func=lambda v:{"flowing":"流動漸強 · 自然接入主題（推薦）","lyrical":"柔和分解和弦與順階填充","source":"原譜前奏"}[v],key=f"intro_{revision}")
a,b,c,d=st.columns([3,1,1,2])
p.title=a.text_input("曲名",p.title,key=f"title_{revision}")
p.meter=b.text_input("拍號",p.meter,key=f"meter_{revision}")
p.tempo=c.number_input("速度",30,240,p.tempo,key=f"tempo_{revision}")
p.style=d.selectbox("編曲風格",["enka_motion","enka","block"],index={"enka_motion":0,"enka":1,"block":2}[p.style],
    format_func=lambda x:{"enka_motion":"日本演歌 · 流動和聲與填充","enka":"日本演歌 · 原版延音","block":"三部同節奏和聲"}[x],key=f"style_{revision}",disabled=p.ensemble=="sat")
if p.review_policy=="editorial":
    if p.ensemble=="sat":st.info(p.editorial_notes+" 修改組合、風格或八度後，請於第3區重新封存。")
    else:st.info("本版演出路線："+p.editorial_notes)
elif p.source_notes:st.info("來源辨識備註："+p.source_notes)

st.subheader("2 · 逐小節人工校對")
reviewed=sum(bool(m.reviewer) and m.review_hash==m.digest() for m in p.measures)
if p.review_policy=="human":st.progress(reviewed/max(1,len(p.measures)),text=f"人工確認 {reviewed}/{len(p.measures)} 小節")
else:st.caption("目前採演出編訂模式；下方為來源資料，人工簽認不是此版的輸出條件。")
st.caption("表格修改會立即送入草稿並取消該小節確認。音級 0=休止、1=C4；八度 -1=降低八度；升降 -1/0/1；duration 以四分音符為 1 拍。八分三連音填 1/2 並勾 triplet。dots 為節奏附點，並非八度點。chord 空白延續前和弦（起始預設 C）；降和弦如 B-，N.C. 表示只奏主旋律。tie 為延音線起點 start／中段 continue／終點 stop；圓滑線不填。")

if p.measures:
    index=st.selectbox("選擇印刷小節",range(len(p.measures)),format_func=lambda i:f"第 {i+1} 小節",key=f"measure_index_{revision}")
    m=p.measures[index]
    audit=st.session_state.get("case_audit")
    if audit and source and audit["source_sha256"]==hashlib.sha256(source).hexdigest():
        from PIL import Image
        entry=audit["measures"][index]
        with Image.open(io.BytesIO(source)) as original:
            st.image(original.crop(entry["crop"]),caption=f"原圖第 {entry['source_row']} 列：請對照第 {m.number} 小節",width="stretch")
        st.info("AI 初校核對重點（仍待人工確認）："+entry["check"])
    label="已確認" if m.review_hash==m.digest() and m.reviewer else "待校對"
    st.write(f"**第 {m.number} 小節：{label}**")
    columns=["degree","octave","accidental","duration","dots","triplet","chord","tie","uncertain"]
    seed_key=f"seed_{revision}_{index}"
    if seed_key not in st.session_state:
        st.session_state[seed_key]=pd.DataFrame([e.model_dump() for e in m.events],columns=columns).astype({
            "degree":"Int64","octave":"Int64","accidental":"Int64","duration":"string","dots":"Int64",
            "triplet":"boolean","chord":"string","tie":"string","uncertain":"boolean"})
    edited=st.data_editor(st.session_state[seed_key],key=f"notes_{revision}_{index}",num_rows="dynamic",hide_index=True,width="stretch",
        column_config={
            "degree":st.column_config.NumberColumn("音級",min_value=0,max_value=7,step=1,default=1,required=True),
            "octave":st.column_config.NumberColumn("八度",min_value=-2,max_value=2,step=1,default=0,required=True),
            "accidental":st.column_config.NumberColumn("升降",min_value=-1,max_value=1,step=1,default=0,required=True),
            "duration":st.column_config.SelectboxColumn("拍值",options=["1/16","1/8","1/4","1/2","1","2","4","8"],default="1",required=True),
            "dots":st.column_config.NumberColumn("附點",min_value=0,max_value=2,step=1,default=0,required=True),
            "triplet":st.column_config.CheckboxColumn("三連音",default=False,required=True),
            "chord":st.column_config.TextColumn("和弦",default=""),
            "tie":st.column_config.SelectboxColumn("延音線",options=["","start","continue","stop"],default=""),
            "uncertain":st.column_config.CheckboxColumn("不確定",default=True,required=True)})
    capacity=st.text_input("本小節拍數（4/4 通常填 4；弱起可縮短）",m.capacity,key=f"capacity_{revision}_{index}")
    annotation=st.text_input("小節備註（反覆、D.S.、Coda 等）",m.annotation,key=f"annotation_{revision}_{index}")
    try:
        records=edited.to_dict("records")
        for record in records:
            for field in ("chord","tie"):
                if pd.isna(record.get(field)): record[field]=""
        candidate=Measure(number=m.number,capacity=capacity,annotation=annotation,events=records)
        if candidate.digest()!=m.digest():
            p.measures[index]=candidate; m=candidate
            st.session_state.pop("bundle",None)
        invalid.pop(index,None)
        actual=sum((event.beats() for event in m.events),start=__import__("fractions").Fraction())
        st.caption(f"實際拍值：{actual} / 應有：{capacity}")
    except Exception as exc:
        invalid[index]=str(exc); st.error("尚未儲存："+str(exc))
    if st.button("我已逐音核對，清除此小節不確定標記",disabled=index in invalid or not reviewer.strip() or p.review_policy=="editorial"):
        for event in m.events:event.uncertain=False
        m.review_hash=m.reviewer=m.reviewed_at=""
        st.session_state.revision=revision+1
        st.session_state[f"measure_index_{revision+1}"]=index
        st.session_state.pop("bundle",None)
        st.rerun()
    if st.button("已逐音對照原圖，確認此小節",disabled=index in invalid or p.review_policy=="editorial"):
        try:
            confirm(m,p.meter,reviewer)
            st.success(f"第 {m.number} 小節已由 {reviewer} 確認")
        except Exception as exc: st.error(str(exc))
else:
    index=-1

left,right=st.columns(2)
if left.button("在此小節後新增"):
    p.measures.insert(index+1,Measure(number=index+2,capacity="4",events=[]))
    for i,m in enumerate(p.measures,1): m.number=i
    p.performance_order=[]
    load_project(p,source); st.rerun()
if right.button("刪除此小節",disabled=not p.measures):
    p.measures.pop(index)
    for i,m in enumerate(p.measures,1): m.number=i
    p.performance_order=[]
    load_project(p,source); st.rerun()
if invalid: st.error("有尚未儲存的無效小節，請回到對應小節修正後再輸出。")

st.subheader("3 · 全曲完整性與演奏順序")
st.caption("反覆與 D.S.／Coda 由人工展開。輸入印刷小節編號，如 1,2,3,2,3,4；留空依印刷順序演奏一次。輸出將依此順序重新編為連續小節，不保留跳轉符號。")
order=st.text_input("演奏順序",value=",".join(map(str,p.performance_order)),key=f"order_{revision}")
order_error=False
try:
    p.performance_order=[int(v.strip()) for v in order.replace("，",",").split(",") if v.strip()]
except ValueError:
    order_error=True; st.error("演奏順序只能填小節編號，以逗號分隔。")
if p.review_policy=="human":
    p.source_complete=st.checkbox("我已完整核對來源所有小節、調性、反覆、跳轉、結尾及上述演奏順序",value=p.source_complete,key=f"complete_{revision}")
    if st.button("確認全曲來源與演奏順序",disabled=bool(invalid) or order_error):
        try:
            confirm_structure(p,reviewer)
            st.success("全曲已確認，可以編曲並正式輸出。")
        except Exception as exc: st.error(str(exc))
else:
    st.caption("編訂模式保留來源與授權紀錄，不虛填人工校對者。修改來源或路線後，請重新封存此版。")
    if st.button("重新封存編訂路線（免人工確認）",disabled=bool(invalid) or order_error):
        try:
            seal_editorial_edition(p,p.editorial_authorization or "使用者明確選擇免人工確認的編訂輸出",p.editorial_notes+ (" SAT改編：Soprano主旋律、Alto中聲部、Tenor低聲部；來源小字填充不沿用；主旋律八度設定="+str(p.lead_octave) if p.ensemble=="sat" and "SAT改編" not in p.editorial_notes else ""))
            st.success("編訂紀錄已更新，可以輸出。")
        except Exception as exc:st.error(str(exc))
st.download_button("儲存目前草稿 JSON",p.model_dump_json(indent=2),"draft.json","application/json")

st.subheader("4 · 正式輸出")
try:
    validate_project(p)
    valid=not invalid and not order_error
except Exception as exc:
    valid=False; st.info(str(exc))
if st.button("編曲並建立正式輸出 ZIP",disabled=not valid):
    try:
        with st.spinner("編曲與匯出中…"):
            st.session_state.bundle=export_bundle(p,pdf,exe)
            st.session_state.bundle_hash=hashlib.sha256(p.model_dump_json().encode()).hexdigest()
            st.session_state.bundle_pdf=pdf
    except Exception as exc:
        st.session_state.pop("bundle",None)
        st.error(str(exc))
current=hashlib.sha256(p.model_dump_json().encode()).hexdigest()
if valid and st.session_state.get("bundle") and st.session_state.get("bundle_hash")==current and st.session_state.get("bundle_pdf")==pdf:
    data=st.session_state.bundle
    st.download_button("下載全部正式輸出",data,"alto_trio.zip","application/zip")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for filename in sorted(z.namelist()):
            if filename.endswith((".musicxml",".mid",".pdf")):
                st.download_button(filename,z.read(filename),filename,key="download_"+filename)


st.subheader("5 · 真實薩克斯錄音取樣試奏")
st.caption("內附愛荷華大學 Michael Giles 的 64 個 Alto Sax 實錄單音，可離線試奏。這是錄音單音重組，不是樂手連續吹奏；連奏銜接與長音循環由電腦處理。")
mode=st.selectbox("試奏表情",["enka","neutral"],format_func=lambda x:"演歌：長音顫音、樂句力度與柔和收音" if x=="enka" else "中性：無額外樂句表情")
expression=st.slider("演歌表情程度",0.0,1.0,.7,step=.1)
room=st.slider("空間感",0.0,.3,.1,step=.05)
settings=Performance(mode,expression,room)
preview=not valid
sat_audio_ack=True
if p.ensemble=="sat":
    st.info("SAT 使用三種樂器各自的實錄單音：Iowa Soprano、Iowa Alto、VCSL Tenor；缺少的半音由同樂器鄰近錄音移調。這是取樣重組，不是樂手連續演奏。")
ack=True
if preview:
    st.warning("目前資料未完成正式確認，只能產生帶 DRAFT 標記的校對試聽；試聽不會替你確認音符。")
    ack=st.checkbox("我知道這只是未確認草稿的校對試聽")
@st.cache_resource(show_spinner=False)
def recorded_bank():
    return load_bank()
audio_key=hashlib.sha256((p.model_dump_json()+repr(settings)+str(preview)).encode()).hexdigest()
if st.button("以真實薩克斯取樣產生試奏",disabled=bool(invalid) or order_error or not ack or not sat_audio_ack):
    try:
        with st.spinner("載入實錄取樣並製作三部試奏…"):
            files,report=render_project(p,recorded_bank(),settings,preview=preview)
            st.session_state.audio_result={"key":audio_key,"files":files,"report":report}
    except Exception as exc:
        st.session_state.pop("audio_result",None)
        st.error(str(exc))
result=st.session_state.get("audio_result")
if result and result["key"]==audio_key:
    st.write("校對草稿試奏" if preview else "演出編訂版試奏" if p.review_policy=="editorial" else "已確認來源的取樣試奏")
    st.audio(result["files"]["mix.wav"],format="audio/wav")
    with st.expander("各聲部單獨試聽"):
        for i in range(1,4):
            label=("Soprano","Alto","Tenor")[i-1] if p.ensemble=="sat" else f"Alto {i}"
            filename=("soprano","alto","tenor")[i-1]+".wav" if p.ensemble=="sat" else f"alto_{i}.wav"
            st.write(label)
            st.audio(result["files"][filename],format="audio/wav")
    st.download_button("下載試奏 WAV 與檢查紀錄",audio_bundle(result["files"],result["report"]),"DRAFT_sampled_audio.zip" if preview else "sampled_audio.zip","application/zip")
    st.caption("試奏內容變更後須重新產生。來源：https://theremin.music.uiowa.edu/MISaltosaxophone.html")
