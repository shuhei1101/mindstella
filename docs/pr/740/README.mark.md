# 配信元の設定の exclude から "*.yml" を削除し、管理用の YAML の行の Markdown を配信する

## 概要

project-index が、配信元の設定 `dev-docs.yaml` の管理用の YAML（`docs/guide/files.yml`・`docs/_root/files.yml`）の行が指す Markdown を配信するようになる。

## 背景

[Issue #739](https://github.com/shuhei1101/mindstella/issues/739) の不具合。`files_guide`・`files_root` の行の `exclude` の `"*.yml"` が `paths` の `files.yml` 自身を除外し、`docs/guide/`・`docs/_root/` の Markdown が配信されない。AI Monitor の `update_dev_docs_section` がこれらのページを `served: false` にし、作業 PR の本文のリンクが GitHub のファイルの URL になる（実例は [PR #733](https://github.com/shuhei1101/mindstella/pull/733)）。

[shuhei1101/aituber#204](https://github.com/shuhei1101/aituber/issues/204) と同じ修正。AI Monitor 側の報告は [shuhei1101/ai-monitor#3865](https://github.com/shuhei1101/ai-monitor/issues/3865)。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理と変更箇所の由来 |
| [配信元の設定](./配信元の設定.mark.md) | 配信元の設定 `dev-docs.yaml` の計画書 |
