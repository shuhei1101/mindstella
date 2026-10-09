"""話し合いのセットアップ（利用者が依存を確かめ、新しいワークスペースを作るか既存の続きを選ぶ）のうち、版の比較の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from workspace_fixtures import (
    RECORD_DIR,
    REPO_ROOT,
    CallTool,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
)

# ワークスペースの版を持つファイルの名前
VERSION_FILE = "mindstella-version.ini"

# 版が新しいワークスペースに書く版
NEWER_VERSION = "v99.0.0"

# 前の版（v0.6.0 より前）の設定ファイルの名前
LEGACY_SETTINGS = "mindmap.yaml"


def _plugin_version() -> str:
    """プラグインの版（`plugins/mindstella/version.ini` の 1 行目）を返す。"""
    path = REPO_ROOT / "plugins" / "mindstella" / "version.ini"
    return path.read_text(encoding="utf-8").splitlines()[0]


def _version_key(version: str) -> tuple[int, ...]:
    """`v0.5.0` の形の版を、大小を比べられる数の並びにする。"""
    return tuple(int(part) for part in version.removeprefix("v").split("."))


def _step_versions_after(version: str) -> set[str]:
    """`version` より新しく、プラグインの版までの移し替えの手順の版の集まりを返す。"""
    migrations = (
        REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "migrations"
    )
    plugin = _version_key(_plugin_version())
    return {
        folder.name
        for folder in migrations.iterdir()
        if folder.is_dir()
        and _version_key(version) < _version_key(folder.name) <= plugin
    }


def test_normal_when_older_version(
    make_legacy_workspace: MakeLegacyWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """版が古いワークスペースでは、状況を示さず、移し替えのスキルを案内して止まる（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        legacy_docs={"A-1": True}, settings_file=LEGACY_SETTINGS, top=True
    )
    before = snapshot_tree(root)
    # 実行
    # 手順が連ねるのは版の比較までで、status は呼ばない
    plan = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    # 版の比較が、ワークスペースの版を「版を記録する前の形式」、プラグインより古いと返す
    assert plan.is_error is False
    payload = plan.data
    assert payload["workspace_version"] is None
    assert payload["relation"] == "older"
    # 設定は config.yaml でなく直下の mindmap.yaml だけを持つ
    assert not (root / RECORD_DIR).exists()
    assert (root / LEGACY_SETTINGS).exists()
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_newer_version(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """版が新しいワークスペースでは、状況を示さず、プラグインを更新するよう案内して止まる（異常系）。"""
    # 準備
    root = make_workspace(raw_files={VERSION_FILE: f"{NEWER_VERSION}\n"})
    before = snapshot_tree(root)
    # 実行
    # 手順が連ねるのは版の比較までで、status は呼ばない
    plan = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    # 版の比較が、ワークスペースの版がプラグインより新しいと返す
    assert plan.is_error is False
    assert plan.data["relation"] == "newer"
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_normal_when_version_recorded_at_top(
    make_workspace: MakeWorkspace,
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """直下に版を記録した古いワークスペースでは、状況を示さず、移し替えのスキルを案内して止まる（正常系）。"""
    # 準備
    root = make_workspace(settings_file=LEGACY_SETTINGS, top=True)
    (root / VERSION_FILE).write_text("v0.5.0\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    # 手順が連ねるのは版の比較までで、status は呼ばない
    plan = call_tool("migrate", workspace=str(root), plan=True)
    # 検証
    # 版の比較が、ワークスペースの版を v0.5.0、プラグインより古いと返し、当てる手順が v0.5.0 より新しくプラグインの版までの手順である
    assert plan.is_error is False
    payload = plan.data
    assert payload["workspace_version"] == "v0.5.0"
    assert payload["relation"] == "older"
    assert {step["version"] for step in payload["steps"]} == _step_versions_after(
        "v0.5.0"
    )
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before
