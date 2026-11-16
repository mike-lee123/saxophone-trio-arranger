# v1.6.3 三部豐富前奏驗證

2026-11-17。完整pytest：110 passed、2 skipped，見release-1.6.3-test-results.xml。
前4小節各4拍，Soprano32個音、高低音域E4-G5；新增Alto26個音及Tenor8個音，明確取代前奏N.C.停奏，以C、Am7、Dm7、G7為和聲基礎。三聲部無交叉，末音F5接主題G5；第5小節起三聲部音高、起點、長度、力度與原版完全一致。原38小節來源資料未改，使用intro_variation=trio明確記錄改編。
前奏Soprano力度64-75，起音8ms漸接5ms，低通4800Hz漸開至6600Hz，保留亮度並銜接主題。原柔和模式仍保留且其高頻衰減測試通過。試奏495個事件、202秒，MusicXML回讀與音訊來源一致；非人工聽審。
其餘三Alto、SAT、音源、移調、拍值、封存、檔案、儀表板測試維持通過。真實OpenAI API與MuseScore兩個外部服務測試略過。
Windows／Python3.9.6本機驗證；未宣稱Linux或Python3.11乾淨部署。PDF以Verovio製作並渲染檢查，仍為60小節三部總譜與三份分譜。
