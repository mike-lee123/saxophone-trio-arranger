# Saxophone Trio Arranger · Streamlit Cloud

完整三支Alto編曲工作室，附67小節正式演出版、五線譜、簡譜、MusicXML、Concert MIDI及實錄取樣試奏。

部署入口：`streamlit_app.py`；Community Cloud Advanced settings 選 Python **3.11**。

完整教學：[DEPLOY_繁體中文.md](DEPLOY_繁體中文.md)。音源來源及許可：[assets/SAMPLE_CREDITS.md](assets/SAMPLE_CREDITS.md)。

快速本機啟動：`python -m pip install -r requirements.txt`，然後 `python -m streamlit run streamlit_app.py`。

不需 API 即可使用既有演出版；新增圖片的OpenAI辨識需另備金鑰。免費託管不代表OpenAI API免費，也不代表永久在線。新編曲PDF需外部MuseScore；首頁內附PDF可直接下載。
