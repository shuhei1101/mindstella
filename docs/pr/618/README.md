# mdmark の記法を含む文書とワークスペースの資料の本文の拡張子を .mark.md へ移す

## 概要

MindStella のリポジトリの文書と、ワークスペースの記録の本文のうち、mdmark の記法で記載する Markdown の拡張子を `.mark.md` にし、mdmark の文書として扱われるようにする。

## 背景

[Issue #527](https://github.com/shuhei1101/mindstella/issues/527) の要望。[shuhei1101/mdmark#499](https://github.com/shuhei1101/mdmark/issues/499)（PR [shuhei1101/mdmark#541](https://github.com/shuhei1101/mdmark/pull/541)）で、mdmark の記法で記載する文書の拡張子が `.mark.md` になった。前提の mdmark のタグ（[shuhei1101/mdmark#548](https://github.com/shuhei1101/mdmark/issues/548)）は配布済み。

- `mdmark check` は、記法を含む純粋な `.md` に、拡張子を `.mark.md` へ変えるよう提案する（`plain_md_with_marks`）
- origin/develop の `.md` のうち記法（`<!-- table -->`・`<!-- html -->` など）を含むのは、`docs/guide/` の 7 ページ・`docs/design-policy.md`・`docs/mock/` の目次 22 件と、目次（`index.yaml`）から書き出した `README.md`・PR ドキュメント（`docs/pr/`）
- ワークスペースの記録の本文は `docs/{ID}.md` に配置し、プレビューは mdmark で描く
- AI Monitor でも同じ移行を [shuhei1101/ai-monitor#3427](https://github.com/shuhei1101/ai-monitor/issues/3427)（PR [shuhei1101/ai-monitor#3684](https://github.com/shuhei1101/ai-monitor/pull/3684)）で進めており、目次の `README.md` と PR ドキュメントのファイル名は AI Monitor の書き出しとテンプレートが決める

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [サーバー](./サーバー.md) | 本文のパス・点検・変更の検知・移し替えの計画書 |
| [プレビュー](./プレビュー.md) | 画面が本文を参照・書き出すパスの計画書 |
| [スキル](./スキル.md) | エージェントフローが指す本文のパスの計画書 |
