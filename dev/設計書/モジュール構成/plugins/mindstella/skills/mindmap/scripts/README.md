# scripts

scripts の設計書

## 目次

<!-- table: data -->

| ページ | 概要 |
| --- | --- |
| [backup.py](./backup.py.yaml) | サーバー / 移行 / backup.py |
| [builder.py](./builder.py.yaml) | ワークスペースの記録を 1 つの JSON にまとめ、プレビューの雛形に CSS と JavaScript を差し込む。配信はその雛形と記録をその場で返し、配る書き出しは同じ雛形に jsDelivr から取った描画のライブラリとライセンスの表示と記録を入れて書き出す。読み書きと検証と、依存と影響・ゴール判定（画面に出す値の計算）に依存する。 |
| [check_env.py](./check_env.py.yaml) | サーバー / 起動 / check_env.py |
| [checker.py](./checker.py.yaml) | ワークスペースのスキーマ違反・ID の重複・参照切れ・本文のずれ・設定に無いフェーズを問題として洗い出す。読み書きと検証だけに依存し、ファイルを書かない。 |
| [claude_input.py](./claude_input.py.yaml) | ツールの呼び出しが運んだセッションの値を読み、ワークスペースごとに宛先を持つ。まとめて送った後に、そのワークスペースを指して最後にツールを呼んだセッションが生きているかを確かめてからペインへ 1 行の文字列を貼り、Claude Code の会話の記録に入ったかを確かめる。tmux と ps を子プロセスで呼び、会話の記録（jsonl）を読む。 |
| [commands.py](./commands.py.yaml) | サーバー / ゴール判定 / commands.py |
| [comments.py](./comments.py.yaml) | レビュー中のコメント（`comments.yaml`）と書きかけ（`drafts.yaml`）を読み書きし、チェックしたコメントをスレッドへ移す。文字起こしの結果の書き込み 1 件は、レビュー中に溜めずにすぐスレッドへ足す。箇所・スレッド・読み書きと検証に依存し、鍵は呼ぶ側（配信）が取る。 |
| [edits.py](./edits.py.yaml) | プレビューで利用者が溜めた保存待ちの編集（`edits.yaml`）を読み書きし、まとめて保存するときに項目と設定へ当てる。読み書きと検証・入口（項目の追加と更新）・設定の更新・変更履歴に依存し、鍵は呼ぶ側（配信）が取る。例外はモジュール構成『読み書きと検証』の `EditInvalidError`・`EditNotFoundError`・`EditConflictError`・`EditsBlockedError`。単体テストは `tests/unit/scripts/test_edits.py` に置く。 |
| [ensure_server.py](./ensure_server.py.yaml) | サーバー / 起動 / ensure_server.py |
| [errors.py](./errors.py.yaml) | サーバー / 読み書きと検証 / errors.py |
| [graph.py](./graph.py.yaml) | サーバー / ゴール判定 / graph.py |
| [history.py](./history.py.yaml) | 項目の変更履歴の 1 回分を作って積み、書き換えのまとまり（`changes.yaml`）・AI が最後に読んだ時点・前回開いた日時（`.mindstella-opened`）を読み書きし、読んだ時点からの変更を組み立てる。『読み書きと検証』にだけ依存し、書き込みは `save_change`・`save_batch` に任せる。 |
| [html_body.py](./html_body.py.yaml) | 資料の HTML の本文の開きタグに原文の行の印を足す処理と、原文の行の範囲の描いた文を取り出す処理。どちらも Python の標準ライブラリ `html.parser.HTMLParser` で原文を読む。 |
| [inject_session.py](./inject_session.py.yaml) | Claude Code の `PreToolUse` のフックが呼ぶスクリプト。mindstella のツールを呼んだセッションの作業フォルダ・tmux のペイン・設定のフォルダ・Claude Code のプロセスを、ツールの入力の `session` に入れて返す。 |
| [kinds.py](./kinds.py.yaml) | サーバー / 読み書きと検証 / kinds.py |
| [launch.py](./launch.py.yaml) | サーバー / 起動 / launch.py |
| [locations.py](./locations.py.yaml) | コメントが指す箇所（本文の行の範囲か項目の値のキーと、選んだ文）の形を確かめ、今の項目に合うかを確かめる。読み書きと検証だけに依存し、書き込まない。 |
| [migration_ops.py](./migration_ops.py.yaml) | サーバー / 移行 / migration_ops.py |
| [migrator.py](./migrator.py.yaml) | サーバー / 移行 / migrator.py |
| [query.py](./query.py.yaml) | 条件で項目を探してページに分け、返す量を選んで JSON か Markdown にし、1 件の中身と参照元、使っている属性名とタグを出す。読み書きと検証・タグの表記だけに依存し、ファイルを書かない。 |
| [readme.py](./readme.py.yaml) | ワークスペースの直下の `README.md`（起動・接続のコマンド、スキルの呼び方、プレビューの URL の一覧）を組み立てて書く。`init`・`readme`・`preview_url` の 3 つのツールが同じ関数で書く。 |
| [reset_unread.py](./reset_unread.py.yaml) | Claude Code の `SessionStart` のフックが呼ぶスクリプト。作業フォルダとその直下のワークスペースを探し、ロックを取ってスレッドの書き込みを未読に戻す。スレッドと読み書きと検証に依存する。単体テストは `tests/unit/scripts/test_reset_unread.py` に置く。 |
| [serve.py](./serve.py.yaml) | ワークスペースごとに `127.0.0.1` の空きポートでプレビューを配る。画面・記録・スレッド・書き換えの知らせを返し、レビュー中のコメント・書きかけ・まとめて送る・スレッドの状態の書き換え・スレッドの利用者の既読・設定の既定の書き換え・設定の再読み込み・書き込みをすぐ送るを受け付ける。まとめて送った後とすぐ送った後は Claude Code へ入力する。文字起こしの可否を返し、受けた音声を文字起こしのインターフェースへ渡す。ビルド（雛形と記録）とコメントとスレッドと Claude Code への入力と設定の更新と文字起こしと読み書きと検証に依存する。 |
| [server.py](./server.py.yaml) | サーバー / 入口 / server.py |
| [settings_update.py](./settings_update.py.yaml) | `update_settings` の引数を確かめ、設定のキーを置き換え、フェーズ・対象・カテゴリーの対応で項目の `phase`・`target`・`category` と `goal.phase`・カテゴリーの `target` を付け替えて、設定と種類ごとの YAML をまとめて書く。読み書きと検証だけに依存する。 |
| [store.py](./store.py.yaml) | サーバー / 読み書きと検証 / store.py |
| [tag_text.py](./tag_text.py.yaml) | タグを NFKC と小文字にそろえた表記にし、使われているタグのうち字面の近いものを並べる。検索から使う。 |
| [threads.py](./threads.py.yaml) | スレッド（`threads.yaml`）を読み書きする。まとめて送られた利用者の書き込みを足し、AI の一覧・既読・返信・状態と要約の書き換え・取り込み済みを担い、画面へ返す形を作る。読み書きと検証だけに依存し、鍵は呼ぶ側（入口・コメント・配信・未読へ戻す）が取る。単体テストは `tests/unit/scripts/test_threads.py` に置く。 |
| [transcriber.py](./transcriber.py.yaml) | 配信が音声を文字に起こすときに依存する文字起こしのインターフェースと、使えるかの確かめ・失敗の種類を持つ。サービスごとの呼び方は実装のモジュール、環境変数で実装を選ぶ処理は引き当てのモジュールが持ち、配信はこのモジュールだけを import する。どのモジュールも import しない。 |
| [transcriber_registry.py](./transcriber_registry.py.yaml) | 環境変数で文字起こしの実装を選び、URL を確かめて作る。常駐サーバーの起動の入口だけが import し、文字起こし（抽象）と実装のモジュールに依存する。実装は抽象だけに依存するので、import は一方向になる（入口 → 引き当て → 実装 → 抽象）。 |
| [versions.py](./versions.py.yaml) | サーバー / 移行 / versions.py |
| [voice_paste.py](./voice_paste.py.yaml) | 文字起こしのインターフェースの voice-paste の実装。プリセットの一覧を読み、音声を `multipart/form-data` で依頼し、ジョブの状態を取りに行って終わるまで待つ。HTTP は標準ライブラリの `urllib.request` で送り、文字起こしだけに依存する。 |

<!-- /table -->
