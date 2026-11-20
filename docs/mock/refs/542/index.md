# 542

使用していないネットワークの画面と検討事項のマップを削除する（[PR #632](https://github.com/shuhei1101/mindstella/pull/632)・起点 [Issue #542](https://github.com/shuhei1101/mindstella/issues/542)）。
画面は、#609 のモックのスクリプトにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「542:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）を読む。
サーバーの代わり（`assets/mock.js`）は #609 と同じで、表示する種類の上書きと既定の保存の確かめを開く見本を足した。
スタイルは今のプレビューの `style.css` の上に、モック専用の操作列（`assets/style.css`）を重ねる。

| 画面 | 中身 |
| --- | --- |
| [decisions](../../pages/decisions/542/index.md) | 表示形式をボード・表の 2 つにした検討事項と、ネットワークを除いたタブの帯 |
| [settings-panel](../../pages/settings-panel/542/index.md) | ネットワークの見た目を除いた表示の設定と既定の保存の確かめ |
