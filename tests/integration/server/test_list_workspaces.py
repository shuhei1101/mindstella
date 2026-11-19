"""ワークスペースの一覧（GET /workspaces）の結合テスト。"""

from __future__ import annotations

from session_fixtures import SessionWorld


def _three_workspaces(world: SessionWorld) -> list[str]:
    """ワークスペースを 3 つ作り、2 つ目だけをクローズにして、作った順の ID を返す。"""
    ids = [str(world.create_workspace(name)["id"]) for name in ("家計簿", "旅行", "引っ越し")]
    status, body = world.api("POST", f"/workspaces/{ids[1]}/close")
    assert status == 200, body
    return ids


def _state_files(world: SessionWorld) -> dict[str, bytes]:
    """グローバルの設定のファイルと状態のフォルダの中身。"""
    paths = [world.pi.settings_path, *(p for p in world.state_root.rglob("*") if p.is_file())]
    return {str(path): path.read_bytes() for path in sorted(paths)}


def test_normal(session_world: SessionWorld) -> None:
    """クローズしていないワークスペースだけを返す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    ids = _three_workspaces(world)
    before = _state_files(world)
    # 実行
    status, body = world.api("GET", "/workspaces")
    # 検証
    assert status == 200, body
    assert [(entry["id"], entry["closed"]) for entry in body["workspaces"]] == [
        (ids[0], False),
        (ids[2], False),
    ]
    assert body["warnings"] == []
    assert _state_files(world) == before


def test_normal_when_include_closed(session_world: SessionWorld) -> None:
    """include_closed でクローズしたものも返す（正常系）。"""
    # 準備
    world = session_world
    world.start()
    ids = _three_workspaces(world)
    # 実行
    status, body = world.api("GET", "/workspaces?include_closed=true")
    # 検証
    assert status == 200, body
    assert [(entry["id"], entry["closed"]) for entry in body["workspaces"]] == [
        (ids[0], False),
        (ids[1], True),
        (ids[2], False),
    ]


def test_error_when_settings_unreadable(session_world: SessionWorld) -> None:
    """グローバルの設定のファイルを読めないときは空の並びと警告（異常系）。"""
    # 準備
    world = session_world
    world.start()
    world.create_workspace()
    world.pi.settings_path.write_text("sources: [", encoding="utf-8")
    # 実行
    status, body = world.api("GET", "/workspaces")
    # 検証
    assert status == 200, body
    assert body["workspaces"] == []
    assert [warning["stage"] for warning in body["warnings"]] == ["settings"]


def test_error_when_invalid_flag(session_world: SessionWorld) -> None:
    """include_closed の値が違えば 400（異常系）。"""
    # 準備
    world = session_world
    world.start()
    # 実行
    status, body = world.api("GET", "/workspaces?include_closed=yes")
    # 検証
    assert (status, body["stage"]) == (400, "request")
