# Git フック（lefthook）から lint・型検査を除外し、ビルドの出力の検査だけを残す

## 概要

commit の前の Git フック（lefthook）から lint と型検査を除外し、commit するビルドの出力がソースと合うかの検査（`spa-build`）だけを残す。

## 背景

[#470](https://github.com/shuhei1101/mindstella/issues/470) の要望。
AI Monitor の手順では planner が lint・テストを実行してログを PR ドキュメントに配置し、reviewer がログを確認するため、フックの lint・型検査はその検査と重なる。
フックは [#429](https://github.com/shuhei1101/mindstella/pull/429)（React 移行の土台）で入れた。
規約の側は [shuhei1101/knowledge#227](https://github.com/shuhei1101/knowledge/issues/227) で修正する。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.md) | プレビューの計画書 |
