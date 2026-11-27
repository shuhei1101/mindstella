# パネルの幅の上限を画面の 2/3 にし、全画面のモーダル・コメントの件数のバッジ・ボタンの中の ID・外部の URL・mdmark の機能・本文の間・テストの fail を修正する

## 概要

利用者が、コメントのパネルと詳細パネルを互いの幅に制限されずに画面の 2/3 まで広げ、資料の全画面表示を画面の 9/10 ほどの大きさで参照できるようになる。
利用者が、詳細パネルでコメントの件数をバッジで把握し、外部の URL を新規タブで開き、プレビューの本文で mdmark のコードブロックの機能を使用できるようになる。
スレッドの行の中の ID のツールチップ・本文の区切りの中のブロックの間・表示の設定のパネルの余白・mdmark の表の列の幅のつまみの a11y の検出と、結合テスト 2 件の fail を修正する。

## 背景

束の親 [Issue #730](https://github.com/shuhei1101/mindstella/issues/730) の子 11 件をまとめて対応する。[#725](https://github.com/shuhei1101/mindstella/issues/725) はユーザーの指示で最優先。

<!-- table: {"kind": "data"} -->

| Issue | 困っていること |
| --- | --- |
| [#725](https://github.com/shuhei1101/mindstella/issues/725) | [#713](https://github.com/shuhei1101/mindstella/pull/713) でコメントのパネルの幅を変えられるようになったが、2 つのパネルの上限が本文の幅 400px と相手のパネルの幅を引いて決まり、片方を広げるともう片方を広げられない |
| [#728](https://github.com/shuhei1101/mindstella/issues/728) | 資料の全画面表示のモーダルの横幅が、全画面にしないときとほとんど変わらない |
| [#724](https://github.com/shuhei1101/mindstella/issues/724) | 詳細パネルの「コメント」のタブとヘッダーのコメントのボタンが、コメントの件数を出さない |
| [#726](https://github.com/shuhei1101/mindstella/issues/726) | コメントのパネルのスレッドの行（ボタン）の中の ID にツールチップが出て、ボタンと重なる |
| [#708](https://github.com/shuhei1101/mindstella/issues/708) | 記録・スレッドに記載された外部の URL を押すと今のタブで開き、MindStella の画面から離れる |
| [#710](https://github.com/shuhei1101/mindstella/issues/710) | プレビューは MindStella の画面と重ならない mdmark の機能までオフにしており、言語 `markdown` のコードブロックの `Raw` の切り替えとインデントの縦線が出ない |
| [#729](https://github.com/shuhei1101/mindstella/issues/729) | 見出しごとに包む `div.md-section-body` の中のブロック同士に mdmark の間が届かず 0px になる（依頼元 [shuhei1101/mdmark#825](https://github.com/shuhei1101/mdmark/issues/825)） |
| [#715](https://github.com/shuhei1101/mindstella/issues/715) | 表示の設定のパネル（幅 390px）で Impeccable の `body-text-viewport-edge` が出る |
| [#714](https://github.com/shuhei1101/mindstella/issues/714) | mdmark が描く表の列の幅のつまみで axe の `aria-valid-attr-value`（critical）が出る |
| [#716](https://github.com/shuhei1101/mindstella/issues/716) | 結合テスト `test_diff_source` が、[#668](https://github.com/shuhei1101/mindstella/issues/668) の `diffControls: false` の設計に追従しておらず fail する |
| [#717](https://github.com/shuhei1101/mindstella/issues/717) | 結合テスト `test_normal_when_records_changed_while_typing` が、表のタイトルの読み上げ用の hidden の要素を待って fail する |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.mark.md) | パネルの幅・全画面のモーダル・コメントの件数のバッジ・記録の文字・本文の描画・表示の設定のパネル・結合テストの計画書 |
