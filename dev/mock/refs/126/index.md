# 126

プレビューの検索・絞り込み・画面の固定・本文のリンクを使いやすくする（[PR #126](https://github.com/shuhei1101/mindstella/pull/126)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「126:」のコメント）と、mindstella 自身の改善の話し合いの記録を今の形式へ移した見本（`assets/data.js`）を読む。
スタイルは develop の `style.css` の写し（`assets/base.css`）の上に、部品の分（`assets/style.css`）と画面の作りの分（`assets/layout.css`）を重ねる。
見本の記録は埋め込んで読むため、配る書き出しと同じくコメントのボタンは出ない。
URL のハッシュに `h={見出し}` を足すと、詳細の本文のその見出しまでスクロールした状態で開く。

| 画面 | 中身 |
| --- | --- |
| [search](../../pages/search/126/standard/index.html) | 全体の検索。Ctrl+K で開き、完全に一致する項目を種類の見出しより上に出す |
| [records](../../pages/records/126/index.md) | 用語集の表。列の値・ID で絞り込む入口を 2 案（A 列の見出し・B ドロワー） |
| [decisions](../../pages/decisions/126/standard/index.html) | 検討事項のマップ。中間の層のラベルの面と線、帯の下の領域いっぱいのマップ |
| [tasks](../../pages/tasks/126/standard/index.html) | タスクのボード。帯の下の領域の中で縦・横にスクロールする |
| [docs](../../pages/docs/126/standard/index.html) | 資料のカード・ボード・表 |
| [overview](../../pages/overview/126/standard/index.html) | 概要のタイル |
| [graph](../../pages/graph/126/standard/index.html) | つながり |
| [detail-panel](../../pages/detail-panel/126/standard/index.html) | 詳細パネルの本文の見出しのリンク・用語の印とツールチップ・項目の ID のリンク |
| [detail-full](../../pages/detail-full/126/standard/index.html) | 詳細の全画面の大きさと本文の幅、全画面表示のボタン |

| 部品 | 中身 |
| --- | --- |
| [body-links](../../components/body-links/index.html) | 本文の見出しのリンク・用語の印とツールチップ・項目の ID のリンク |
| [filter-drawer](../../components/filter-drawer/index.html) | B 案の列ごとの文字の条件と、文字の条件のチップ |
| [table](../../components/table/index.html) | A 案の列の見出しの文字の絞り込みのボタンとポップオーバー |
| [fullscreen-button](../../components/fullscreen-button/index.html) | 全画面の間の縮小のアイコンと読み上げ名 |
| [topbar](../../components/topbar/index.html) | 検索の入口のキーの案内（Ctrl+K・⌘K） |
