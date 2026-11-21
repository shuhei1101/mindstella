# 次の Sprint の 10 件の束（書き出しの取り直し・本文の ID のリンクと差分・トップバーの帯の削除と画面の小さい修正）

## 概要

利用者が、配る書き出しを CDN の一時的な失敗で止められずに使用でき、プレビューの本文のスレッドの ID・差分の表示中の ID をリンクとして使用でき、トップバー・図の拡大・案のカード・書体・ファビコンを修正した画面で使用できるようになる。

## 背景

[Issue #673](https://github.com/shuhei1101/mindstella/issues/673) の束。次の Sprint の未着手の 10 件を 1 つの作業 PR で対応する。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#672](https://github.com/shuhei1101/mindstella/issues/672) | 配る書き出しの `fetch_url`（`builder.py`）は GET を 1 回だけ送信し、jsDelivr の一時的な 403 でも `DownloadFailedError` になる。[PR #667](https://github.com/shuhei1101/mindstella/pull/667) の結合テストで `test_spa_open.py` の書き出しの 2 件が fail した |
| [#152](https://github.com/shuhei1101/mindstella/issues/152) | 図の拡大は「本文へ戻る」のボタンで閉じ、外側を押しても閉じない |
| [#154](https://github.com/shuhei1101/mindstella/issues/154) | 変更履歴の差分の表示中は、本文の用語・項目の ID がリンク・ツールチップにならないという報告 |
| [#161](https://github.com/shuhei1101/mindstella/issues/161) | 案のカードは記号を本文の左に等幅の文字で、採用・不採用を文字で出し、推奨の理由を一覧の下にまとめて出さない |
| [#184](https://github.com/shuhei1101/mindstella/issues/184) | 過去の差分を表示している間、トップバーの変更履歴のボタンの横に選んだ履歴のマーカーとタイトル（`DiffChip`）が出る |
| [#192](https://github.com/shuhei1101/mindstella/issues/192) | プレビューの HTML に `<link rel="icon">` が無く、タブが既定のアイコンになる |
| [#351](https://github.com/shuhei1101/mindstella/issues/351) | コピーのボタンの文言を、描いた後に `relabelParamCopy` で書き換えている。mdmark は設定 `labels.paramCopy` を持つようになった |
| [#426](https://github.com/shuhei1101/mindstella/issues/426) | 本文・スレッドの書き込みのスレッドの ID（`TH-150`）がリンクにならない |
| [#635](https://github.com/shuhei1101/mindstella/issues/635) | 入力中に記録が更新されるとトップバーの下に「更新があります」のバーが出て、下の領域を押し下げる |
| [#637](https://github.com/shuhei1101/mindstella/issues/637) | `detect_screen_issues` で `overused-font` が出る（文字のトークンが `"Inter"` から始まる） |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件 |
| [プレビュー](./プレビュー.mark.md) | プレビューの画面・部品・テストの計画書 |
| [サーバー](./サーバー.mark.md) | 配る書き出しの取得の計画書 |
| [プラグイン](./プラグイン.mark.md) | 記録のエージェントフローの計画書 |
