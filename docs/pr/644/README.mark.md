# 配信と配る書き出しを React の画面へ切り替え、今の画面と雛形と今の Storybook を削除する

## 概要

利用者がサーバーの配信と配る書き出しのどちらで開いても React の画面で記録を参照できるようにし、今のバニラ TS の画面・雛形・今の Storybook を削除する。

## 背景

[Issue #371](https://github.com/shuhei1101/mindstella/issues/371) の要望。React 移行（[#365](https://github.com/shuhei1101/mindstella/issues/365)）の分割の子 6 で、子 2〜5（[#367](https://github.com/shuhei1101/mindstella/issues/367)・[#369](https://github.com/shuhei1101/mindstella/issues/369)・[#370](https://github.com/shuhei1101/mindstella/issues/370) ほか）で全ての画面を React で再現した後に、配信を React の画面へ切り替える。

- 今は常駐サーバーが今の画面（`/w/{workspace}/mindstella.html`）と React の画面（`/w/{workspace}/spa/`）を並べて配っており、配る書き出し（`export`）は今の画面の雛形から作っている
- 今の画面を残す間は、画面の修正（[#548](https://github.com/shuhei1101/mindstella/issues/548)・[#592](https://github.com/shuhei1101/mindstella/issues/592) ほか）が今の画面の分も必要になる
- E2E は 0.x の間は合わせない（計画の行の概要）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理と未確定の論点 |
| [プレビュー](./プレビュー.mark.md) | 今の画面・雛形・今の Storybook の削除と、配る書き出しの React の画面の計画書 |
| [サーバー](./サーバー.mark.md) | 配信の切り替えと、配る書き出しを React のビルドから作る計画書 |
