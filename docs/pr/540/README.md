# 記録の検索と書き込みを project-index へ移し、commit とスレッドを MindStella の MCP に残す

## 概要

どのセッションも、ワークスペースの記録（検討事項・資料などと資料の本文）を project-index の `search_docs`・`write_docs`・`delete_docs` で検索・書き込みできるようになる。
MindStella のセッションは、スレッドと書き換えのまとまり（commit）と ID の採番を MindStella の MCP で行い、ほかのセッションが書き込んだ変更も履歴に残る。

## 背景

[Issue #517](https://github.com/shuhei1101/mindstella/issues/517) の要望で、MindStella を project-index と同じ作りに作り直す束 [Issue #481](https://github.com/shuhei1101/mindstella/issues/481) の子のうち 2 つ目（資料 A-107 の「シナリオを作る順」の No 2）。

- 今は MindStella の MCP が記録の検索（`find`・`show`・`tags`・`attrs`・`impact`）と書き込み（`add`・`update`・`remove`・`batch`）を持ち、project-index の検索・書き込み・検査と同じ処理を 2 重に持っている
- 変更の履歴（項目の `history`・`changes.yaml` の通し番号とまだまとめていない変更）は、MindStella の MCP と画面の書き込みだけが記録する。project-index で書き込んだ変更は履歴に残らない
- [PR #531](https://github.com/shuhei1101/mindstella/pull/531)（#516）は、ワークスペースを project-index の配信元の行として登録するが、行の `config`（`.mindstella/dev-docs.yaml`）はまだ作らない。配信元の行は配信されないまま登録される（インターフェース定義『ワークスペースの作成』の `notes`）
- 記録の読み取りを project-index へ移す [#345](https://github.com/shuhei1101/mindstella/issues/345) と、ワークスペースを配信する設定を配置する [#344](https://github.com/shuhei1101/mindstella/issues/344) は、この Issue に含めて close された。#345 に引き渡されていた [PR #390](https://github.com/shuhei1101/mindstella/pull/390) の材料は、[引き継ぎのコメント](https://github.com/shuhei1101/mindstella/issues/517#issuecomment-6880106726) でこの Issue へ移された

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と、#345 から引き継いだ材料の扱い |
| [サーバー](./サーバー.md) | MindStella の MCP のツールの移し替え・変更の検知・ID の採番・配信元の設定の計画書 |
| [プレビュー](./プレビュー.md) | 外部の変更のまとまりと、重なった ID の通知の画面の計画書 |
| [スキル](./スキル.md) | 既存のワークスペースの移し替えの計画書 |
