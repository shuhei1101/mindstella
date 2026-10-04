# 79

プレビューで前回からの差分を表示する（[PR #79](https://github.com/shuhei1101/mindstella/pull/79)）。
画面は 52 の見本のデータに変更履歴を足したもの（`assets/history.js`）と、71 のスクリプトに差分の表示を足したもの（`assets/app.js`）を読み、スタイルは 65・71 の上に差分の分（`assets/style.css`）を重ねる。
画面は変更履歴から「前回開いてから」を選んだ状態で開く（データの前回開いた日時は 10/04 13:05）。
モック専用の操作列で、状態（端末で初めて開く・保持する回数が 0 ほか）、シナリオの場面（前回開いてから・古いまとまりを選ぶ・まだまとめていない変更・前後を組み立てられない古いまとまり）、開いたまま届く書き換え（D-022）、抜ける操作の案（A 札と外すボタン・B 押し直し）を切り替える。

| 画面 | 中身 |
| --- | --- |
| [overview](../../pages/overview/79/standard/index.html) | 概要のタイルの項目に新規・変更の印 |
| [decisions](../../pages/decisions/79/standard/index.html) | 検討事項の表・ボード・マップの印（D-005 変更・D-019 変更・D-037 新規）と、変更履歴のモーダル・トップバーの札 |
| [tasks](../../pages/tasks/79/standard/index.html) | 印の付く項目が無いタブ |
| [docs](../../pages/docs/79/standard/index.html) | 資料のカード・ボード・表の印（A-003・A-005 変更） |
| [records](../../pages/records/79/standard/index.html) | メモの表の印（N-004 新規） |
| [detail-panel](../../pages/detail-panel/79/standard/index.html) | D-005 の差分（キー・本文・表の行・flowchart・Raw）。D-019 は本文の前の版を組み立てられない。A-003 は sequenceDiagram、A-005 は gantt。古いまとまり「フェーズの切り方を決める」の D-005 は前後を組み立てられない |
| [detail-full](../../pages/detail-full/79/standard/index.html) | 詳細の全画面の D-005 の差分 |
| [diagram-viewer](../../pages/diagram-viewer/79/standard/index.html) | 図の拡大の D-005 の図の色・凡例・消したもの・Raw の差分 |

| 部品 | 中身 |
| --- | --- |
| [diff-marks](../../components/diff-marks/index.html) | 差分の表示の部品の状態ごとの見本 |
