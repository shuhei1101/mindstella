# MindStella のセッションが project-index で Git 管理外のワークスペースの記録を作成・更新・参照できるようにする

## 概要

MindStella のセッションが、Git 管理外のワークスペースの記録（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）を project-index で作成・更新・参照できるようにする。

## 背景

[Issue #583](https://github.com/shuhei1101/mindstella/issues/583) の不具合（利用者の指定で超最優先）。
v0.13.0 で記録の読み書きを project-index の MCP に移した後、`write_docs` の作成・更新が検査に通らず、話し合いを記録できない。
原因は、project-index が Git 管理外の配信元へ追加する `created`・`updated` を MindStella のスキーマが許可しないこと、v0.14.0 の移し替えがスキーマの複製を再配置しないこと、本文のファイルを持たない項目を project-index が配信から除くことの 3 件。
v0.13.0・v0.14.0 は未リリースで、master には入っていない。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と未確定の論点 |
| [サーバー](./サーバー.md) | サーバーの計画書 |
