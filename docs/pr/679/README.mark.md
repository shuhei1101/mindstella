# ペインの無い MindStella のセッションを落ちたと判定し、書き込みのボタンを反映まで押せなくする

## 概要

利用者が、ほかの MindStella のセッションが動いている間も落ちた MindStella のセッションを落ちたと知ることができ、プレビューの書き込みのボタンを何度押しても押した回数だけ反映されずに使用できるようになる。

## 背景

[Issue #678](https://github.com/shuhei1101/mindstella/issues/678) の束。現在の Sprint の未着手の 2 件を 1 つの作業 PR で対応する。[#606](https://github.com/shuhei1101/mindstella/issues/606) はユーザーの指示（[#1 のコメント](https://github.com/shuhei1101/mindstella/issues/1#issuecomment-7079438765)）で最優先にした行。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#606](https://github.com/shuhei1101/mindstella/issues/606) | `sessions.py` の `_dead_reason` は `tmux display-message` の終了コードだけでペインの有無を判定する。tmux 3.4 は同じ tmux のサーバーにほかのセッションがあると、無いペインを指しても空の出力で 0 を返すため、落ちた MindStella のセッションを生きていると判定する。[PR #605](https://github.com/shuhei1101/mindstella/pull/605) で見つけ、IF-605-1・SC-605-1 の正常系の A を `stopped` にして確かめている |
| [#677](https://github.com/shuhei1101/mindstella/issues/677) | React への置き換えの後、送信・更新のボタン（レビューに送信する 等）を、押してから記録に反映されるまでの間も押せ、押した回数だけまとめて反映される（利用者のコメント TH-1576） |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件 |
| [サーバー](./サーバー.mark.md) | MindStella のセッションの落ちたかの判定の計画書 |
| [プレビュー](./プレビュー.mark.md) | 書き込みのボタンの待つ間の状態の計画書 |
