# ネットワークと全体の検索を React へ移行する

## 概要

ネットワークの画面（3D の描画・見た目の選択・起点のロック）と全体の検索のモーダルを React へ移行する。

## 背景

[#370](https://github.com/shuhei1101/mindstella/issues/370) の要望で、親 [#365](https://github.com/shuhei1101/mindstella/issues/365) を分割した子 5。
子 1（[#366](https://github.com/shuhei1101/mindstella/issues/366)・[#429](https://github.com/shuhei1101/mindstella/pull/429)）の React の土台と、子 2〜4（[#367](https://github.com/shuhei1101/mindstella/issues/367)・[#368](https://github.com/shuhei1101/mindstella/issues/368)・[#369](https://github.com/shuhei1101/mindstella/issues/369)）で移した画面の上に、今は今の画面（`/mindstella.html`）を開いているネットワークと全体の検索を移行する。
移行を終えるまでは今の画面を配信し続け、子 6（[#371](https://github.com/shuhei1101/mindstella/issues/371)）で切り替える。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [プレビュー](./プレビュー.md) | プレビューの計画書 |
