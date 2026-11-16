# v1.6.2 流動漸強前奏驗證

2026-11-17。完整pytest：109 passed、2 skipped，見release-1.6.2-test-results.xml。
前4小節各4拍，32個Soprano發聲音，分解和弦與順階流動；末音F5上行全音接主題G5，力度73接76，四小節平均力度逐步上升；第5小節起主旋律以及Alto/Tenor音高、起點、長度、力度與原版完全一致。原38小節來源資料未改，使用intro_variation=flowing明確記錄改編。
前奏Soprano力度64-75，起音8ms漸接5ms，低通4800Hz漸開至6600Hz，保留亮度並銜接主題。原柔和模式仍保留且其高頻衰減測試通過。試奏461個事件、202秒，MusicXML回讀與音訊來源一致；非人工聽審。
其餘三Alto、SAT、音源、移調、拍值、封存、檔案、儀表板測試維持通過。真實OpenAI API與MuseScore兩個外部服務測試略過。
Windows／Python3.9.6本機驗證；未宣稱Linux或Python3.11乾淨部署。PDF以Verovio製作並渲染檢查，仍為60小節三部總譜與三份分譜。
