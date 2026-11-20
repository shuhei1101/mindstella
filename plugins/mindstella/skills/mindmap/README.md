# mindstella

話し合いを記録しながら、要件・調査・資料作りで決めたことを形にしていく Claude Code のスキル。

## はじめに

Claude Code と話し合いながら、検討事項・そこから派生する質問・調査を、ワークスペース（YAML と Markdown のフォルダ）に記録する。
抽象と具体を行き来する発言をそのまま話しても、記録に残り、再開するときは前回の続きから進められる。

## コアコンセプト

- 記録は種類（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）ごとに分け、話題はタグで表す。細かいものは派生・依存・関連で表す
- 何をどの順に話し合うかは、導入する側の進め方の文書が持つ。起動のコマンドの `--flow` で渡す
- MindStella のセッションは、プラグインが同梱するエージェントフロー（起動と再開・コメントの取り込み・記録の使い分け）に従って記録を進める
- ワークスペースへの書き込みは、全て MCP のツールを通す。書き込む前にスキーマと突き合わせ、合わなければ何も書き換えない
- MCP のツールは、1 つの常駐サーバー（`127.0.0.1:8784`。`MINDSTELLA_PORT` で変えられる）がプラグインの `.mcp.json` で全ての Claude Code に載せる。常駐サーバーがプレビューも配り、項目や選んだ箇所へのコメントをレビュー中に溜めて、コメントの一覧から選んで送信できる

詳しくは [話し合いの進め方](https://shuhei1101.github.io/mindstella/guide/コアコンセプト-話し合いの進め方.html) を読む。

## エージェントフロー

| ID | 名前 | 進める契機 |
| --- | --- | --- |
| `mindstella/startup` | [起動と再開](../../agent-flows/startup.yaml) | MindStella のセッションを起動したとき、`/clear` の後、圧縮の後 |
| `mindstella/on-comment` | [コメントの取り込み](../../agent-flows/on-comment.yaml) | プレビューから送信したコメントが入力されたとき |
| `mindstella/record` | [記録の使い分け](../../agent-flows/record.yaml) | 利用者の発言・コメントを記録するとき |

エージェントフローは project-index の配信元 `mindstella-agent-flows` として配り、`search_docs` で ID を指して参照する。

## 依存とインストール

Claude Code 2.1.287 以上と、Python 3.12 以上（`venv` を含む）と、tmux と、systemd --user が要る。
マーケットプレイスを登録して、プラグインをインストールする。

```bash
claude plugin marketplace add shuhei1101/mindstella
claude plugin install mindstella@mindstella
```

起動中の Claude Code では `/reload-plugins` を実行する。
常駐サーバーの依存（PyYAML・jsonschema・mcp・Jinja2）は、常駐サーバーを起動する前に確かめ、足りなければそろえるコマンドを示して止まる。

## 使い方

Claude Code の会話を始めると、SessionStart のフックが常駐サーバーを systemd --user のユニットとして起動する（待ち受けていれば何もしない。古いコードで動いていれば再起動の手順を出す）。
プレビューから送信したコメントを Claude Code へ入力させたいときは、起動スクリプトで MindStella のセッションを作る。
起動スクリプトは、依存を確かめ、常駐サーバーが落ちていれば起動してから、MindStella の API でワークスペースと MindStella のセッション（tmux のペインの中の Claude Code）を作り、そのペインへつなぐ。

```bash
{プラグインのフォルダ}/bin/mindstella {ワークスペースのフォルダ}
```

`{プラグインのフォルダ}` は、`claude plugin list --json` の `mindstella@mindstella` の `installPath`。
`{プラグインのフォルダ}/bin/mindstella register set` で起動スクリプトを登録すると、新しいシェルで alias から叩ける。
環境変数も登録でき、Claude Code のアカウントごとの alias `mindstella-{アカウントの名前}` も追加できる。

```bash
mindstella {ワークスペースのフォルダ}
```

tmux の外で立ち上げた Claude Code にも MCP のツールは載るが、プレビューから送信したコメントは Claude Code へ入力されない。

ワークスペースのバージョンがプラグインより古ければ、起動スクリプトがワークスペースを開くときに今のバージョンへ移し替える。

操作の手順は [話し合い](https://shuhei1101.github.io/mindstella/使い方/)、エージェントフローと MCP のツールの一覧は [エージェントフロー](https://shuhei1101.github.io/mindstella/guide/エージェントフロー.html)・[コマンド](https://shuhei1101.github.io/mindstella/guide/コマンド.html) にある。
