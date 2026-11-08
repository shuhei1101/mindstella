# 476

コメント・返信の入力にマイクのボタンを追加し、音声を文字起こしのインターフェース経由で voice-paste に文字起こしさせる（[PR #476](https://github.com/shuhei1101/mindstella/pull/476)・起点 [Issue #402](https://github.com/shuhei1101/mindstella/issues/402)）。
スタイルは今のプレビューの `style.css` の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [voice-input](../../components/voice-input/index.html) | 音声の入力（マイクのボタン・ホバーとフォーカス・録音中の経過の時間の 2 案（結果の行の案 A とボタンの左の案 B）・打ちかけがある録音中・文字起こし中・送信した・挿入した・押せない 3 つの理由のツールチップ・押せないボタンを押した・マイクの許可を拒否した・文字起こしに失敗した・送信できなかった・狭い幅。コメントの入力と返信の入力） |
| [transcription-settings](../../components/transcription-settings/index.html) | 文字起こしの設定（設定の画面の「音声入力」のまとまり・既定・保存待ち・候補を読めない・狭い幅） |
