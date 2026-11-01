# 325

利用者が画面から項目を編集・追加・削除し、まとめて保存できるようにする（[PR #325](https://github.com/shuhei1101/mindstella/pull/325)・起点 [Issue #48](https://github.com/shuhei1101/mindstella/issues/48)）。
画面は、develop のプレビューのスクリプト（`plugins/mindstella/skills/mindmap/preview/` の build がつなぐ順）と #237 の見本の記録（`../237/assets/data.js`）を読み、この PR の編集・保存待ち・まとめての保存を `assets/edit.js` で重ねたもの。
サーバーの代わり（`assets/mock.js`）が、保存待ちの編集を当てた記録を返し、書き換えの知らせで画面に読み直させる。
保存待ちの編集はモックでは端末の作業の保存領域に見本ごとに持ち、開き直しても残る（モック専用の操作列の「見本の保存待ちに戻す」で見本へ戻す）。
保存の結果は見本で決まる（書き込めない編集の見本は D-17 が溜めた後に AI に書き換えられ、D-8 が指されている。つながらない見本は保存に失敗する）。
モック専用の操作列で、論点の案と見本を切り替える。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/325/index.md) | 編集の置き方（詳細パネルの中で切り替える案 A・別の画面の案 B）と、保存待ちに溜める時点（入力欄を離れたときの案 A・「保存待ちに入れる」の案 B）。読む表示のキー・案のバッジ・書き込めない編集の理由・指されている項目を消すときの知らせ |
| [detail-full](../../pages/detail-full/325/index.md) | 詳細の全画面の編集の表示 |
| [decisions](../../pages/decisions/325/index.md) | 項目を足す入口と、ボード・マップ・表の保存待ちのバッジ |
| [tasks](../../pages/tasks/325/index.md) | 項目を足す入口と、ボード・表の保存待ちのバッジ・ID を持たない足すタスクのカード |
| [docs](../../pages/docs/325/index.md) | 項目を足す入口と、カード・ボード・表の保存待ちのバッジ |
| [records](../../pages/records/325/index.md) | 項目を足す入口（開いているタブの種類）と、表の保存待ちのバッジ |
| [pending-edits](../../pages/pending-edits/325/index.md) | 保存待ちのパネル（消す件数をボタンに出す案 A・消す行を先頭に分ける案 B）と、トップバーの保存の入口（件数だけの案 A・保存のボタンを並べる案 B）。1 件ずつの取り消し・書き込めない編集・つながらない |
| [workspace-settings](../../pages/workspace-settings/325/index.md) | 設定の画面 |
| [settings-panel](../../pages/settings-panel/325/index.md) | 設定の画面の入口（パネルの下端の案 A・題名の案 B・トップバーのボタンの案 C・パネルのタブの案 D） |

| 部品 | 中身 |
| --- | --- |
| [pending-mark](../../components/pending-mark/index.html) | 保存待ちのバッジ |
| [topbar](../../components/topbar/index.html#pending-a) | トップバーの保存待ちの件数 |
