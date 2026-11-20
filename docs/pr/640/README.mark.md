# 文書と UI 文言の単語を、knowledge の対応表と規約『文章の書き方』に合わせて修正する

## 概要

文書（docs・エージェントフロー）と UI 文言（React の画面と今の画面）の文章でない所の単語を、knowledge の対応表（`docs/word-list/word-list-ai-slop.yaml`）と規約『文章の書き方』に合わせて修正し、文章の冗長表現と話し言葉を修正する。

## 背景

[Issue #337](https://github.com/shuhei1101/mindstella/issues/337) の要望。
UI ラベル・見出し・表の列名・項目名に「送る」「足す」「版」「節」「印」「口」「形」「段」「題」などの和語・一字の単語が多く、読み手が元の用語を推測しないと意味を特定できない。
エージェントが毎回参照する文書の単語が出力に寄るため、規約の追加だけでなく参照させている文書も修正する。

修正する単語の正は、[shuhei1101/knowledge#135](https://github.com/shuhei1101/knowledge/issues/135) で YAML に移行した対応表と、それを埋め込む規約『文章の書き方』（[連絡](https://github.com/shuhei1101/mindstella/issues/337#issuecomment-6604992099)）。

受付の後に、[#413](https://github.com/shuhei1101/mindstella/issues/413) で `dev/` は `docs/` にまとまり、[#518](https://github.com/shuhei1101/mindstella/issues/518) で session のスキルは `plugins/mindstella/agent-flows/` へ移行した。React の画面 `frontend/` も加わった。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [プレビュー](./プレビュー.mark.md) | 画面の UI 文言と、画面設計・部品設計・モックの計画書 |
| [サーバー](./サーバー.mark.md) | サーバーが返却するメッセージと、インターフェース定義・モジュール構成の計画書 |
| [スキル](./スキル.mark.md) | エージェントフロー・プロンプトの計画書 |
