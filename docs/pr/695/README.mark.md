# 詳細パネル・スレッド・一覧の表示と操作を改善し、lint の除外を追加する（束 #694）

## 概要

利用者が、詳細パネルで開いた順と元の画面の並びの両方で項目をたどり、値の欄の項目の ID から資料を開き、表とカードを作成日時・更新日時で並べ替え、スレッドを開いたら最新の書き込みから読めるようになる。
あわせて、長い値でもラベルとボタンの文字が折り返されないようにし、lint の全件実行が worktree の状態に左右されないようにする。

## 背景

[Issue #694](https://github.com/shuhei1101/mindstella/issues/694) の束。次の Sprint の未着手の 8 件を 1 つの作業 PR で対応する。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#690](https://github.com/shuhei1101/mindstella/issues/690) | レビュー中の書き込みの行の種類のラベル（返信・新規スレッド）に `shrink-0`・`whitespace-nowrap` が無く、タイトルが長い行と狭い幅でラベルが 1 文字ずつ折り返される（利用者の報告。TH-1617） |
| [#691](https://github.com/shuhei1101/mindstella/issues/691) | `eslint.config.js` の `ignores` に `.venv/**`・`storybook-static/**` が無く、worktree の直下にあると lint の全件実行が失敗する（作業 PR [#685](https://github.com/shuhei1101/mindstella/pull/685) の lint で見つけた） |
| [#148](https://github.com/shuhei1101/mindstella/issues/148) | 詳細パネルの戻る・進むは、一覧・ボードから別の項目を開くと履歴を作り直すため使えず、タブの切り替えは履歴に追加する（送信 S-43・S-49）。スクロールの位置の復元は [#452](https://github.com/shuhei1101/mindstella/issues/452) が受け持つ |
| [#688](https://github.com/shuhei1101/mindstella/issues/688) | 詳細パネルの値の欄（検討事項の案・回答・理由・概要）は `linkBody` を通さず、項目の ID が文字のまま出る（TH-1613・A-308） |
| [#186](https://github.com/shuhei1101/mindstella/issues/186) | 項目は `created`・`updated` を持つが、表の列・カードに出ず、それで並べ替えもできない（送信 S-144） |
| [#364](https://github.com/shuhei1101/mindstella/issues/364) | 詳細パネルで項目を続けて見るには、毎回一覧・ボードに戻って次の項目を押す（会話ログ L-12） |
| [#372](https://github.com/shuhei1101/mindstella/issues/372) | スレッドの見出しのタイトルが全文で折り返され、長いと書き込みの並びと返信の入力欄を圧迫して押せなくなる（TH-137・TH-1390） |
| [#374](https://github.com/shuhei1101/mindstella/issues/374) | スレッドを開くと先頭から表示され、送信済みの長い書き込みは折りたたまれない（T-1・TH-1390） |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件 |
| [プレビュー](./プレビュー.mark.md) | 詳細パネル・スレッド・一覧の表示と操作と、lint の除外（#148・#186・#364・#372・#374・#688・#690・#691）の計画書 |
