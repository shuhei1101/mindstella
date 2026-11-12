# module

クラス / 関数 / 関数型 インデックス（単体テストの元）

## 目次

<!-- table: data -->

| ページ | 概要 |
| --- | --- |
| [プレビュー / app](./MOD-489-1.tsx.yaml) | QueryClientProvider と RouterProvider を組み、書き換えの知らせへつなぐ（書き換えの知らせへの接続） |
| [プレビュー / query-client](./MOD-489-3.ts.yaml) | knowledge の規約『QueryClient』の defaultOptions |
| [プレビュー / router](./MOD-489-4.tsx.yaml) | SPA を配るパスの頭（インターフェース定義『SPAの配信』） |
| [プレビュー / preview-shell](./MOD-489-2.tsx.yaml) | `tab` の画面と、詳細・変更履歴・保存待ちのパネルを重ねて描く SPA の外枠 |
| [プレビュー / goal-tile](./MOD-489-39.tsx.yaml) | `derived.goal` の数・棒・納品物。ゴールが無いときはフェーズ別の進捗 |
| [プレビュー / list-tile](./MOD-489-40.tsx.yaml) | 要見直し・保留・進行中のタスクに共通の、件数と名前と「すべて表示」 |
| [プレビュー / next-tile](./MOD-489-41.tsx.yaml) | `derived.next` を並べる |
| [プレビュー / progress-table](./MOD-489-42.tsx.yaml) | `derived.progress` の表 |
| [プレビュー / overview-screen](./MOD-489-43.tsx.yaml) | 画面設計『概要.tsx』のトップバーとタイルを描く。記録が読めないときは detail の行を出す |
| [プレビュー / decisions-screen](./MOD-489-18.tsx.yaml) | 画面設計『検討事項.tsx』の要素と操作を描く |
| [プレビュー / map-layout](./MOD-489-19.ts.yaml) | マップの木を elkjs へ渡す形に組み、配置の結果を節と枝にする |
| [プレビュー / decision-map](./MOD-489-16.tsx.yaml) | 対象 → カテゴリー → フェーズ → 検討事項の木を描き、節のロックと拡大・縮小を持つ |
| [プレビュー / decision-outline](./MOD-489-17.tsx.yaml) | 幅 900px 以下のマップ |
| [プレビュー / decision-board](./MOD-489-15.tsx.yaml) | 状態ごとの列に検討事項のカードを並べる |
| [プレビュー / tasks-screen](./MOD-489-53.tsx.yaml) | 画面設計『タスク.tsx』の要素と操作を描く |
| [プレビュー / task-board](./MOD-489-52.tsx.yaml) | 状態ごとの列にタスクのカードを並べる |
| [プレビュー / docs-screen](./MOD-489-36.tsx.yaml) | 画面設計『資料.tsx』の要素と操作を描く |
| [プレビュー / doc-cards](./MOD-489-35.tsx.yaml) | 資料を納品物を先頭にカードで並べる |
| [プレビュー / doc-board](./MOD-489-34.tsx.yaml) | 状態ごとの列に資料のカードを並べる |
| [プレビュー / records-screen](./MOD-489-44.tsx.yaml) | 画面設計『記録の表.tsx』の要素と操作を描く |
| [プレビュー / detail-panel](./MOD-489-32.tsx.yaml) | 画面設計『詳細パネル.tsx』の要素と操作を描く |
| [プレビュー / detail-header](./MOD-489-24.tsx.yaml) | 戻る・進む・全画面・エクスポート・編集・閉じるを並べる |
| [プレビュー / option-list](./MOD-489-29.tsx.yaml) | 検討事項の案をカードで並べる |
| [プレビュー / related-list](./MOD-489-30.tsx.yaml) | 前提・後続・関連タスク・経緯・関連・参照元を並べる |
| [プレビュー / value-text](./MOD-489-31.tsx.yaml) | 文字列の値を mdmark で描く |
| [プレビュー / body-view](./MOD-489-21.tsx.yaml) | 本文の形式と差分の表示に応じて描く部品を選ぶ |
| [プレビュー / key-diff](./MOD-489-28.tsx.yaml) | 差分の表示の間、キーの前後の値を並べる |
| [プレビュー / detail-editor](./MOD-489-23.tsx.yaml) | 編集の表示の入力欄を描き、入力欄を離れたらキーの編集を溜める |
| [プレビュー / diagram-block](./MOD-489-26.tsx.yaml) | 本文の図に拡大表示・Raw・コピーを置き、図の差分を描く |
| [プレビュー / detail-resizer](./MOD-489-25.tsx.yaml) | 詳細パネルの幅をドラッグとキーで変える |
| [プレビュー / item-add-panel](./MOD-489-27.tsx.yaml) | 項目の追加の入力。タイトルを離れたときに `item-add` を溜め、残りのキーは返った仮の ID で書き換える |
| [プレビュー / detail-comments](./MOD-489-22.tsx.yaml) | 詳細パネル・詳細の全画面の下端のコメントの入力と、レビュー中のコメントの一覧（並びの切り替え・修正・削除・元に戻す・続きを読む）、本文の選択から出す選んだ箇所のコメントの入口を描く |
| [プレビュー / detail-fullscreen](./MOD-489-20.tsx.yaml) | 画面設計『詳細の全画面.tsx』の要素と操作を描く |
| [プレビュー / diagram-viewer](./MOD-489-33.tsx.yaml) | 画面設計『図の拡大.tsx』の要素と操作を描く |
| [プレビュー / history-dialog](./MOD-489-38.tsx.yaml) | 画面設計『変更履歴.tsx』の要素と操作を描く |
| [プレビュー / pending-edits-panel](./MOD-489-37.tsx.yaml) | 画面設計『保存待ちのパネル.tsx』の要素と操作を描く |
| [プレビュー / workspace-settings-screen](./MOD-489-51.tsx.yaml) | 画面設計『設定の画面.tsx』の要素と操作を描く |
| [プレビュー / form](./MOD-489-50.ts.yaml) | 設定の画面の入力の Zod スキーマ |
| [プレビュー / settings-confirm](./MOD-489-45.tsx.yaml) | 部品設計『既定の保存の確かめ.tsx』の props・イベント・状態を持つ |
| [プレビュー / settings-panel](./MOD-489-46.tsx.yaml) | 部品設計『表示の設定.tsx』の props・イベント・状態を持つ |
| [プレビュー / display-settings-panel](./MOD-489-47.tsx.yaml) | 画面設計『表示の設定.tsx』の要素と操作を描く。上書きを端末の保存領域に書き、既定にするで確かめのモーダルを開く |
| [プレビュー / settings-confirm-dialog](./MOD-489-48.tsx.yaml) | 画面設計『既定の保存の確かめ.tsx』の要素と操作を描く。shadcn/ui の Dialog に部品『既定の保存の確かめ』を置き、`open`・`onOpenChange` は親が持つ |
| [プレビュー / use-save-display-default](./MOD-489-49.ts.yaml) | ワークスペースの既定の書き換えの mutation |
| [プレビュー / comments-panel](./MOD-489-5.tsx.yaml) | 画面設計『コメントの一覧.tsx』の要素と操作を描く。search の `thread`・`review` でスレッド・レビュー中の書き込みの画面に切り替え、`tstatus`・`ttag` で絞る |
| [プレビュー / review-view](./MOD-489-6.tsx.yaml) | 画面設計『レビュー中の書き込み.tsx』の要素と操作を描く。チェックの状態は画面が持つ |
| [プレビュー / reply-form](./MOD-489-7.tsx.yaml) | 部品設計『返信の入力.tsx』の props・イベント・状態を持つ |
| [プレビュー / review-edit-form](./MOD-489-8.tsx.yaml) | レビュー中の書き込みの本文をその場で書き換える入力欄と「キャンセル」「修正」 |
| [プレビュー / thread-post](./MOD-489-9.tsx.yaml) | 部品設計『スレッドの書き込み.tsx』の props・イベント・状態を持つ |
| [プレビュー / thread-row](./MOD-489-10.tsx.yaml) | 部品設計『スレッドの行.tsx』の props・イベント・状態を持つ |
| [プレビュー / thread-state](./MOD-489-11.tsx.yaml) | スレッドの状態の札・レビュー中の印・未読の札 |
| [プレビュー / use-comment-data](./MOD-489-12.ts.yaml) | コメントの一覧・スレッド・レビュー中の書き込みの画面が読む値 |
| [プレビュー / use-threads](./MOD-489-13.ts.yaml) | スレッドの状態の書き換えと利用者の既読の mutation |
| [プレビュー / thread-view](./MOD-489-14.tsx.yaml) | 画面設計『スレッド.tsx』の要素と操作を描く。開いたら未読のスレッドを既読にする |
| [プレビュー / __root](./MOD-489-54.tsx.yaml) | 子のルートを描く外枠。描画中のエラーは ErrorBoundary で受ける |
| [プレビュー / index](./MOD-489-55.tsx.yaml) | SPA のルート（`/`）。search の検証と先読みをして `PreviewShell` を描く |
| [プレビュー / api-client](./MOD-489-56.ts.yaml) | orval の mutator。fetch で呼び、成功は本文と status を返し、失敗は AppError を投げる |
| [プレビュー / events-client](./MOD-489-57.ts.yaml) | インターフェース定義『書き換えの知らせ』 |
| [プレビュー / libraries](./MOD-489-58.ts.yaml) | 描画のライブラリ（mdmark・mermaid・elkjs・marked・jsdiff）を、今の画面と同じ配信元と版から `integrity` で確かめて読む（制約「描画のライブラリ」） |
| [プレビュー / icon](./MOD-489-74.tsx.yaml) | 24px の枠に描いた線のアイコンと、状態の 10px の印 |
| [プレビュー / topbar](./MOD-489-88.tsx.yaml) | 部品設計『トップバー.tsx』の props・イベント・状態を持つ |
| [プレビュー / button](./MOD-489-89.tsx.yaml) | shadcn/ui の Button（Base UI 版）。見た目の違いは variants（default・secondary・ghost・outline・destructive）で持つ |
| [プレビュー / table](./MOD-489-96.tsx.yaml) | shadcn/ui の Table |
| [プレビュー / dialog](./MOD-489-91.tsx.yaml) | shadcn/ui の Dialog（Base UI 版） |
| [プレビュー / sheet](./MOD-489-95.tsx.yaml) | shadcn/ui の Sheet（Base UI 版） |
| [プレビュー / popover](./MOD-489-93.tsx.yaml) | shadcn/ui の Popover（Base UI 版） |
| [プレビュー / checkbox](./MOD-489-90.tsx.yaml) | shadcn/ui の Checkbox（Base UI 版） |
| [プレビュー / input](./MOD-489-92.tsx.yaml) | shadcn/ui の Input |
| [プレビュー / textarea](./MOD-489-97.tsx.yaml) | shadcn/ui の Textarea |
| [プレビュー / select](./MOD-489-94.tsx.yaml) | shadcn/ui の Select（Base UI 版） |
| [プレビュー / tooltip](./MOD-489-98.tsx.yaml) | shadcn/ui の Tooltip（Base UI 版） |
| [プレビュー / table](./MOD-489-85.tsx.yaml) | 部品設計『表.tsx』の props・イベント・状態を持つ |
| [プレビュー / filter-drawer](./MOD-489-70.tsx.yaml) | 部品設計『絞り込み.tsx』の props・イベント・状態を持つ |
| [プレビュー / view-switch](./MOD-489-99.tsx.yaml) | 部品設計『表示形式の切り替え.tsx』の props・イベント・状態を持つ |
| [プレビュー / diff-mark](./MOD-489-65.tsx.yaml) | 部品設計『差分の印.tsx』の props・イベント・状態を持つ |
| [プレビュー / removed-band](./MOD-489-80.tsx.yaml) | 部品設計『消した項目の帯.tsx』の props・イベント・状態を持つ |
| [プレビュー / history-dialog](./MOD-489-71.tsx.yaml) | 部品設計『変更履歴.tsx』の props・イベント・状態を持つ |
| [プレビュー / diff-minimap](./MOD-489-66.tsx.yaml) | 部品設計『差分のミニマップ.tsx』の props・イベント・状態を持つ |
| [プレビュー / body-diff-layout-switch](./MOD-489-61.tsx.yaml) | 部品設計『本文の差分の並べ方の切り替え.tsx』の props・イベント・状態を持つ |
| [プレビュー / side-by-side-body-diff](./MOD-489-84.tsx.yaml) | 部品設計『左右に並べた本文の差分.tsx』の props・イベント・状態を持つ |
| [プレビュー / html-body-diff](./MOD-489-72.tsx.yaml) | 部品設計『HTMLの本文の差分.tsx』の props・イベント・状態を持つ |
| [プレビュー / html-body-frame](./MOD-489-73.tsx.yaml) | 部品設計『HTMLの本文の枠.tsx』の props・イベント・状態を持つ |
| [プレビュー / markdown-body](./MOD-489-77.tsx.yaml) | 部品設計『Markdownの本文.tsx』の props・イベント・状態を持つ |
| [プレビュー / term-tip](./MOD-489-87.tsx.yaml) | 部品設計『本文の印のツールチップ.tsx』の props・イベント・状態を持つ |
| [プレビュー / doc-export-menu](./MOD-489-67.tsx.yaml) | 部品設計『資料のエクスポートのメニュー.tsx』の props・イベント・状態を持つ |
| [プレビュー / withdrawn-badge](./MOD-489-100.tsx.yaml) | 部品設計『取り下げの札.tsx』の props・イベント・状態を持つ |
| [プレビュー / body-format-badge](./MOD-489-62.tsx.yaml) | 部品設計『本文の形式の札.tsx』の props・イベント・状態を持つ |
| [プレビュー / tag-list](./MOD-489-86.tsx.yaml) | 部品設計『タグの並び.tsx』の props・イベント・状態を持つ |
| [プレビュー / chips-input](./MOD-489-63.tsx.yaml) | 部品設計『チップの入力.tsx』の props・イベント・状態を持つ |
| [プレビュー / comment-mark](./MOD-489-64.tsx.yaml) | 部品設計『コメントの印.tsx』の props・イベント・状態を持つ |
| [プレビュー / pending-mark](./MOD-489-78.tsx.yaml) | 部品設計『保存待ちの印.tsx』の props・イベント・状態を持つ |
| [プレビュー / dom-host](./MOD-489-68.tsx.yaml) | React の外で組み立てた要素を置く入れ物 |
| [プレビュー / filter-chips](./MOD-489-69.tsx.yaml) | 絞り込みの条件のチップ |
| [プレビュー / board](./MOD-489-60.tsx.yaml) | 状態ごとの列にカードを並べたボードと項目のカード |
| [プレビュー / list-columns](./MOD-489-75.tsx.yaml) | 一覧の表の共通の列 |
| [プレビュー / list-screen](./MOD-489-76.tsx.yaml) | 一覧の画面の枠（表示形式の切り替え・項目の追加・消した項目の帯・絞り込みのドロワーと表の状態） |
| [プレビュー / blocked-note](./MOD-489-59.tsx.yaml) | 書き込めない理由の表示 |
| [プレビュー / review-body-fold](./MOD-489-81.tsx.yaml) | 部品設計『本文の折りたたみ.tsx』の props・イベント・状態を持つ |
| [プレビュー / selection-comment](./MOD-489-82.tsx.yaml) | 部品設計『選んだ箇所のコメントの入口.tsx』の props・イベント・状態を持つ |
| [プレビュー / send-form](./MOD-489-83.tsx.yaml) | 部品設計『コメントの入力.tsx』の props・イベント・状態を持つ |
| [プレビュー / post-body](./MOD-489-79.tsx.yaml) | 書き込みの本文を Markdown として描く |
| [プレビュー / app-error](./MOD-489-101.ts.yaml) | 失敗した応答から作るエラー。`detail` を画面に出す |
| [プレビュー / preview-search](./MOD-489-120.ts.yaml) | SPA の search params（インターフェース定義『SPAを開く』の request）の Zod スキーマと、記録に合わない値を外す処理、今の画面へ写すハッシュ |
| [プレビュー / records](./MOD-489-121.ts.yaml) | 記録の型・索引・関係する項目（今の画面の `core/records.ts` と同じ振る舞い） |
| [プレビュー / filters](./MOD-489-110.ts.yaml) | 画面ごとの絞り込みの条件を行に当てる計算 |
| [プレビュー / diff](./MOD-489-105.ts.yaml) | 差分の表示の計算（今の画面の `core/diff.ts` と同じ振る舞い |
| [プレビュー / edits](./MOD-489-109.ts.yaml) | 保存待ちの編集を記録に重ねる計算（今の画面の `core/edits.ts` と同じ振る舞い） |
| [プレビュー / doc-export](./MOD-489-107.ts.yaml) | 資料のエクスポートの HTML と Markdown の組み立て（今の画面の `core/doc-export.ts` と同じ振る舞い） |
| [プレビュー / body-links](./MOD-489-102.ts.yaml) | 描いた本文に、見出しのリンク・本文の印・項目の ID のリンクを付ける処理（今の画面の `core/libs.ts` の `linkHeadings`・`linkBody` と同じ振る舞い） |
| [プレビュー / markdown-decorate](./MOD-489-117.ts.yaml) | 描いた Markdown の本文の見せ方（表の列の幅・固定・見出しの固定・しま模様・セクションの折りたたみ・コードブロックの札とコピー・Alert の見出し） |
| [プレビュー / minimap](./MOD-489-118.ts.yaml) | 差分のミニマップの印の計算と操作 |
| [プレビュー / body-render](./MOD-489-103.ts.yaml) | 本文の差分の描画（足した・消した塊・語の面・図の差分） |
| [プレビュー / side-by-side](./MOD-489-122.ts.yaml) | 左右に並べた本文の差分の組み立て |
| [プレビュー / html-body-diff](./MOD-489-112.ts.yaml) | HTML の本文の差分の組み立て |
| [プレビュー / html-frame](./MOD-489-113.ts.yaml) | スクリプトを動かさない HTML の本文の枠の組み立て |
| [プレビュー / term-tips](./MOD-489-123.ts.yaml) | 本文の印のツールチップと、見出しへの送り・示す箇所 |
| [プレビュー / list-rows](./MOD-489-115.ts.yaml) | 一覧の行の絞り込み・並べ替え・ドロワーの条件の組み立て |
| [プレビュー / format](./MOD-489-111.ts.yaml) | 日時と値の文字の組み立て |
| [プレビュー / dom-parts](./MOD-489-108.ts.yaml) | mdmark が描いた本文の中へ足す要素の組み立て |
| [プレビュー / lock](./MOD-489-116.ts.yaml) | 注目の起点のロックの判定と鍵の震え |
| [プレビュー / comments](./MOD-489-104.ts.yaml) | コメントの一覧・スレッド・レビュー中の書き込みの計算（今の画面の `screens/comments.ts`・`components/thread-row.ts` の DOM に触らない関数と同じ振る舞い） |
| [プレビュー / display](./MOD-489-106.ts.yaml) | 表示の設定の計算（今の画面の `components/settings-panel.ts`・`settings-confirm.ts` の DOM に触らない関数と、`app.ts` の既定に戻すと同じ振る舞い） |
| [プレビュー / post-links](./MOD-489-119.ts.yaml) | 書き込みの描いた本文に、項目の ID のボタンとまとまりのリンクを付ける |
| [プレビュー / voice](./MOD-489-124.ts.yaml) | コメント・返信の入力の録音と、カーソルの位置への挿入（今の画面の `core/voice.ts` と同じ振る舞い） |
| [プレビュー / cn](./MOD-489-135.ts.yaml) | clsx と tailwind-merge でクラス名を 1 つにする |
| [プレビュー / connection-store](./MOD-489-136.ts.yaml) | 書き換えの知らせがつながっているか（インターフェース定義『SPAを開く』の制約「接続の状態」） |
| [プレビュー / theme-store](./MOD-489-141.ts.yaml) | 今の画面と同じキー。値の JSON の `theme` だけを読み書きし、他のキーは残す |
| [プレビュー / prefs-store](./MOD-489-140.ts.yaml) | 表の列・ピン留め・差分のミニマップ・本文の差分の並べ方・本文の見せ方・絞り込みの条件・表示する種類・ネットワークの見た目・コメントの一覧のピン止め・レビュー中のコメントの並びを、今の画面と同じ `localStorage` のキーで読み書きする（制約「端末の保存領域」） |
| [プレビュー / edit-session-store](./MOD-489-138.ts.yaml) | 開いている追加の入力と、直前の保存で書き込めなかった編集 |
| [プレビュー / display-notice-store](./MOD-489-137.ts.yaml) | 表示の設定の知らせ（ワークスペースの既定が変わった知らせと、表示の設定のパネルの `message`） |
| [プレビュー / location-highlight-store](./MOD-489-139.ts.yaml) | コメントの一覧（レビュー中の書き込みの行・スレッドの向けた項目）から開いた項目の中で示す箇所 |
| [プレビュー / index](./MOD-489-142.css.yaml) | Tailwind を読み、`--color-*: initial` で標準のパレットを消し、`@theme inline` でトークンを割り当てる |
| [プレビュー / tokens](./MOD-489-143.css.yaml) | デザイン方針のトークンを :root の 3 ティア（プリミティブ・セマンティック・派生）で持つ。値は採用した見本（`docs/mock/styles/shadcn-swiss-cards/`）から写す |
| [プレビュー / preview-queries](./MOD-489-125.ts.yaml) | SPA が読む query（記録・レビュー中のコメント・保存待ちの編集・スレッド）と invalidate |
| [プレビュー / use-preview-search](./MOD-489-129.ts.yaml) | search の読み書き |
| [プレビュー / use-diff-view](./MOD-489-127.ts.yaml) | 差分の表示の時点と、項目ごとの印を返す |
| [プレビュー / use-edits](./MOD-489-128.ts.yaml) | 保存待ちの編集を溜める・取り消す・まとめて保存する mutation |
| [プレビュー / use-screen-filters](./MOD-489-132.ts.yaml) | 画面の絞り込みの条件を URL と端末の保存領域で持つ（制約「保存した絞り込みの条件」） |
| [プレビュー / use-records](./MOD-489-130.ts.yaml) | 記録に保存待ちの編集を重ねた索引を読む |
| [プレビュー / use-screen-edit](./MOD-489-131.ts.yaml) | 一覧の画面の編集の入口を組む |
| [プレビュー / use-visible-kinds](./MOD-489-133.ts.yaml) | 表示する種類を返す |
| [プレビュー / use-comments](./MOD-489-126.ts.yaml) | レビュー中の書き込みを溜める・書き換える・消す・まとめて送る mutation と、書きかけの保存 |
| [プレビュー / use-voice-input](./MOD-489-134.ts.yaml) | 文字起こしの可否の query と、コメント・返信の入力の録音・文字起こし・すぐ送るの props |
| [サーバー / 移行 / tags_to_vocabulary.py](./MOD-489-185.py.yaml) | サーバー / 移行 / tags_to_vocabulary.py |
| [サーバー / 移行 / remove_tag_vocabulary.py](./MOD-489-186.py.yaml) | サーバー / 移行 / remove_tag_vocabulary.py |
| [サーバー / 移行 / tags_to_objects.py](./MOD-489-187.py.yaml) | サーバー / 移行 / tags_to_objects.py |
| [サーバー / 移行 / field_to_playbooks.py](./MOD-489-182.py.yaml) | サーバー / 移行 / field_to_playbooks.py |
| [サーバー / 移行 / answer_to_adopted_option.py](./MOD-489-183.py.yaml) | サーバー / 移行 / answer_to_adopted_option.py |
| [サーバー / 移行 / submissions_to_threads.py](./MOD-489-184.py.yaml) | サーバー / 移行 / submissions_to_threads.py |
| [プレビュー / 入口 / app.ts](./MOD-489-171.ts.yaml) | プレビューを開いたときに記録を読み（配る書き出しは埋め込みから、サーバーの配信は『記録の取得』から）、URL のハッシュが指す画面を描き、操作を画面の移動・書き換えの知らせ・コメントの読み書き・端末の保存領域につなぐ。 |
| [プレビュー / 画面と部品 / body-diff-layout-switch.ts](./MOD-489-205.ts.yaml) | プレビュー / 画面と部品 / body-diff-layout-switch.ts |
| [プレビュー / 画面と部品 / chips-input.ts](./MOD-489-243.ts.yaml) | プレビュー / 画面と部品 / chips-input.ts |
| [プレビュー / 画面と部品 / comment-mark.ts](./MOD-489-215.ts.yaml) | プレビュー / 画面と部品 / comment-mark.ts |
| [プレビュー / 画面と部品 / diff-mark.ts](./MOD-489-229.ts.yaml) | プレビュー / 画面と部品 / diff-mark.ts |
| [プレビュー / 画面と部品 / diff-minimap.ts](./MOD-489-203.ts.yaml) | プレビュー / 画面と部品 / diff-minimap.ts |
| [プレビュー / 画面と部品 / doc-export-menu.ts](./MOD-489-241.ts.yaml) | プレビュー / 画面と部品 / doc-export-menu.ts |
| [プレビュー / 画面と部品 / filter-drawer.ts](./MOD-489-233.ts.yaml) | プレビュー / 画面と部品 / filter-drawer.ts |
| [プレビュー / 画面と部品 / history-dialog.ts](./MOD-489-230.ts.yaml) | プレビュー / 画面と部品 / history-dialog.ts |
| [プレビュー / 画面と部品 / markdown-body.ts](./MOD-489-207.ts.yaml) | プレビュー / 画面と部品 / markdown-body.ts |
| [プレビュー / 画面と部品 / pending-mark.ts](./MOD-489-240.ts.yaml) | プレビュー / 画面と部品 / pending-mark.ts |
| [プレビュー / 画面と部品 / removed-band.ts](./MOD-489-234.ts.yaml) | プレビュー / 画面と部品 / removed-band.ts |
| [プレビュー / 画面と部品 / reply-form.ts](./MOD-489-237.ts.yaml) | プレビュー / 画面と部品 / reply-form.ts |
| [プレビュー / 画面と部品 / review-body-fold.ts](./MOD-489-208.ts.yaml) | プレビュー / 画面と部品 / review-body-fold.ts |
| [プレビュー / 画面と部品 / selection-comment.ts](./MOD-489-228.ts.yaml) | プレビュー / 画面と部品 / selection-comment.ts |
| [プレビュー / 画面と部品 / send-form.ts](./MOD-489-214.ts.yaml) | プレビュー / 画面と部品 / send-form.ts |
| [プレビュー / 画面と部品 / settings-confirm.ts](./MOD-489-231.ts.yaml) | プレビュー / 画面と部品 / settings-confirm.ts |
| [プレビュー / 画面と部品 / settings-panel.ts](./MOD-489-204.ts.yaml) | プレビュー / 画面と部品 / settings-panel.ts |
| [プレビュー / 画面と部品 / side-by-side-body-diff.ts](./MOD-489-239.ts.yaml) | プレビュー / 画面と部品 / side-by-side-body-diff.ts |
| [プレビュー / 画面と部品 / table.ts](./MOD-489-209.ts.yaml) | プレビュー / 画面と部品 / table.ts |
| [プレビュー / 画面と部品 / tag-list.ts](./MOD-489-242.ts.yaml) | プレビュー / 画面と部品 / tag-list.ts |
| [プレビュー / 画面と部品 / term-tip.ts](./MOD-489-236.ts.yaml) | プレビュー / 画面と部品 / term-tip.ts |
| [プレビュー / 画面と部品 / thread-post.ts](./MOD-489-238.ts.yaml) | プレビュー / 画面と部品 / thread-post.ts |
| [プレビュー / 画面と部品 / thread-row.ts](./MOD-489-217.ts.yaml) | プレビュー / 画面と部品 / thread-row.ts |
| [プレビュー / 画面と部品 / topbar.ts](./MOD-489-223.ts.yaml) | プレビュー / 画面と部品 / topbar.ts |
| [プレビュー / 画面と部品 / view-switch.ts](./MOD-489-222.ts.yaml) | プレビュー / 画面と部品 / view-switch.ts |
| [プレビュー / 画面と部品 / withdrawn-badge.ts](./MOD-489-235.ts.yaml) | プレビュー / 画面と部品 / withdrawn-badge.ts |
| [プレビュー / 基盤 / api.ts](./MOD-489-196.ts.yaml) | プレビュー / 基盤 / api.ts |
| [プレビュー / 差分 / diff.ts](./MOD-489-173.ts.yaml) | 差分の表示の計算。変更履歴で選んだ時点から印を付ける項目を決め、項目の `history` から前の版を組み立て、本文・記法の行と図の要素を比べる。DOM には触らず、描くのは画面が持つ。 |
| [プレビュー / 基盤 / doc-export.ts](./MOD-489-201.ts.yaml) | プレビュー / 基盤 / doc-export.ts |
| [プレビュー / 基盤 / dom.ts](./MOD-489-199.ts.yaml) | プレビュー / 基盤 / dom.ts |
| [プレビュー / 基盤 / edits.ts](./MOD-489-202.ts.yaml) | プレビュー / 基盤 / edits.ts |
| [プレビュー / 基盤 / libs.ts](./MOD-489-198.ts.yaml) | プレビュー / 基盤 / libs.ts |
| [プレビュー / 基盤 / lock.ts](./MOD-489-200.ts.yaml) | プレビュー / 基盤 / lock.ts |
| [プレビュー / 基盤 / records.ts](./MOD-489-194.ts.yaml) | プレビュー / 基盤 / records.ts |
| [プレビュー / 基盤 / router.ts](./MOD-489-195.ts.yaml) | プレビュー / 基盤 / router.ts |
| [プレビュー / 基盤 / voice.ts](./MOD-489-197.ts.yaml) | プレビュー / 基盤 / voice.ts |
| [プレビュー / 画面と部品 / graph.ts](./MOD-489-213.ts.yaml) | プレビュー / 画面と部品 / graph.ts |
| [プレビュー / 画面と部品 / looks.ts](./MOD-489-216.ts.yaml) | プレビュー / 画面と部品 / looks.ts |
| [プレビュー / 画面と部品 / comments.ts](./MOD-489-218.ts.yaml) | プレビュー / 画面と部品 / comments.ts |
| [プレビュー / 画面と部品 / decisions.ts](./MOD-489-212.ts.yaml) | プレビュー / 画面と部品 / decisions.ts |
| [プレビュー / 画面と部品 / detail-edit.ts](./MOD-489-221.ts.yaml) | プレビュー / 画面と部品 / detail-edit.ts |
| [プレビュー / 画面と部品 / detail.ts](./MOD-489-206.ts.yaml) | プレビュー / 画面と部品 / detail.ts |
| [プレビュー / 画面と部品 / diagram-viewer.ts](./MOD-489-227.ts.yaml) | プレビュー / 画面と部品 / diagram-viewer.ts |
| [プレビュー / 画面と部品 / docs.ts](./MOD-489-211.ts.yaml) | プレビュー / 画面と部品 / docs.ts |
| [プレビュー / 画面と部品 / overview.ts](./MOD-489-224.ts.yaml) | プレビュー / 画面と部品 / overview.ts |
| [プレビュー / 画面と部品 / pending-edits.ts](./MOD-489-219.ts.yaml) | プレビュー / 画面と部品 / pending-edits.ts |
| [プレビュー / 画面と部品 / records.ts](./MOD-489-225.ts.yaml) | プレビュー / 画面と部品 / records.ts |
| [プレビュー / 画面と部品 / search.ts](./MOD-489-226.ts.yaml) | プレビュー / 画面と部品 / search.ts |
| [プレビュー / 画面と部品 / settings.ts](./MOD-489-232.ts.yaml) | プレビュー / 画面と部品 / settings.ts |
| [プレビュー / 画面と部品 / tasks.ts](./MOD-489-210.ts.yaml) | プレビュー / 画面と部品 / tasks.ts |
| [プレビュー / 画面と部品 / workspace-settings.ts](./MOD-489-220.ts.yaml) | プレビュー / 画面と部品 / workspace-settings.ts |
| [サーバー / 移行 / backup.py](./MOD-489-180.py.yaml) | サーバー / 移行 / backup.py |
| [サーバー / ビルド / builder.py](./MOD-489-152.py.yaml) | ワークスペースの記録を 1 つの JSON にまとめ、プレビューの雛形に CSS と JavaScript を差し込む。配信はその雛形と記録をその場で返し、配る書き出しは同じ雛形に jsDelivr から取った描画のライブラリとライセンスの表示と記録を入れて書き出す。読み書きと検証と、依存と影響・ゴール判定（画面に出す値の計算）に依存する。 |
| [サーバー / 起動 / check_env.py](./MOD-489-191.py.yaml) | サーバー / 起動 / check_env.py |
| [サーバー / 点検 / checker.py](./MOD-489-162.py.yaml) | ワークスペースのスキーマ違反・ID の重複・参照切れ・本文のずれ・設定に無いフェーズを問題として洗い出す。読み書きと検証だけに依存し、ファイルを書かない。 |
| [サーバー / ClaudeCodeへの入力 / claude_input.py](./MOD-489-144.py.yaml) | ツールの呼び出しが運んだセッションの値を読み、ワークスペースごとに宛先を持つ。まとめて送った後に、そのワークスペースを指して最後にツールを呼んだセッションが生きているかを確かめてからペインへ 1 行の文字列を貼り、Claude Code の会話の記録に入ったかを確かめる。tmux と ps を子プロセスで呼び、会話の記録（jsonl）を読む。 |
| [サーバー / ゴール判定 / commands.py](./MOD-489-176.py.yaml) | サーバー / ゴール判定 / commands.py |
| [サーバー / コメント / comments.py](./MOD-489-147.py.yaml) | レビュー中のコメント（`comments.yaml`）と書きかけ（`drafts.yaml`）を読み書きし、チェックしたコメントをスレッドへ移す。文字起こしの結果の書き込み 1 件は、レビュー中に溜めずにすぐスレッドへ足す。箇所・スレッド・読み書きと検証に依存し、鍵は呼ぶ側（配信）が取る。 |
| [サーバー / 保存待ちの編集 / edits.py](./MOD-489-155.py.yaml) | プレビューで利用者が溜めた保存待ちの編集（`edits.yaml`）を読み書きし、まとめて保存するときに項目と設定へ当てる。読み書きと検証・入口（項目の追加と更新）・設定の更新・変更履歴に依存し、鍵は呼ぶ側（配信）が取る。例外はモジュール構成『読み書きと検証』の `EditInvalidError`・`EditNotFoundError`・`EditConflictError`・`EditsBlockedError`。単体テストは `tests/unit/scripts/test_edits.py` に置く。 |
| [サーバー / 起動 / ensure_server.py](./MOD-489-192.py.yaml) | サーバー / 起動 / ensure_server.py |
| [サーバー / 読み書きと検証 / errors.py](./MOD-489-190.py.yaml) | サーバー / 読み書きと検証 / errors.py |
| [サーバー / ゴール判定 / graph.py](./MOD-489-175.py.yaml) | サーバー / ゴール判定 / graph.py |
| [サーバー / 変更履歴 / history.py](./MOD-489-157.py.yaml) | 項目の変更履歴の 1 回分を作って積み、書き換えのまとまり（`changes.yaml`）・AI が最後に読んだ時点・前回開いた日時（`.mindstella-opened`）を読み書きし、読んだ時点からの変更を組み立てる。『読み書きと検証』にだけ依存し、書き込みは `save_change`・`save_batch` に任せる。 |
| [サーバー / HTMLの本文 / html_body.py](./MOD-489-145.py.yaml) | 資料の HTML の本文の開きタグに原文の行の印を足す処理と、原文の行の範囲の描いた文を取り出す処理。どちらも Python の標準ライブラリ `html.parser.HTMLParser` で原文を読む。 |
| [サーバー / セッションの値の注入 / inject_session.py](./MOD-489-150.py.yaml) | Claude Code の `PreToolUse` のフックが呼ぶスクリプト。mindstella のツールを呼んだセッションの作業フォルダ・tmux のペイン・設定のフォルダ・Claude Code のプロセスを、ツールの入力の `session` に入れて返す。 |
| [サーバー / 読み書きと検証 / kinds.py](./MOD-489-188.py.yaml) | サーバー / 読み書きと検証 / kinds.py |
| [サーバー / 起動 / launch.py](./MOD-489-193.py.yaml) | サーバー / 起動 / launch.py |
| [サーバー / 箇所 / locations.py](./MOD-489-165.py.yaml) | コメントが指す箇所（本文の行の範囲か項目の値のキーと、選んだ文）の形を確かめ、今の項目に合うかを確かめる。読み書きと検証だけに依存し、書き込まない。 |
| [サーバー / 移行 / migration_ops.py](./MOD-489-181.py.yaml) | サーバー / 移行 / migration_ops.py |
| [サーバー / 移行 / migrator.py](./MOD-489-179.py.yaml) | サーバー / 移行 / migrator.py |
| [サーバー / 検索 / query.py](./MOD-489-161.py.yaml) | 条件で項目を探してページに分け、返す量を選んで JSON か Markdown にし、1 件の中身と参照元、使っている属性名とタグを出す。読み書きと検証・タグの表記だけに依存し、ファイルを書かない。 |
| [サーバー / ワークスペースの README / readme.py](./MOD-489-153.py.yaml) | ワークスペースの直下の `README.md`（起動・接続のコマンド、スキルの呼び方、プレビューの URL の一覧）を組み立てて書く。`init`・`readme`・`preview_url` の 3 つのツールが同じ関数で書く。 |
| [サーバー / 未読へ戻す / reset_unread.py](./MOD-489-160.py.yaml) | Claude Code の `SessionStart` のフックが呼ぶスクリプト。作業フォルダとその直下のワークスペースを探し、ロックを取ってスレッドの書き込みを未読に戻す。スレッドと読み書きと検証に依存する。単体テストは `tests/unit/scripts/test_reset_unread.py` に置く。 |
| [サーバー / 配信 / serve.py](./MOD-489-169.py.yaml) | ワークスペースごとに `127.0.0.1` の空きポートでプレビューを配る。画面・記録・スレッド・書き換えの知らせを返し、レビュー中のコメント・書きかけ・まとめて送る・スレッドの状態の書き換え・スレッドの利用者の既読・設定の既定の書き換え・設定の再読み込み・書き込みをすぐ送るを受け付ける。まとめて送った後とすぐ送った後は Claude Code へ入力する。文字起こしの可否を返し、受けた音声を文字起こしのインターフェースへ渡す。ビルド（雛形と記録）とコメントとスレッドと Claude Code への入力と設定の更新と文字起こしと読み書きと検証に依存する。 |
| [サーバー / 入口 / server.py](./MOD-489-177.py.yaml) | サーバー / 入口 / server.py |
| [サーバー / 設定の更新 / settings_update.py](./MOD-489-166.py.yaml) | `update_settings` の引数を確かめ、設定のキーを置き換え、フェーズ・対象・カテゴリーの対応で項目の `phase`・`target`・`category` と `goal.phase`・カテゴリーの `target` を付け替えて、設定と種類ごとの YAML をまとめて書く。読み書きと検証だけに依存する。 |
| [サーバー / 読み書きと検証 / store.py](./MOD-489-189.py.yaml) | サーバー / 読み書きと検証 / store.py |
| [サーバー / タグの表記 / tag_text.py](./MOD-489-151.py.yaml) | タグを NFKC と小文字にそろえた表記にし、使われているタグのうち字面の近いものを並べる。検索から使う。 |
| [サーバー / スレッド / threads.py](./MOD-489-149.py.yaml) | スレッド（`threads.yaml`）を読み書きする。まとめて送られた利用者の書き込みを足し、AI の一覧・既読・返信・状態と要約の書き換え・取り込み済みを担い、画面へ返す形を作る。読み書きと検証だけに依存し、鍵は呼ぶ側（入口・コメント・配信・未読へ戻す）が取る。単体テストは `tests/unit/scripts/test_threads.py` に置く。 |
| [サーバー / 文字起こし / transcriber.py](./MOD-489-158.py.yaml) | 配信が音声を文字に起こすときに依存する文字起こしのインターフェースと、使えるかの確かめ・失敗の種類を持つ。サービスごとの呼び方は実装のモジュール、環境変数で実装を選ぶ処理は引き当てのモジュールが持ち、配信はこのモジュールだけを import する。どのモジュールも import しない。 |
| [サーバー / 文字起こしの引き当て / transcriber_registry.py](./MOD-489-159.py.yaml) | 環境変数で文字起こしの実装を選び、URL を確かめて作る。常駐サーバーの起動の入口だけが import し、文字起こし（抽象）と実装のモジュールに依存する。実装は抽象だけに依存するので、import は一方向になる（入口 → 引き当て → 実装 → 抽象）。 |
| [サーバー / 移行 / versions.py](./MOD-489-178.py.yaml) | サーバー / 移行 / versions.py |
| [サーバー / voice-pasteの文字起こし / voice_paste.py](./MOD-489-146.py.yaml) | 文字起こしのインターフェースの voice-paste の実装。プリセットの一覧を読み、音声を `multipart/form-data` で依頼し、ジョブの状態を取りに行って終わるまで待つ。HTTP は標準ライブラリの `urllib.request` で送り、文字起こしだけに依存する。 |
| [サーバー / 登録 / register.py](./MOD-489-163.py.yaml) | セットアップのスキルが Bash で呼ぶ登録のスクリプト。起動スクリプトを呼ぶ alias `mindstella`・`mindstella-{名前}` と、起動スクリプトが読む環境変数を、登録の置き場所のファイルとログインシェルの設定ファイルの印の範囲へ書く・読み返す・外す。 |
| [サーバー / ゴール判定](./MOD-489-148.yaml) | ゴールのフェーズまでの検討事項とゴールの納品物から、ゴールに届いたかを判定する `goal` の処理。判定は依存と影響（`graph.py`）、出力の形はツールの処理（`commands.py`）に置く。 |
| [サーバー / 依存と影響](./MOD-489-154.yaml) | 検討事項とタスクの依存をたどり、影響・次の候補・再開時の状況を出す。読み書きと検証だけに依存し、ファイルを書かない。 |
| [サーバー / 入口](./MOD-489-156.yaml) | 常駐する MCP サーバー `mindstella` を `127.0.0.1` の HTTP で待ち受け、ツールを登録し、ツールの引数を各機能へ渡して、結果を構造化の結果・エラーをツールのエラーにする。プレビューの配信と、常駐サーバーの状態と停止も同じプロセスに持つ。 |
| [サーバー / 移行](./MOD-489-164.yaml) | ワークスペースの版とプラグインの版を比べ、版ごとの移し替えの手順（`migrations/{版}/steps.yaml`）を並べる・写しを取って当てる・値を入れる・版を書き換える。読み書きと検証だけに依存する。 |
| [サーバー / 読み書きと検証](./MOD-489-167.yaml) | ワークスペースの YAML と本文を読み書きし、JSON Schema と突き合わせる。ほかの全てのモジュールがここに依存し、ここはほかに依存しない。 |
| [サーバー / 起動](./MOD-489-168.yaml) | 起動スクリプト（`bin/mindstella`）と SessionStart のフックが呼ぶ Python の部分。仮想環境の依存を確かめ、インストールしたプラグインのフォルダ・セッションの名前を作り、常駐サーバーが待ち受けているかを確かめて落ちていれば起動する。tmux と Claude Code の起動は起動スクリプト（bash）が持つ。 |
| [プレビュー / graph-screen](./MOD-489-244.tsx.yaml) | 画面設計『ネットワーク.tsx』の要素と操作を描く |
| [プレビュー / graph-canvas](./MOD-489-245.tsx.yaml) | 3D のキャンバスと重ねる層を描き、毎コマの描画を GraphRenderer に任せる |
| [プレビュー / graph-renderer](./MOD-489-246.ts.yaml) | 今の画面の graph.ts の視点・操作・毎コマの描画を、React に依存しない描画として移す |
| [プレビュー / graph-model](./MOD-489-247.ts.yaml) | ネットワークの玉と線、描く項目、絞る条件を求める |
| [プレビュー / looks](./MOD-489-248.ts.yaml) | ネットワークの 5 つの見た目の描き方 |
| [プレビュー / graph-store](./MOD-489-249.ts.yaml) | ネットワークのロックを、画面を離れても残るようにページの間だけ持つ |
| [プレビュー / look-select](./MOD-489-250.tsx.yaml) | ネットワークの見た目のドロップダウン |
| [プレビュー / search-dialog](./MOD-489-251.tsx.yaml) | 画面設計『全体の検索.tsx』の要素と操作を描く |
| [プレビュー / use-search-shortcut](./MOD-489-252.ts.yaml) | Ctrl+K（macOS は Cmd+K）で全体の検索を開く |
| [プレビュー / React](./MOD-489-170.yaml) | React のプレビューのファイルの並び・つながり・置き場所の決まり。各ファイルの設計書は `モジュール構成/frontend/` の下に置く。 |
| [プレビュー / 基盤](./MOD-489-172.yaml) | 画面が共通で使う土台。記録の索引と画面に出す値の計算、描画のライブラリの呼び出しと読めないときの知らせ、URL のハッシュと履歴、コメント・返信の入力の録音を持つ。 |
| [プレビュー / 画面と部品](./MOD-489-174.yaml) | 部品（表・トップバー・表示形式の切り替え）と画面。どれも「引数を受けて要素を返す関数」で、操作は引数のコールバックで入口に知らせる。 |

<!-- /table -->
