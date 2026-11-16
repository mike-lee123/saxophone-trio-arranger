# SAT 實錄音源

Soprano：University of Iowa Electronic Music Studios / Lawrence Fritts；Michael Giles，1997年11月，ff有顫音及無顫音獨立音符。來源 https://theremin.music.uiowa.edu/MIS-Pitches-2012/MISBbSopranoSaxophone2012.html 。Iowa允許下載並用於任何專案，不另宣稱CC0：https://theremin.music.uiowa.edu/MIS.html 。62個原始錄音映射為64個奏法/半音；缺少的C#6由同樂器鄰音移調。

Alto：原內附Iowa Michael Giles mf錄音，64個單音，詳SAMPLE_CREDITS.md。

Tenor：Versilian Community Sample Library (VCSL)，Versilian Studios / Sam Gossner及貢獻者，原始檔標記BrettTenor。官方頁 https://versilian-studios.com/vcsl/ 明確允許CC0下使用及整合軟體；來源repository https://github.com/sgossner/VCSL/tree/sfz 。使用原廠SFZ pitch_keycenter（檔名八度與科學記號不同，不能直接解析檔名當實音）。31個原始錄音映射64個奏法/半音，缺音由同樂器鄰近錄音移調。

處理：轉單聲道44.1kHz、裁去靜音、實測微調音準、響度平衡、最長保留3.2秒；長音採持續區段循環。逐來源URL、SHA256、固定VCSL commit、音準修正與映射見soprano_recorded_manifest.json、tenor_recorded_manifest.json。這是各樂器真人單音錄音重組，不是樂手連續錄製整首。
