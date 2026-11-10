# dev/ を廃止して文書を docs/ 1 つにまとめ、公開分を mdmark で描く Pages の Actions の配信に切り替える

## 概要

開発ドキュメント（`dev/`）と公開ドキュメント（`docs/`）を `docs/` 1 つにまとめ、公開分（`visibility: public`）だけを mdmark で描いて GitHub Actions で Pages へ配信する。
エージェントが、AI Monitor と同じく `docs/` だけを前提に文書を参照・記載できるようになる。

## 背景

[Issue #413](https://github.com/shuhei1101/mindstella/issues/413) の要望。
AI Monitor は [shuhei1101/ai-monitor#3307](https://github.com/shuhei1101/ai-monitor/pull/3307) で `dev/` を廃止し、マージの後の AI Monitor は `dev/` の置き場所を参照しない。
`dev/` が残る間は、設計書の検証・Markdown の生成（`python -m ai_monitor.design_docs`）が動かない。
後続の [#407](https://github.com/shuhei1101/mindstella/issues/407) の子のうち、公開ドキュメント・PR ドキュメント・モックの子が、この Issue を依存に持つ。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 移す先と修正する設定・参照の整理 |
| [反映作業](./反映作業/index.yaml) | Pages の配信元の切り替え |
