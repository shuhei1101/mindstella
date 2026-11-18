# 565

スキルとプレイブックをやめて記録のエージェントフローにし、ゴール判定・次の候補などの削除する機能を削除する（[PR #565](https://github.com/shuhei1101/mindstella/pull/565)・起点 [Issue #518](https://github.com/shuhei1101/mindstella/issues/518)）。
スタイルは今のプレビューの `style.css` の上に、この PR の分（`assets/style.css`）を重ねる。

| 画面 | 中身 |
| --- | --- |
| [overview / 565](../../pages/overview/565/index.md) | 概要を、未読の AI の書き込み・未決定の検討事項・要見直しの検討事項・確認中の資料の 4 つの一覧のタイルだけにする（確認中の資料は 0 件の表示） |
| [decisions / 565](../../pages/decisions/565/index.md) | 検討事項のマップを、対象 → カテゴリー → フェーズの木から、主題のタグで分ける木（案 A）か親子の関係でつなぐ木（案 B）にする。狭い幅は字下げの一覧 |
