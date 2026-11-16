# coding: utf-8
"""Multi-song performance dashboard and shared arranging workspace."""
from pathlib import Path
import io,runpy,zipfile
import streamlit as st
import pandas as pd
from trio.library import read_pack,inspect_pack,pack_available

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title="薩克斯三重奏工作室",page_icon="🎷",layout="wide")
with st.sidebar:
    st.title("🎷 三重奏工作室")
    page=st.radio("工作區",["演出儀表板","上傳與編曲工作台"],key="dashboard_page")
    st.caption("三 Alto／組合 C：Soprano · Alto · Tenor")
    st.caption("演歌 · 抒情 · 古典 · 柔和爵士")
if page=="上傳與編曲工作台":
    st.info("側欄可載入《榕樹下》SAT、原有曲目，或上傳新曲譜。SAT 使用各樂器的實錄單音；可調整風格、速度與主旋律八度。")
    runpy.run_path(str(ROOT/'app.py'),run_name='__main__')
else:
    songs={}
    if pack_available(ROOT,'rongshu-performance.zip'):
        songs['榕樹下 · SAT']=('rongshu-performance.zip','rongshu.performance.json','rongshu.jpg')
    songs['黃昏的故鄉 · 三 Alto']=('complete-performance.zip','huanghun.performance.json','huanghun.jpg')
    options=list(songs)
    preferred=st.session_state.get('library_last_song',options[0])
    selection=st.selectbox('曲目',options,index=options.index(preferred) if preferred in options else 0,key='library_song')
    st.session_state.library_last_song=selection
    archive_name,project_name,image_name=songs[selection]
    st.title(selection.split(' · ')[0])
    st.caption('固定演出庫 · 可下載總譜、分譜與分聲部試奏；工作台變更不會覆寫此庫。')
    @st.cache_data(show_spinner=False,max_entries=2)
    def cached_pack(folder,name,version):return read_pack(folder,name)
    archive=ROOT/'assets'/archive_name
    manifest=archive.with_name(archive.name+'.parts.json')
    if pack_available(ROOT,archive_name):
        try:
            version=manifest.stat().st_mtime_ns if manifest.is_file() else archive.stat().st_mtime_ns
            data=cached_pack(str(ROOT),archive_name,version)
        except (OSError,ValueError,KeyError) as exc:
            st.error('演出資料分片不完整或損壞，請補上 assets 中全部對應 part 及 parts.json。'+str(exc));st.stop()
    else:
        st.warning('網站程式已啟動，但尚未載入演出資料包。')
        st.write('請上傳完整 assets 資料夾，保留所有分片與 parts.json，程式會自動重組。')
        st.code('assets/'+archive_name+'\nassets/'+archive_name+'.parts.json')
        st.caption('也可暫時上傳完整演出 ZIP；僅此連線有效。不是程式碼專案 ZIP。')
        uploaded=st.file_uploader('載入演出資料包 complete-performance.zip',type=['zip'],key='performance_upload')
        if uploaded is not None:st.session_state.performance_upload_bytes=uploaded.getvalue()
        data=st.session_state.get('performance_upload_bytes')
        if not data:
            st.info('沒有資料包仍可切換左側「上傳與編曲工作台」。');st.stop()
    try:
        report,route,names,pdfs,mp3s=inspect_pack(data)
    except (ValueError,KeyError,AssertionError,zipfile.BadZipFile,UnicodeError) as exc:
        st.error('無法載入這份演出資料包：'+str(exc))
        st.session_state.pop('performance_upload_bytes',None);st.stop()
    sat=report.get('ensemble')=='sat'
    roles=['Soprano','Alto','Tenor'] if sat else ['Alto 1','Alto 2','Alto 3']
    bars=report['notated_measures'];seconds=round(report['stats']['mix']['seconds'])
    columns=st.columns(4)
    columns[0].metric('演出小節',bars)
    columns[1].metric('完整試奏',f'{seconds//60} 分 {seconds%60:02d} 秒')
    columns[2].metric('記譜調性','D / A / D' if sat else 'Alto A 大調')
    columns[3].metric('實際發聲','C 大調')
    st.download_button('下載全部樂譜與試奏 ZIP',data,archive_name,'application/zip',type='primary',on_click='ignore')
    def edit_selected():
        from trio.model import Project
        st.session_state.project=Project.model_validate_json((ROOT/'examples'/project_name).read_text(encoding='utf-8'))
        st.session_state.source_image=(ROOT/'examples/source'/image_name).read_bytes()
        st.session_state.revision=st.session_state.get('revision',0)+1
        st.session_state.invalid_bars={}
        for field in ('case_audit','bundle','audio_result'):st.session_state.pop(field,None)
        st.session_state.dashboard_page='上傳與編曲工作台'
    st.button('在工作台編輯此曲',on_click=edit_selected,disabled=not (ROOT/'examples'/project_name).is_file())
    st.caption('直接由瀏覽器下載；另存 JSON 可保存工作台修改。')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        def download(label,name,key):
            mime='application/pdf' if name.endswith('.pdf') else 'audio/mpeg' if name.endswith('.mp3') else 'application/octet-stream'
            st.download_button(label,z.read(name),name,mime,key=key,on_click='ignore',use_container_width=True)
        scores,listen,form,checks=st.tabs(['總譜與分譜','試奏練習','演出路線','來源與檢查'])
        with scores:
            if sat:
                notation='五線譜';files=pdfs
                st.caption('Soprano D、Alto A、Tenor D 大調。SAT 提供五線譜 PDF；未將三 Alto 簡譜套為 SAT。')
            else:
                notation=st.radio('選擇譜式',['五線譜','簡譜'],horizontal=True)
                files=pdfs if notation=='五線譜' else ['簡譜總譜_Alto_A調_正式演出.pdf']+[f'Alto{i}_簡譜_A調_正式演出.pdf' for i in (1,2,3)]
            for i,(column,name) in enumerate(zip(st.columns(4),files)):
                with column:
                    with st.container(border=True):
                        st.subheader('三部總譜' if i==0 else roles[i-1]);st.caption('PDF · 演出編訂版')
                        download('下載 PDF',name,f'score_{selection}_{i}_{notation}')
            with st.expander('編輯用 MusicXML 與 Concert MIDI'):
                for name in ['score.musicxml']+[x+'.musicxml' for x in names]+['concert.mid']:
                    download(name,name,'source_'+selection+name)
        with listen:
            voice=st.selectbox('練習聲部',['三部合奏']+roles,key='voice_'+selection)
            name=mp3s[0 if voice=='三部合奏' else roles.index(voice)+1]
            st.audio(z.read(name),format='audio/mpeg');download('下載目前試奏 MP3',name,'audio_'+selection+voice)
            st.caption('三種樂器各自的實錄單音重組；缺少半音由同樂器鄰音移調。不是樂手連續演奏。' if sat else '真實 Alto 單音錄音取樣的電腦試奏。')
            st.write('先聽單一聲部，再切回合奏，對照排練記號。')
        with form:
            rows=[]
            for idx,(start,letter,label,a,b) in enumerate(route['sections']):
                end=route['sections'][idx+1][0]-1 if idx+1<len(route['sections']) else bars
                rows.append({'排練記號':letter,'段落':label,'演出小節':f'{start}-{end}','來源小節':f'{a}-{b}'})
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
            download('下載演出路線說明 PDF','演出路線與編訂說明.pdf','route_'+selection)
            st.caption(route.get('notes',report.get('edition_notes','本版編訂路線，未另加未註明的 D.S.。')))
        with checks:
            st.success('依使用者授權採免人工確認的演出編訂模式，保留拍值、音域與來源紀錄。')
            a,b=st.columns(2)
            with a:
                st.json({'發聲事件':report['note_count'],'長度（秒）':round(report['stats']['mix']['seconds'],2),'削波取樣':report['stats']['mix']['clipped_samples'],'MusicXML 回讀一致':report['notation_musicxml_roundtrip']})
                download('下載檢查紀錄','演出與聲音檢查.json','checks_'+selection)
                if sat:download('音源來源與授權','SAT_SAMPLE_CREDITS.md','credits_sat')
                st.caption('PDF 使用 Verovio；檢查結果屬此演出版，不是開頁後重新測試。')
            with b:st.image(z.read('來源簡譜.jpg'),caption='來源簡譜',use_container_width=True)
