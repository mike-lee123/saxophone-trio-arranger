# 部署至免費 Streamlit Community Cloud

這是完整 Python 原始碼，不是僅供示範的介面。包含 trio 模組、音源、67小節演出檔案、測試及設定。部署入口為 streamlit_app.py。

## 1. 上傳到 GitHub

1. 解壓縮 Saxophone-Trio-Streamlit-Cloud.zip。
2. 在 GitHub 建立 repository，例如 saxophone-trio-arranger。
3. 把解壓資料夾「裡面的所有檔案及資料夾」上傳至 repository 根目錄，並 Commit。不是只上傳 ZIP。
4. 確認根目錄能看見 streamlit_app.py、requirements.txt、packages.txt、trio/、assets/、examples/、.streamlit/。
5. 若 GitHub 網頁每批限制檔案數量，可分批上傳各資料夾；務必保留完整目錄。

音源已分割為四個小於10MB的 part 檔案，程式會驗證並在記憶體重組。不要解壓或重新命名這些 part；不需要 Git LFS。單一最大的演出 ZIP 約21.5MB，可分開上傳。

## 2. 建立網站

1. 開啟 https://share.streamlit.io 並以 GitHub 登入。
2. Create app → 選擇已有 repository 的方式。
3. Repository 選剛才的專案，Branch 選 main。
4. Main file path 填 streamlit_app.py。
5. Advanced settings → Python version 選 3.11。本套件鎖定的版本不要直接搭配未驗證的新 Python 版本。
6. App URL 可填喜歡且尚未被使用的名稱，例如 mike-saxophone-trio。
7. 按 Deploy。建置成功後，Cloud 顯示實際的 https://你的名稱.streamlit.app 網址。

名稱範例不是已註冊網址。本交付沒有替使用者登入 GitHub 或完成雲端部署。

## 3. 金鑰（選用）

不設定任何 API 金鑰，也可下載所有已完成樂譜、播放67小節合奏及三份分聲部。
新增曲目的 AI Vision 辨識才需要 OpenAI API；該 API 的費用獨立於免費網站託管。
可讓每位使用者在工作台輸入自己的 key；也可在 Cloud App Settings → Secrets 貼上：

```toml
OPENAI_API_KEY = "你的金鑰"
```

站台金鑰只留在伺服器，不填入網頁的密碼欄。設定站台金鑰後，有權使用網站的人按辨識會使用該金鑰的額度；請依你的分享範圍選擇是否提供。不要將真實 secrets.toml 或 .env 提交 GitHub。

## 4. 使用與維護

首頁提供固定完成版五線譜／簡譜、分聲部試奏、路線與檢查紀錄；按鈕直接下載到瀏覽器。工作台可上傳、辨識、校對、編曲、輸出 MusicXML／MIDI，或使用真實單音錄音取樣重新試奏。
工作台修改不會覆寫首頁的固定演出包。下載 JSON 以保存工作進度；Session 和 Cloud 本機檔案不當成永久資料庫。
每次完整音訊重新渲染較耗記憶體和時間。練習既有曲目請用首頁已製作的MP3；多人同時重算可能碰到免費服務資源限制。
本套件內附既有 PDF（Verovio 製作）；Cloud 不包含 MuseScore 桌面程式。新編曲可匯出 MusicXML 後在本機 MuseScore 列印 PDF。不要將 Windows MuseScore.exe 路徑填入 Linux 雲端。

## 5. 網址是否永久

可以取得可分享的固定子網域，但免費服務沒有永久在線保證。官方文件目前說明12小時無流量會休眠，訪客可在休眠頁按鈕喚醒。帳號、repository、服務政策及相依版本仍需維護；刪除或更改網站會影響網址。

官方參考：
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## 本機執行

Python 3.11：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

測試：python -m pytest -q。驗證結果另見 CLOUD_VALIDATION.md。雲端首次建置仍以實際部署日的Cloud建置紀錄為準。
