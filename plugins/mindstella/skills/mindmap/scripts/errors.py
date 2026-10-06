"""ツールのエラーにする例外。"""

from __future__ import annotations


class MindmapError(Exception):
    """入口（`call_tool`）が捕まえてツールのエラーにする例外の親。配信は子の種類でステータスコードを決める。"""

    def __init__(self, message: str, lines: list[str] | None = None) -> None:
        """メッセージと、`エラー: {内容}` の後に続けて本文に出す行を持つ。"""
        super().__init__(message)
        self.lines: list[str] = lines if lines is not None else []


class WorkspaceNotFoundError(MindmapError):
    """`.mindstella/config.yaml` が無いフォルダを指した。直下に前の版の設定ファイルだけがあるフォルダでは、`lines` に移し替えの案内を持つ。"""


class WorkspaceExistsError(MindmapError):
    """`.mindstella/config.yaml` か、直下の `config.yaml`・`mindmap.yaml`（前の版の設定ファイル）が既にあるフォルダに作ろうとした。直下の前の版の設定ファイルでは、`lines` に移し替えの案内を持つ。"""


class SchemaMismatchError(MindmapError):
    """書き込もうとした・書き出そうとした・読もうとしたワークスペースがスキーマに合わない。"""

    def __init__(self, lines: list[str], *, legacy: bool = False) -> None:
        """合わない箇所ごとの `{ファイル名}: {キーのパス}: {理由}` の行と、前の版の形式の問題があるかを持つ。"""
        super().__init__("スキーマに合いません", lines)
        # 問題に前の版の形式（資料の `done`・題名の無い設定・`field` を持つ設定）のものがあるか
        self.legacy = legacy


class UnmappedPhaseError(MindmapError):
    """新しい `phases` に対応の無いフェーズを持つ項目か `goal.phase` が残る。`lines` に残るものごとの `{ID か goal}: {フェーズ}` を持つ。"""

    def __init__(self, unmapped: list[tuple[str, str]]) -> None:
        """残るもの（ID か `goal`、フェーズ）を持ち、その並びを `lines` の行にする。"""
        super().__init__(
            "新しいフェーズに対応の無いフェーズが残ります",
            [f"{owner}: {phase}" for owner, phase in unmapped],
        )
        self.unmapped = unmapped


class UnmappedTargetError(MindmapError):
    """新しい設定に無い対象・カテゴリーを持つ項目かカテゴリーが残る、または `target_map`・`category_map` の値が新しい設定に無い。`lines` に残るものごとの行を持つ。"""

    def __init__(self, lines: list[str]) -> None:
        """残るものごとの行を持ち、メッセージを固定の文言にする。"""
        super().__init__("新しい設定に対応の無い対象・カテゴリーが残ります", lines)


class ItemNotFoundError(MindmapError):
    """渡した ID の項目が無い。"""


class SettingsInvalidError(MindmapError):
    """既定の書き換えの要求の本文に `network_look`・`visible_kinds` が無い・値が合わない。メッセージは `{キー}: {理由}`。"""


class OptionNotFoundError(MindmapError):
    """検討事項が渡した記号の案を持たない（`adopt` の切り替え・`edit_option` の `update`・`remove`）。"""


class OptionExistsError(MindmapError):
    """`edit_option` の `add` で、検討事項が同じ記号の案を既に持つ。"""


class AdoptedOptionError(MindmapError):
    """`edit_option` の `remove` で、採用している案を指した。"""


class WriteFailedError(MindmapError):
    """ファイルの書き込み・置き換えで OSError が起きた。"""


class ArgumentError(MindmapError):
    """ツールが確かめる引数の誤り（一緒に使わない引数・値の形が違う・`out` が `.html` で終わらない）。"""

    def __init__(self, argument: str, reason: str) -> None:
        """誤った引数の名前と理由を持ち、メッセージを `引数の誤り: {引数の名前}: {理由}` にする。"""
        super().__init__(f"引数の誤り: {argument}: {reason}")
        self.argument = argument


class DownloadFailedError(MindmapError):
    """配る書き出しで jsDelivr から配布ファイルかライセンスの本文を取れないか、配布ファイルが `integrity` と合わない。"""


class WorkspaceNewerError(MindmapError):
    """ワークスペースの版がプラグインの版より新しいのに、手順を当てる・版を書こうとした。メッセージに 2 つの版とプラグインの更新の案内を持つ。"""


class StepFailedError(MindmapError):
    """移し替えの手順が失敗し、写しから戻した。メッセージは `{版} の手順 {番号}（{操作}）: {理由}`。"""


class StepsInvalidError(MindmapError):
    """プラグインの `steps.yaml` が読めないか、手順の形のスキーマに合わない。`lines` は合わない箇所。"""


class SubmissionNotFoundError(MindmapError):
    """渡した ID の送信が無い。"""


class ServeFailedError(MindmapError):
    """プレビューの配信の待ち受けを立てられない（`OSError`）。"""


class CommentInvalidError(MindmapError):
    """コメント・書きかけ・まとめて送るの要求のキーが無い・型が違う、本文が空白だけか上限を超える、箇所の形が崩れている。メッセージは `{キーのパス}: {理由}`。"""


class CommentNotFoundError(MindmapError):
    """渡した ID のコメントがレビュー中に無い。メッセージに無い ID（複数なら `、` でつなぐ）。"""


class CommentConflictError(MindmapError):
    """箇所が今の項目に合わない・向けた項目が消えた・元に戻す ID が使えない。`stale` に合わないコメントの `(ID, 理由)` を溜めた順に持つ（まとめて送るときだけ）。"""

    def __init__(self, message: str, *, stale: list[tuple[str, str]] | None = None) -> None:
        """合わない理由と、合わないコメントごとの ID と理由を持つ。"""
        super().__init__(message)
        self.stale: list[tuple[str, str]] = stale if stale is not None else []
