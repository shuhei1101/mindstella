# 529

音声入力の確定でレビュー中に追加する既定・録音中の移動と戻り・録音中の画面の消灯の抑止（[PR #529](https://github.com/shuhei1101/mindstella/pull/529)・起点 [Issue #528](https://github.com/shuhei1101/mindstella/issues/528)）。
スタイルは今のプレビューの `style.css` と [476](../476/index.md)・[500](../500/index.md) の分の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [topbar](../../components/topbar/index.html) | トップバーの音声入力中の表示（コメントのボタンの左の案 A・題名の右の案 B・文字起こし中・ホバーとフォーカス・保存待ちが無い・録音を破棄した・ダーク。幅 1280・390・320px） |
| [send-form](../../components/send-form/index.html) | コメントの入力の「音声:」の節（レビュー中に追加した（既定）・レビュー中に追加できなかった・ほかの入力欄で音声入力中で押せない・トップバーから録音中の入力欄へ戻った） |
| [reply-form](../../components/reply-form/index.html) | 返信の入力の「音声:」の節（レビュー中に追加した（既定）・ほかの入力欄で音声入力中で押せない） |
| [transcription-settings](../../components/transcription-settings/index.html) | 文字起こしの設定（「レビュー中に追加する」を足して既定にした） |
