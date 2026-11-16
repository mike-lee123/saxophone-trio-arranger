# coding: utf-8
"""Performance library and editing workspace, served through real download buttons."""
from pathlib import Path
import json
import runpy
import zipfile
import streamlit as st
import pandas as pd

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="薩克斯三重奏工作室",page_icon="🎷",layout="wide")
with st.sidebar:
    st.title("🎷 三重奏工作室")
    page = st.radio("工作區",["演出儀表板","上傳與編曲工作台"],key="dashboard_page")
    st.caption("Concert C · Alto Written A")
    st.caption("日本演歌 · 三支 Alto Sax")

if page == "上傳與編曲工作台":
    st.info("在左側載入完整演出編訂版，即可調整速度、編曲並重新製作試奏。新增曲目則先上傳圖片。")
    runpy.run_path(str(ROOT/"app.py"),run_name="__main__")
else:
    @st.cache_data(show_spinner=False)
    def file_bytes(path,mtime):
        return Path(path).read_bytes()

    archive=ROOT/"assets/complete-performance.zip"
    st.title("黃昏的故鄉")
    st.caption("正式演出編訂版 · 樂譜、分聲部練習與完整演出，一處完成")
    if not archive.is_file():
        st.error("找不到內附演出檔案，請重新解壓完整 Dashboard 專案。")
        st.stop()
    data=file_bytes(str(archive),archive.stat().st_mtime_ns)
    with zipfile.ZipFile(archive) as z:
        report=json.loads(z.read("演出與聲音檢查.json"))
        route=json.loads(z.read("演出路線.json"))
        def download(label,name,key):
            mime="application/pdf" if name.endswith('.pdf') else "audio/mpeg" if name.endswith('.mp3') else "application/octet-stream"
            st.download_button(label,z.read(name),name,mime,key=key,on_click="ignore",use_container_width=True)
        cols=st.columns(4)
        cols[0].metric("演出小節",report['notated_measures'])
        cols[1].metric("完整試奏","3 分 46 秒")
        cols[2].metric("Alto 記譜調","A 大調")
        cols[3].metric("實際發聲","C 大調")
        st.download_button("下載全部樂譜與試奏 ZIP",data,"complete-performance.zip","application/zip",type="primary",on_click="ignore")
        st.caption("直接由瀏覽器下載，檔案會存至瀏覽器的下載資料夾。")
        scores,listen,form,checks=st.tabs(["總譜與分譜","試奏練習","演出路線","來源與檢查"])
        with scores:
            notation=st.radio("選擇譜式",["五線譜","簡譜"],horizontal=True)
            columns=st.columns(4)
            files=(["三部總譜_正式演出.pdf"]+[f"Alto {i} 分譜_正式演出.pdf" for i in range(1,4)]) if notation=="五線譜" else (["簡譜總譜_Alto_A調_正式演出.pdf"]+[f"Alto{i}_簡譜_A調_正式演出.pdf" for i in range(1,4)])
            for i,(col,name) in enumerate(zip(columns,files)):
                with col:
                    with st.container(border=True):
                        st.subheader("三部總譜" if i==0 else f"Alto {i}")
                        st.caption("Written A 大調 · PDF")
                        download("下載 PDF",name,f"score_{i}_{notation}")
            with st.expander("編輯用 MusicXML 與 Concert MIDI"):
                for name in ['score.musicxml','alto_1.musicxml','alto_2.musicxml','alto_3.musicxml','concert.mid']:
                    download(name,name,'source_'+name)
            st.caption("要修改曲目或重新產生樂譜，請切換左側「上傳與編曲工作台」。此頁是已完成的固定演出版。")
        with listen:
            voice=st.selectbox("練習聲部",["三部合奏","Alto 1","Alto 2","Alto 3"])
            name="三部合奏_完整演出.mp3" if voice=="三部合奏" else voice.replace(' ','')+"_完整試奏.mp3"
            st.audio(z.read(name),format="audio/mpeg")
            download("下載目前試奏 MP3",name,'audio_'+voice)
            st.caption("真實 Alto 單音錄音取樣的電腦試奏；不是樂手連續現場演奏。")
            st.write("練習建議：先聽單一聲部，再切回三部合奏，對照 A–G 排練記號。")
        with form:
            st.subheader("前奏 → 第一段 → 間奏 → 第二段 → 間奏 → 第三段 → 尾奏")
            rows=[]
            labels=['前奏','第一段','間奏一','第二段','間奏二','第三段','尾奏']
            for idx,(start,letter,label,a,b) in enumerate(route['sections']):
                end=route['sections'][idx+1][0]-1 if idx+1<len(route['sections']) else 67
                rows.append({'排練記號':letter,'段落':labels[idx],'演出小節':f'{start}–{end}','來源小節':f'{a}–{b}'})
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
            download("下載演出路線說明 PDF","演出路線與編訂說明.pdf",'route_pdf')
            st.caption("本版採用的編訂路線；原圖 Segno 作來源定位，未另加未註明的 D.S.。尾奏末拍全員一起延長。")
        with checks:
            st.success("編訂模式已封存；依使用者要求免逐小節人工確認，拍值及音域驗證仍保留。")
            a,b=st.columns([1,1])
            with a:
                st.write("聲音檢查")
                st.json({'發聲事件':report['note_count'],'長度（秒）':round(report['stats']['mix']['seconds'],2),'削波取樣':report['stats']['mix']['clipped_samples'],'MusicXML 回讀一致':report['notation_musicxml_roundtrip']})
                download("下載檢查紀錄","演出與聲音檢查.json",'checks_json')
                st.caption("附檔中的測試結果是該演出版的測試紀錄，不是每次開啟頁面重新執行。PDF 使用 Verovio 製作。")
            with b:
                st.image(z.read('來源簡譜.jpg'),caption="來源簡譜",use_container_width=True)
