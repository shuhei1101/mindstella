# 540

記録の検索と書き込みを project-index へ移し、commit とスレッドを MindStella の MCP に残す（[PR #540](https://github.com/shuhei1101/mindstella/pull/540)・起点 [Issue #517](https://github.com/shuhei1101/mindstella/issues/517)）。
画面は、今のプレビューのトークンとスタイル（`plugins/mindstella/skills/mindmap/preview/tokens.css`・`style.css`）の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねた静的な HTML。
モック専用の操作列の「案」で案を、「見本」でライトとダークを切り替える。

| 画面 | 中身 |
| --- | --- |
| [history-dialog](../../pages/history-dialog/540/index.md) | 変更履歴のモーダルで、外部の変更のまとまりを見分ける 2 案（名前の横の札の案 A と行の頭の書き手の案 B） |
| [duplicate-id-notice](../../pages/duplicate-id-notice/540/index.md) | 重なった ID の通知の 2 案（トップバーの下の帯の案 A と右下のトーストの案 B） |
| [detail-panel](../../pages/detail-panel/540/index.md) | 詳細パネルの編集の、種類つきの関係の入力の 2 案（1 件 1 行で種類を選ぶ案 A と種類ごとにまとめる案 B） |
