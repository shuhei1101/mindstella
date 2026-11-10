# dev/ を廃止して文書を docs/ 1 つにまとめる

## 概要

開発ドキュメント（`dev/`）と公開ドキュメント（`docs/`）を `docs/` 1 つにまとめ、Pages には公開分（`visibility: public`）だけを出す。
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
| [サーバー](./サーバー.md) | README の書き出しの公開ドキュメントのリンクの計画書 |
| [確認ログ](./確認ログ.yaml) | ユーザーへの確認事項の決着 |

## テスト結果

### ドキュメント修正

文書の移動と参照の書き換えだけで、コードを変えていないため、規約『V字モデル』の対応表で関係する単体・結合テストは無い。

| 確認 | 結果 | 補足 |
| --- | --- | --- |
| v0.4.0 の変換（AI Monitor `f135cff63`） | ✅ | `テスト結果/20261111045636_300ccd52_v0.4.0の変換.log`<br>1 回目は `container` の無い関数 17 件と、テストファイルの振り分け先が決まらない 58 件で拒否された。関数に物理ファイルを書き（`98602505`）、テストファイルは docstring の 1 行目が指す物理ファイルを渡して流した |
| 設計書の検証・目次の書き出し（AI Monitor develop `af7258c2d`） | ✅ | `テスト結果/20261111045458_6df6cb46_設計書の検証.log`<br>`validate`・`publish --check` とも誤り 0 件 |
