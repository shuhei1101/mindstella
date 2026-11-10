# 327

Markdown の本文に共通のスタイルを持たせ、表の列の固定・見出しの固定・しま模様・セクションの折りたたみを表示の設定で切り替えられるようにする（[PR #327](https://github.com/shuhei1101/mindstella/pull/327)・起点 [Issue #135](https://github.com/shuhei1101/mindstella/issues/135)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「327:」のコメント）と、#237 の見本の記録（`../237/assets/data.js`）に列の多い表を持つ資料 A-18 とそれを書き換えたまとまり V-8 を足したもの（`assets/data-extra.js`）を読む。
サーバーの代わり（`../214/assets/mock-server.js`）が記録とレビュー中のコメントの読み書きに応え、プレビューをサーバーにつながった状態で開く。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
モック専用の操作列で、見出しの開閉の案・見本（差分なし・表を縦に送った・本文の差分・左右に並べた差分・A-14）・列の幅（文字数で決める / 今の表示）・境目の案・表示の設定の上書きを切り替える。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/327/index.md) | 詳細パネルの本文の表（列の幅と折り返し・右端のフェード・列の固定・見出しの固定・しま模様）・コードブロック・コールアウト・セクションの折りたたみ（矢印を押す案 A・見出しの文言を押す案 B） |
| [detail-full](../../pages/detail-full/327/index.md) | 詳細の全画面の同じ見せ方と、本文の差分（インライン・左右に並べる）の表 |
| [settings-panel](../../pages/settings-panel/327/index.md) | 区画「詳細に表示するもの」の 4 つの切り替えと、「この端末で変えている項目」「既定に戻す」・端末に保存できないとき |

| 部品 | 中身 |
| --- | --- |
| [markdown-body](../../components/markdown-body/index.html) | 本文の Markdown（列の幅と折り返し・右端のフェード・列の固定・見出しの固定・しま模様・セクションの折りたたみ・コードブロック・コールアウト） |
| [settings-panel](../../components/settings-panel/index.html) | 表示の設定のパネルの「本文の表とセクションの見せ方を変えている」 |
