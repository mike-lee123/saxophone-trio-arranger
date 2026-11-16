# 雲端封裝驗證

本次實際測試：85 passed、2 skipped。測試記錄：cloud-test-results.xml。
已由此交付資料夾執行全部pytest，包含雲端入口、儀表板與工作台切換、64音源分片重組、損壞檔案拒絕、伺服器金鑰不填入瀏覽器欄位、拍值、音域、移調、MusicXML/MIDI及音訊輸出。
實際本機啟動streamlit_app.py，健康檢查回應ok。

執行環境：Windows、Python3.9.6及requirements.txt既有相符套件。雲端部署請選Python3.11；這份交付未聲稱完成Linux／Python3.11乾淨建置或真實Community Cloud部署。
真實OpenAI API與MuseScore整合測試略過；首頁既有PDF可下載，新編曲MusicXML可交本機MuseScore列印。
雲端資源、相依套件安裝與公開網址的最終驗證須以使用者部署後的建置記錄及實際網站為準。
