# 絞り込みのプリセットの保存・検索からの絞り込み・詳細の補足の見分けと目次・原文の差分の指定・反映の時間の非機能要件テストを追加する

## 概要

利用者が、画面の今の絞り込みを名前付きのプリセットとして保存し、全体の検索から絞り込みをオンにし、詳細で本文と補足の欄を見分けて本文の目次から見出しへ移れるようになる。あわせて、本文の「原文の差分」で重なるボタンと欄を出さないようにし、画面への反映の時間を確かめる非機能要件テストを追加する。

## 背景

[Issue #684](https://github.com/shuhei1101/mindstella/issues/684) の束。次の Sprint の未着手の 6 件を 1 つの作業 PR で対応する。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#362](https://github.com/shuhei1101/mindstella/issues/362) | [#360](https://github.com/shuhei1101/mindstella/issues/360)・[#361](https://github.com/shuhei1101/mindstella/issues/361) でプリセットのデータ・MCP の作成と、ドロワーでの一覧と適用は入ったが、利用者が画面から今の絞り込みを保存する操作と、配信のプリセットを書き込むエンドポイントが無い |
| [#668](https://github.com/shuhei1101/mindstella/issues/668) | [PR #667](https://github.com/shuhei1101/mindstella/pull/667) で「原文の差分」を mdmark の取り出し元で描くようにしたが、mdmark が出す「変更表示」のボタンとリビジョンの欄が変更履歴で選んだ時点と重なる。出さない指定は [mdmark#784](https://github.com/shuhei1101/mdmark/issues/784)（[mdmark PR #792](https://github.com/shuhei1101/mdmark/pull/792)）で mdmark の develop に入った |
| [#495](https://github.com/shuhei1101/mindstella/issues/495) | NFR-16『画面への反映の時間』の `test_file` が指す `tests/nfr/test_preview_reflect_time.py` が無い。非機能要件テストの層は [#494](https://github.com/shuhei1101/mindstella/issues/494)（[PR #682](https://github.com/shuhei1101/mindstella/pull/682)）で入った |
| [#143](https://github.com/shuhei1101/mindstella/issues/143) | 「すべての項目を検索」は項目の中身だけを探し、タグ・状態で絞るには別に絞り込みを開く必要がある（aituber の話し合いの送信 S-37） |
| [#159](https://github.com/shuhei1101/mindstella/issues/159) | 詳細のサイドバー・拡大表示で、本文の下の参照・関連・経緯がどれも同じ見出しの欄で続き、本文と補足の境が分からない（送信 S-78・S-95） |
| [#160](https://github.com/shuhei1101/mindstella/issues/160) | 長い資料の中で目的の節まで移りにくい。本文を描く mdmark の目次は今は切っている（送信 S-95） |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件 |
| [プレビュー](./プレビュー.mark.md) | プリセットの保存の操作・検索からの絞り込み・詳細の補足の見分けと目次・原文の差分の指定（#143・#159・#160・#362・#668）の計画書 |
| [サーバー](./サーバー.mark.md) | プリセットを書き込む配信のエンドポイントと非機能要件テスト（#362・#495）の計画書 |
