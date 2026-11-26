# 画面に記録の文字を表示する全ての場所で、項目の ID・スレッドの ID を自動でリンクにし、新規の部品でも抜けないようにする

## 概要

利用者が、プレビューの画面のどこに記載した項目の ID・スレッドの ID も、プレーンテキストのままリンクとして開けるようになる。
今後追加する部品・欄でも、リンクにならない場所が生まれないようにする。

## 背景

[Issue #700](https://github.com/shuhei1101/mindstella/issues/700) の要望。
これまで [#154](https://github.com/shuhei1101/mindstella/issues/154)・[#426](https://github.com/shuhei1101/mindstella/issues/426)・[#688](https://github.com/shuhei1101/mindstella/issues/688)（[PR #695](https://github.com/shuhei1101/mindstella/pull/695) でマージ済み）と、場所を 1 か所ずつ修正してきたため、修正した場所の外にリンクにならない場所が毎回残っている。
ID をリンクにする処理は `linkBody`（body-links）と `buttonizeItemIds`・`linkThreadIds`（post-links）の 2 つに分かれ、呼んだ部品（本文・値の欄・スレッドの書き込み）だけがリンクになる。
タイトル・一覧の行・検索の結果などを描く部品はどちらも呼ばず、新規の部品で呼び忘れを見つける決まりもテストも無い。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [プレビュー](./プレビュー.mark.md) | プレビューの計画書 |
