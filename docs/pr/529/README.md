# 音声入力の確定でレビュー中に追加する既定・録音中の移動と戻り・録音中の画面の消灯の抑止

## 概要

利用者が、音声入力の確定だけでレビュー中にコメントを追加でき、録音中もほかの資料を開いてヘッダーから録音中の入力欄へ戻れ、録音中に端末の画面が暗くならずに話し続けられるようになる。

## 背景

束の [Issue #528](https://github.com/shuhei1101/mindstella/issues/528) の要望で、子は次の 3 つ。

- [Issue #509](https://github.com/shuhei1101/mindstella/issues/509): 設定「文字起こし後の挙動」の既定が「入力欄へ挿入する」で、利用者は確定の後に毎回「レビューに追加」を押している。[PR #500](https://github.com/shuhei1101/mindstella/pull/500) が [Issue #499](https://github.com/shuhei1101/mindstella/issues/499)（確認なしの送信）を直すために既定を `send` から `insert` へ変えた
- [Issue #510](https://github.com/shuhei1101/mindstella/issues/510): 録音は入力欄ごとに持ち、ほかの項目やスレッドへ移ると録音を捨てる。利用者は資料を見ながら話したい。同時に 2 つの録音を始められないようにする要望（[Issue #511](https://github.com/shuhei1101/mindstella/issues/511)）を統合した
- [Issue #513](https://github.com/shuhei1101/mindstella/issues/513): 録音中に端末の画面が暗くなる。録音はプレビューの画面の `MediaRecorder` が行い、voice-paste の常駐アプリの消灯の抑止は効かないため、PC を含む全端末が対象（[task-planner の判断](https://github.com/shuhei1101/mindstella/issues/513#issuecomment-6843246760)）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.md) | 音声入力の録音・確定・トップバーの録音中の表示・設定の画面の計画書 |
| [サーバー](./サーバー.md) | 文字起こし後の挙動の値と既定の計画書 |
