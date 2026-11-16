# v1.5.3 正式演出編訂版驗證

黃昏的故鄉｜三支 Alto Sax 正式演出編訂版

本版依使用者「不須人工確認」指示完成，不另要求逐小節簽認；沒有新增虛構的人工校對紀錄。
採用的演出路線共 67 小節：前奏 → 第一段 → 間奏 → 第二段 → 間奏 → 第三段 → 尾奏。
這是本版採用的編訂路線；原圖 Segno 等符號的處理詳見「演出路線與編訂說明.pdf」。

直接演奏：開啟「三部總譜_正式演出.pdf」及三份「Alto 1/2/3 分譜_正式演出.pdf」。
簡譜：另附 A 調總譜、三份 A 調分譜，及 Concert C 調主旋律。
全部 Alto 演奏譜為 Written A 大調；實際發聲及 concert.mid 為 Concert C 大調。
第二、三聲部加入填充、級進與和弦音；原圖小音符安排於第二聲部。
結尾一起延長，試奏約 3 分 46 秒（含尾音）；樂譜 268 拍，試奏終拍延長後 269 拍。

試奏：三部合奏_完整演出.mp3；Alto1/2/3_完整試奏.mp3 可分別練習。
音色使用 University of Iowa 真實 Alto Sax 單音錄音取樣，由電腦編排；不是真人連續現場演奏。
已檢查 MIDI、移調、音域、拍值、音檔無削波及 MusicXML 回讀；未宣稱真人聽審。
MusicXML 可於 MuseScore 開啟再排版。本次 PDF 以 Verovio 製作，並非由未安裝的 MuseScore 轉出。

應用程式 v1.5.3 測試：80 passed、2 skipped。略過真實 OpenAI API 及 MuseScore 外部服務測試。
保留 edition_project.json、演出路線.json、演出與聲音檢查.json 供後續修改追蹤。


完整 pytest 證據：test-results.xml。新增完整路線、封存防竄改、主旋律保留、裝飾音、終止和弦與延長、正式匯出及 Streamlit 免人工確認流程測試。
