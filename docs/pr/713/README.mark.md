# 現在の Sprint の 4 件の束（コメントの一覧のパネルの幅の区切り・手番を返す前の強制・test_stream の停止・画面の横のはみ出し）

## 概要

利用者がコメントの一覧のパネルの幅を詳細パネルと同じくドラッグとキーで変えられ、資料とコメントのパネルが表や長い文字で横にはみ出さなくなる。
あわせて、MindStella のセッションが進められる工程や未着手・進行中のタスクを残したまま手番を返せなくなり、単体テストの全件実行が `test_stream` で止まらなくなる。

## 背景

[Issue #712](https://github.com/shuhei1101/mindstella/issues/712) の束。現在の Sprint の未着手の 4 件を 1 つの作業 PR で対応する。

| Issue | 背景 |
| --- | --- |
| [#357](https://github.com/shuhei1101/mindstella/issues/357) | 詳細パネルは [#340](https://github.com/shuhei1101/mindstella/issues/340) でドラッグで幅を変えられるようになったが、コメントの一覧のパネルは幅が固定のまま（利用者の依頼「コメント欄もスプリッターで横幅を変えれるようにしたい」）。利用者の指示で最優先 |
| [#711](https://github.com/shuhei1101/mindstella/issues/711) | エージェントフローに工程「進め方の続きを進める」と「未着手 のまま残さない」の決まりがあるが、MindStella のセッションが守らずに手番を返した（動画作成のワークスペースの TH-104・TH-105） |
| [#704](https://github.com/shuhei1101/mindstella/issues/704) | 作業 PR [#703](https://github.com/shuhei1101/mindstella/pull/703) の単体テストの全件実行で、`test_serve.py::test_stream` が `changed` を受け取らないまま止まり、全件実行が 62% で止まった |
| [#706](https://github.com/shuhei1101/mindstella/issues/706) | 表が画面の幅を超えると資料のページの全体が横スクロールになり、コメントのパネルのレビュー中の書き込みも横にスクロールし、「新規スレッド」のマーカーが 1 文字ずつ折り返す（TH-64・TH-66）。横スクロールの不具合は [#585](https://github.com/shuhei1101/mindstella/issues/585)・[#619](https://github.com/shuhei1101/mindstella/issues/619)・[#631](https://github.com/shuhei1101/mindstella/issues/631) で繰り返し修正してきた |

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理と子 Issue ごとの終了の条件・変更箇所の由来 |
| [プレビュー](./プレビュー.mark.md) | コメントの一覧のパネルの幅の区切りと、画面の横のはみ出しの計画書 |
| [サーバー](./サーバー.mark.md) | 手番を返す `commit` の拒否と、`test_stream` の停止の計画書 |
| [スキル](./スキル.mark.md) | 手番を返す前の確認のエージェントフローと注入文の計画書 |
