# PreToolUse のフック inject_session.py の出力に permissionDecision を付ける

## 概要

auto モードでも、PreToolUse のフックが入力を書き換えた mindstella のツールの呼び出しが拒否されないようにする。

## 背景

[Issue #479](https://github.com/shuhei1101/mindstella/issues/479) の不具合。
PreToolUse のフック `inject_session.py` は `updatedInput` だけを返却し、`permissionDecision` を返却していない。
Claude Code の auto モードでは、`updatedInput` を `permissionDecision` なしで返却すると、分類器が確認したのは Claude が記載した入力でフックが返却した入力ではないため、書き換えた呼び出しが拒否されうる（[公式の資料](https://code.claude.com/docs/en/hooks)）。
利用者は、フックを持つプラグインは必ず `permissionDecision` を付けると決めた（Issue の `## 決まったこと`）。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [サーバー](./サーバー.md) | サーバーの計画書 |
