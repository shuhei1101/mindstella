# 全てのワークスペースの画面を、常駐サーバーの 1 つのポートで配る作りに切り替える

## 概要

利用者が、全てのワークスペースの画面（プレビュー）を、常駐サーバーの 1 つのポートで開けるようになる。

## 背景

[Issue #538](https://github.com/shuhei1101/mindstella/issues/538) の要望。
今は `serve.py` の `PreviewRegistry` がワークスペースごとに `127.0.0.1` の空きポート（または `config.yaml` の `preview.port`）で配信を起動し、画面の要求（`/api/records` など）はどのワークスペースの要求かを区別しない。
`check_host`・`check_origin` も配信ごとのポートと照らす。

[#531](https://github.com/shuhei1101/mindstella/pull/531)（起点 [#516](https://github.com/shuhei1101/mindstella/issues/516)）のスコープ外から切り出した。
親 [#481](https://github.com/shuhei1101/mindstella/issues/481) で「端末に 1 つの常駐サーバーで、全てのワークスペースの画面と MCP を配る」と決めており、この Issue は #481 の子として扱う。
今の画面を削除する [#371](https://github.com/shuhei1101/mindstella/issues/371) はこの Issue の後に並ぶため、今の画面の呼び出しもこの作業 PR で合わせる。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [サーバー](./サーバー.mark.md) | 配信・`check_host`・`check_origin` と、単一 UC・データ設計・インターフェース定義・モジュール構成の計画書 |
| [プレビュー](./プレビュー.mark.md) | React の画面と今の画面の呼び出しと、画面設計・部品設計・モジュール構成の計画書 |
| [反映作業](./反映作業/index.yaml) | 配信のフックから呼ぶ利用者のスクリプトの追従 |
