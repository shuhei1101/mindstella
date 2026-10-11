# 223

表の「表示する列」のボタンの文言と置き場所を直す（[PR #223](https://github.com/shuhei1101/mindstella/pull/223)・起点 [Issue #197](https://github.com/shuhei1101/mindstella/issues/197)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「223:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）に単一 UC『項目を表で絞り込む』の調査 R-1〜R-3 と縦に送れるだけの調査を足したもの（`assets/data.js`）を読む。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
置き場所の案（A 表の上の帯の右端・B トップバーの絞り込みのボタンの隣）は案のディレクトリで分け、モック専用の操作列で、文言の案（A「列の表示」・B「列」）、絞り込み中の状態、ポップオーバーを開いた状態を切り替える。

| 画面 | 中身 |
| --- | --- |
| [records](../../pages/records/223/index.md) | 調査の表の列を選ぶボタン |
| [decisions](../../pages/decisions/223/index.md) | 検討事項の表の表示形式の列を選ぶボタン（案 B はボード・マップでボタンを出さない） |

| 部品 | 中身 |
| --- | --- |
| [columns-button](../../components/columns-button/index.html) | 列を選ぶボタンの案 A・B（絞っていない・絞り込み中・文言の案 B・ホバーとフォーカス・ポップオーバーを開いている・表を出していない表示形式・狭い幅） |
