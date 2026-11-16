# Saxophone Trio Arranger v1.6.2

同一Streamlit程式支援三支Alto及組合C：Soprano＋Alto＋Tenor。Dashboard預設《榕樹下》SAT60小節，曲目選單可切回《黃昏的故鄉》三Alto67小節。

## 啟動及部署

本機：`python -m pip install -r requirements.txt`，再 `python -m streamlit run streamlit_app.py`。
Streamlit Community Cloud：GitHub完整目錄，入口`streamlit_app.py`，Python選3.11。詳細步驟見`DEPLOY_繁體中文.md`。GitHub Desktop將「本資料夾內的內容」複製到clone目錄，再Commit、Push；不要提交外層交付ZIP。
所有大型素材已分割為單檔不超過8MiB的part，全部原樣上傳，不手動合併。程式校驗SHA256並在記憶體讀取。

## 使用

首頁可下載總譜、三份分譜、MusicXML、Concert MIDI、合奏與分聲部MP3。SAT本版提供五線譜，三Alto另保留原有簡譜。
「在工作台編輯此曲」可將目前選曲載入工作台。修改風格、速度、八度或音符後，編訂模式需重新封存再匯出；不虛填人工校對者。
工作台側欄也有《榕樹下》SAT及《黃昏的故鄉》三Alto／SAT載入按鈕。上傳新圖片需Vision API金鑰才能自動辨識；也可手動建立或匯入JSON。現引擎支持Concert C大調、固定拍號單聲部。
SAT三種風格：抒情、古典、柔和爵士（直八分，有限六／九度色彩，規則式編曲）。Soprano主旋律、Alto中和聲、Tenor低音。C實音分別記譜D／A／D，Tenor提高大九度。主旋律八度由使用者明確選擇；榕樹下保留來源八度，黃昏SAT提高一個八度。

## 真實樂器取樣

Soprano與Alto來自Iowa MIS，Tenor來自VCSL（CC0）。各樂器使用自己的真人單音，缺少的半音用同樂器鄰音移調，沒有用Alto音色冒充Tenor。來源與授權見`assets/SAT_SAMPLE_CREDITS.md`，逐錄音與映射見對應manifest。
這是實錄單音重組的電腦試奏，不是樂手連續演奏。Cloud首頁已有MP3可直接播放；工作台重新製作較耗資源。Session不是永久儲存，請下載JSON保存進度。
新編曲可輸出MusicXML與MIDI；PDF需本機MuseScore，Cloud首頁內附PDF以Verovio製作。免費託管不含OpenAI API費用，也不保證永久在線。


榕樹下v1.6.2：前4小節（13.33秒）改為柔和前奏，Soprano較低音域分解和弦與順階填充。工作台「榕樹下前奏」可切回原譜；改動後重新封存再輸出。


榕樹下v1.6.2：前4小節（13.33秒）改為流動漸強前奏，逐步提高音域、力度與亮度，末音F5接主題G5。原柔和模式仍可選。工作台「榕樹下前奏」可切回原譜；改動後重新封存再輸出。
