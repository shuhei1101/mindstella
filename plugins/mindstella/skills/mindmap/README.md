# mindstella

話し合いを記録しながら、要件・調査・資料作りで決めたことを形にしていく Claude Code のスキル。

## はじめに

Claude Code と話し合いながら、検討事項・そこから派生する問い・調査を、ワークスペース（YAML と Markdown のフォルダ）に記録し、ゴールまで進める。
抽象と具体を行き来する発言をそのまま話しても、記録に残り、再開するときは前回の続きから進められる。

## コアコンセプト

- 記録は 対象 > カテゴリー > フェーズ > 検討事項 の 4 段で整理する。細かいものは派生・依存・タグで表す
- 分野ごとの進め方ガイドが、フェーズの並び・観点・必ず調べるもの・ゴール・リリースの形を決める
- 話し合いは、取り込み・ヒアリング・リサーチ・方針転換・範囲の見直し・プレビュー・ゴール判定のステップで進む
- ワークスペースへの書き込みは、全て MCP のツールを通す。書き込む前にスキーマと突き合わせ、合わなければ何も書き換えない
- MCP のツールは、起動スクリプトで立ち上げた Claude Code にだけ載る。サーバーがプレビューも配り、項目や選んだ箇所へのコメントをレビュー中に溜めて、コメントの一覧から選んで送れる

詳しくは [話し合いの進め方](https://shuhei1101.github.io/mindstella/はじめに/コアコンセプト/話し合いの進め方.html) を読む。

## ユースケース（分野）

| 分野 | 進め方ガイド | ゴールの例 |
| --- | --- | --- |
| システム開発 | [システム開発](./playbooks/システム開発.md) | 要件まで / インターフェースまで（既定）/ モジュール構成まで |
| 調査 | [調査](./playbooks/調査.md) | 事実まで / 評価まで / 結論まで（既定） |
| 資料作り | [資料作り](./playbooks/資料作り.md) | 構成まで / コンテンツまで（既定）/ 仕上げまで |
| 壁打ち | [壁打ち](./playbooks/壁打ち.md) | 整理まで / 結論まで（既定） |

## 依存とインストール

Claude Code 2.1.287 以上と、Python 3.12 以上（`venv` を含む）と、tmux が要る。
マーケットプレイスを登録して、プラグインをインストールする。

```bash
claude plugin marketplace add shuhei1101/mindstella
claude plugin install mindstella@mindstella
```

起動中の Claude Code では `/reload-plugins` を実行する。
サーバーの依存（PyYAML・jsonschema・mcp）は、起動スクリプトが確かめ、足りなければそろえるコマンドを示して止まる。

## 使い方

スキルを呼ぶ前に、起動スクリプトで Claude Code を立ち上げる。
起動スクリプトは、依存を確かめ、tmux のセッションの中で mindstella の MCP サーバーを渡した Claude Code を起動して、そのセッションへつなぐ。

```bash
{プラグインのフォルダ}/bin/mindstella {ワークスペースのフォルダ}
```

`{プラグインのフォルダ}` は、`claude plugin list --json` の `mindstella@mindstella` の `installPath`。
`/mindstella:setup` で起動スクリプトを登録すると、新しいシェルで alias から叩ける。
環境変数も登録でき、Claude Code のアカウントごとの alias `mindstella-{アカウントの名前}` も足せる。

```bash
mindstella {ワークスペースのフォルダ}
```

起動スクリプト以外で立ち上げた Claude Code には、MCP のツールが載らない。

| やりたいこと | 呼び方 |
| --- | --- |
| 新しい話し合いを始める | `/mindstella:setup {ワークスペースのフォルダ}` |
| 途中まで進んだ話し合いを再開する | `/mindstella:setup {ワークスペースのフォルダ}` |
| セットアップの後に話し合いを進める | `/mindstella:session {ワークスペースのフォルダ}` |
| プラグインを上げた後にワークスペースを今の版へ移し替える | `/mindstella:upgrade {ワークスペースのフォルダ}` |

`/mindstella:setup` は、フォルダに `.mindstella/config.yaml` も、直下の `config.yaml`・`mindmap.yaml` も無ければ新しいワークスペースを作り、あれば状況を示して続きを推奨する。
直下の `config.yaml` か `mindmap.yaml` だけなら版が古いワークスペースとして `/mindstella:upgrade` を案内する。
最後に `/mindstella:session` で続けるよう案内する。
ワークスペースの版がプラグインより古ければ、`/mindstella:setup`・`/mindstella:session` は `/mindstella:upgrade` を案内して止まる。
MCP のツールが載っていない会話では、スキルは何も書き込まずに、起動スクリプトでの立ち上げを案内して止まる。

操作の手順は [話し合い](https://shuhei1101.github.io/mindstella/使い方/話し合い/)、スキルと MCP のツールの一覧は [スキル](https://shuhei1101.github.io/mindstella/リファレンス/スキル.html)・[コマンド](https://shuhei1101.github.io/mindstella/リファレンス/コマンド.html) にある。
