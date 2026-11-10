# 476

コメント・返信の入力にマイクのボタンを追加し、音声を文字起こしのインターフェース経由で voice-paste に文字起こしさせる（[PR #476](https://github.com/shuhei1101/mindstella/pull/476)・起点 [Issue #402](https://github.com/shuhei1101/mindstella/issues/402)）。
スタイルは今のプレビューの `style.css` の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [send-form](../../components/send-form/index.html) | コメントの入力の「音声:」の節（マイクのボタン・ホバーとフォーカス・録音中・打ちかけがある録音中・文字起こし中・送信した・挿入した・押せない 3 つの理由のツールチップ・押せないボタンを押した・マイクの許可を拒否した・文字起こしに失敗した・送信できなかった・狭い幅） |
| [reply-form](../../components/reply-form/index.html) | 返信の入力の「音声:」の節（マイクのボタン・録音中・送信した・押せない・最も狭い幅の録音中） |
| [transcription-settings](../../components/transcription-settings/index.html) | 文字起こしの設定（設定の画面の「音声入力」のまとまり・既定・保存待ち・候補を取得できない・狭い幅） |
