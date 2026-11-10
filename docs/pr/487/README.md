# AI Monitor v0.3.0 の配布物へ追従する

## 概要

AI Monitor の配布物（サイトのレイアウト・配信設定・テンプレート・規約・判定と観点・ルール索引）を v0.3.0 に合わせ、`ai-monitor-version.ini` を `v0.3.0` にする。

## 背景

[Issue #375](https://github.com/shuhei1101/mindstella/issues/375) の要望。AI Monitor v0.3.0 のタグで配布元が起票した追従 Issue で、origin/develop の `ai-monitor-version.ini` は `v0.2.0` のまま。
後続の追従 [#408](https://github.com/shuhei1101/mindstella/issues/408)・[#413](https://github.com/shuhei1101/mindstella/issues/413) が、この Issue を依存に持つ。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 分類ごとの要望の整理と変更箇所の由来 |
| [反映作業](./反映作業/index.yaml) | プラグインの取り直しと設定の見直し |

## テスト結果

コードを変えないため、規約『V字モデル』の対応表で関係する単体・結合テストは無い。

| 確認 | 結果 |
| --- | --- |
| 設計書の検証（AI Monitor v0.3.0 の `ai_monitor.design_docs validate`） | 設計書は全て合格。誤りは `docs/pr/487/反映作業/index.yaml` を目次として扱う 3 件だけ（スコープ外 #413） |
| `docs/_config.yml` の YAML の解析 | 解析できる |
| Jekyll のビルド | この端末に Jekyll が無いため未実行。マージ後の GitHub Pages のビルドで確認する |
