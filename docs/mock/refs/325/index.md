# 325

利用者が画面から項目を編集・追加・削除し、まとめて保存できるようにする（[PR #325](https://github.com/shuhei1101/mindstella/pull/325)・起点 [Issue #48](https://github.com/shuhei1101/mindstella/issues/48)）。
画面は、develop のプレビューのスクリプト（`plugins/mindstella/skills/mindmap/preview/` の build がつなぐ順）と #237 の見本の記録（`../237/assets/data.js`）を読み、この PR の編集・保存待ち・まとめての保存を `assets/edit.js` で重ねたもの。
サーバーの代わり（`assets/mock.js`）が、保存待ちの編集を当てた記録を返し、書き換えの知らせで画面に読み直させる。
保存待ちの編集はモックでは端末の作業の保存領域に見本ごとに持ち、開き直しても残る（モック専用の操作列の「見本の保存待ちに戻す」で見本へ戻す）。
保存の結果は見本で決まる（書き込めない編集の見本は D-17 が溜めた後に AI に書き換えられ、D-8 が指されている。つながらない見本は保存に失敗する）。
モック専用の操作列で、論点の案と見本を切り替える。

画面のモックは、読み込む今の画面のスクリプトが #644 で削除されて描けなくなったため、#667 で削除した。

| 部品 | 中身 |
| --- | --- |
| [pending-mark](../../components/pending-mark/index.html) | 保存待ちのバッジ |
| [topbar](../../components/topbar/index.html#pending-a) | トップバーの保存待ちの件数 |
