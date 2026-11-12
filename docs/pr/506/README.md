# develop に入っている作業 PR のスクリーンショットを削除する

## 概要

develop に入っている作業 PR のスクリーンショットの画像を、履歴を書き換えずに削除の commit で取り除き、リポジトリを軽くする。

## 背景

[Issue #498](https://github.com/shuhei1101/mindstella/issues/498) の要望。
作業 PR のスクリーンショットが squash マージで develop に入り、リポジトリが重くなっている。
これからのスクリーンショットは AI Monitor の手順変更（[shuhei1101/ai-monitor#3373](https://github.com/shuhei1101/ai-monitor/pull/3373)）で Git 管理外に置くため、既に入った画像だけを削除する（[確認ログ](https://github.com/shuhei1101/ai-monitor/pull/3373#discussion_r4536950116)）。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
