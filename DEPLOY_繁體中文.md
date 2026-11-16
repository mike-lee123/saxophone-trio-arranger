# Streamlit Cloud 網頁上傳部署

請先閱讀 [先讀我_網頁上傳.md](先讀我_網頁上傳.md)，正確解壓、上傳所有小檔案並保留資料夾。
入口 streamlit_app.py，Python 3.11。免費網站可取得固定子網域，但休眠及服務限制仍適用；不保證永久在線。
首頁既有樂譜與試奏不需API。新增圖片辨識可輸入自己的OpenAI key，或由站台管理者在Cloud Secrets設定OPENAI_API_KEY。不要將真實金鑰提交GitHub；API費用與免費託管分開。
工作台變更請下載JSON保存，Cloud本機資料不是永久資料庫。新編曲輸出MusicXML後，可在本機MuseScore列印PDF；首頁既有PDF可直接下載。
此版所有演出和音源分片由程式自動驗證SHA256並在記憶體組合，不需要在repository或Cloud磁碟產生大型檔案。
