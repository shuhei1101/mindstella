# 音声入力中の表示とつながらない表示が並んでも、トップバーを画面の幅に収める

## 概要

利用者が、今の画面で録音中にサーバーとの接続が切れても、どの幅でもトップバーを横にスクロールせずに操作できるようになる。

## 背景

[Issue #560](https://github.com/shuhei1101/mindstella/issues/560) の不具合。

- 今の画面のトップバーで、音声入力中の表示とサーバーにつながらない表示が同時に出ると、幅 901px（`scrollWidth 921 > clientWidth 901`）と幅 1441px（`scrollWidth 1510 > clientWidth 1441`）でトップバーが画面の幅を超える
- 音声入力中の表示は [#510](https://github.com/shuhei1101/mindstella/issues/510) の作業 PR [#529](https://github.com/shuhei1101/mindstella/pull/529) で入り、まだ release していない

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.md) | 今の画面のトップバーの計画書 |
