# コメント・返信の入力にマイクのボタンを追加し、音声を文字起こしのインターフェース経由で voice-paste に文字起こしさせる

## 概要

利用者が、プレビューのコメント・返信の入力のマイクのボタンで話した内容を、文字起こしの結果としてその書き込みのまま Claude Code へ送信するか、入力欄へ挿入できるようになる。

## 背景

[Issue #402](https://github.com/shuhei1101/mindstella/issues/402) の要望。利用者は音声入力で操作しているが、プレビューのコメント・返信の入力はキーボードの入力だけを受ける。
同じ端末で動く voice-paste は、音声を受けて文字起こしする API（`POST /web/transcriptions`・`GET /web/transcriptions/{job_id}`）を持つ。
音声の経路は検討事項 D-7 で案 A（ブラウザ → MindStella のサーバー → 文字起こしのインターフェース → voice-paste）に決まり、前提の voice-paste 側の変更は [shuhei1101/voice-paste#256](https://github.com/shuhei1101/voice-paste/issues/256) で入っている。
マイクのボタンは [#399](https://github.com/shuhei1101/mindstella/issues/399)（[#473](https://github.com/shuhei1101/mindstella/pull/473)）で入力欄の右に置いたアイコンのボタンの並びに加える。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [プレビュー](./プレビュー.md) | コメント・返信の入力のマイクのボタンと録音・設定の画面の計画書 |
| [サーバー](./サーバー.md) | 音声を受けるエンドポイントと文字起こしのインターフェース・voice-paste の実装・設定の計画書 |
