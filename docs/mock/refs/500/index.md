# 500

音声入力の文字起こしを入力欄へ挿入するだけにし、録音中は入力欄の場所に入力している音声の波形を表示する（[PR #500](https://github.com/shuhei1101/mindstella/pull/500)・起点 [Issue #499](https://github.com/shuhei1101/mindstella/issues/499)）。
スタイルは今のプレビューの `style.css` と [476](../476/index.md) の分の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [send-form](../../components/send-form/index.html) | コメントの入力の「音声:」の節（録音中・打ちかけがある録音中・狭い幅の録音中を波形に替え、波形の案 B を足した。挿入した（既定）と、送信した（「送信する」を選んだとき）の見出し） |
| [reply-form](../../components/reply-form/index.html) | 返信の入力の「音声:」の節（録音中・最も狭い幅の録音中を波形に替えた） |
| [transcription-settings](../../components/transcription-settings/index.html) | 文字起こしの設定（既定を「入力欄へ挿入する」にした） |
