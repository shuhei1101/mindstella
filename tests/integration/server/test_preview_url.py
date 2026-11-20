"""preview_url（プレビューの URL）の結合テスト。"""

from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from external_access_helpers import (
    HOOK_SETTLE_SEC,
    read_hook_lines,
    read_settled_hook_lines,
    recording_hook,
)
from workspace_fixtures import RECORD_DIR

from .fixture_types import CallTool, MakeItem, MakeWorkspace, SnapshotTree, StartServer
from .history_helpers import DECISION_ITEM, add_item, commit
from .http_helpers import http_request
from .readme_helpers import section_of

# 利用者の README の更新日時として置く、十分に古い日時（ナノ秒）
OLD_MTIME_NS = 1_000_000_000 * 1_000_000_000

# 起動時のフックと終了時のフックを渡す環境変数
START_HOOK_ENV = "MINDSTELLA_PREVIEW_START_HOOK"
STOP_HOOK_ENV = "MINDSTELLA_PREVIEW_STOP_HOOK"

# 配信の URL の頭と、画面のパス（ワークスペースの経路の下）と、URL のパスの形
URL_PREFIX = "http://127.0.0.1:"
PAGE_PATH = "/mindstella.html"
WORKSPACE_PAGE_PATH = re.compile(r"/w/mindstella-[^/]+/mindstella\.html")

# 2 つのフォルダが重ねて持つワークスペースの ID
CONFLICT_ID = "mindstella-話し合いA-0a1b2c"

# 記録にあるまとまりと、記録に無いまとまり
KNOWN_SET_ID = "V-1"
UNKNOWN_SET_ID = "V-99"


def test_normal(make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool) -> None:
    """初めて呼ぶと配信を立て、127.0.0.1 の URL を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["url"].startswith(URL_PREFIX)
    assert WORKSPACE_PAGE_PATH.fullmatch(urlsplit(result.data["url"]).path)
    assert result.data["started"] is True
    assert http_request(result.data["url"], PAGE_PATH).status == 200
    assert not (root / "preview.html").exists()
    # 直下の README のプレビューの節に、返した URL が書かれる
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    assert result.data["url"] in section_of(readme_text, "## プレビュー")


def test_normal_when_user_readme_exists(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """自動で書いた印の無い README.md は書き換えずに配信を立てる（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    readme = root / "README.md"
    readme.write_text("# 家計簿アプリの話し合い\n", encoding="utf-8")
    os.utime(readme, ns=(OLD_MTIME_NS, OLD_MTIME_NS))
    content_before = readme.read_bytes()
    mtime_before = readme.stat().st_mtime_ns
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["started"] is True
    assert readme.read_bytes() == content_before
    assert readme.stat().st_mtime_ns == mtime_before


def test_normal_when_called_again(
    make_workspace: MakeWorkspace, make_item: MakeItem, call_tool: CallTool
) -> None:
    """同じワークスペースで呼び直すと、同じ URL を返して配信を増やさない（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    first = call_tool("preview_url", workspace=str(root))
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is False
    assert first.data is not None
    assert result.data is not None
    assert result.data["url"] == first.data["url"]
    assert result.data["started"] is False


def test_error_when_workspace_not_found(tmp_path: Path, call_tool: CallTool) -> None:
    """config.yaml が無いフォルダを指すと、配信を立てずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert str(root) in result.text


def test_error_when_config_invalid(
    make_workspace: MakeWorkspace,
    valid_settings: dict[str, Any],
    call_tool: CallTool,
    snapshot_tree: SnapshotTree,
) -> None:
    """config.yaml がスキーマに合わないと、違う箇所を返して配信を立てない（異常系）。"""
    # 準備
    root = make_workspace(settings={**valid_settings, "display": {"visible_kinds": ["rainbow"]}})
    before = snapshot_tree(root)
    # 実行
    result = call_tool("preview_url", workspace=str(root))
    # 検証
    assert result.is_error is True
    assert any(
        line.startswith("config.yaml: display.visible_kinds") and "decisions" in line
        for line in result.text.splitlines()
    )
    assert snapshot_tree(root) == before
    # 配信が立っていないので、もう一度呼んでも同じエラーになる
    again = call_tool("preview_url", workspace=str(root))
    assert again.is_error is True
    assert "config.yaml: display.visible_kinds" in again.text


def test_normal_when_start_hook_set(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    start_server: StartServer,
) -> None:
    """配信を立てたときだけ、起動時のフックをポート・ワークスペースの名前・画面のパスを足して呼ぶ（正常系）。"""
    # 準備
    record = tmp_path / "start-hook.txt"
    root = make_workspace(make_item("D-1"), name="家計簿")
    server = start_server(extra_env={START_HOOK_ENV: recording_hook(record)})
    # 実行（2 回目は立て済みなので、フックを呼ばない）
    first = server.call("preview_url", workspace=str(root))
    second = server.call("preview_url", workspace=str(root))
    # 検証
    assert first.data is not None
    assert second.data is not None
    assert (first.data["started"], second.data["started"]) == (True, False)
    parts = urlsplit(first.data["url"])
    assert read_hook_lines(record) == [f"{parts.port} 家計簿 {parts.path}"]
    assert read_settled_hook_lines(record) == [f"{parts.port} 家計簿 {parts.path}"]
    # 存在しないコマンドをフックにしても、ツールのエラーにならず url を返す
    missing_server = start_server(extra_env={START_HOOK_ENV: "mindstella-no-such-command"})
    other_root = make_workspace(make_item("D-1"), name="別の話し合い")
    missing = missing_server.call("preview_url", workspace=str(other_root))
    assert missing.is_error is False
    assert missing.data is not None
    assert missing.data["url"].startswith(URL_PREFIX)
    assert http_request(missing.data["url"], PAGE_PATH).status == 200


def _make_workspace_with_set(make_workspace: MakeWorkspace, call_tool: CallTool) -> Path:
    """検討事項 D-1 を足して `commit` し、まとまり V-1 を持つワークスペースを作る。

    項目を足すと call_tool の常駐サーバーがそのワークスペースの配信を立てる（変更の検知を動かすため）。
    """
    root = make_workspace()
    add_item(call_tool, root, "decision", DECISION_ITEM)
    assert commit(call_tool, root, "足す")["id"] == KNOWN_SET_ID
    return root


def _make_workspace_with_set_unserved(
    make_workspace: MakeWorkspace, start_server: StartServer
) -> Path:
    """まとまり V-1 を持つワークスペースを、別の常駐サーバーで作る（fixture call_tool の常駐サーバーは配信を立てていない）。"""
    return _make_workspace_with_set(make_workspace, start_server().call)


def test_normal_when_diff_given(
    make_workspace: MakeWorkspace, call_tool: CallTool, start_server: StartServer
) -> None:
    """diff を渡すと、そのまとまりの差分を開くハッシュを付けた URL を返す（正常系）。"""
    # 準備
    root = _make_workspace_with_set_unserved(make_workspace, start_server)
    # 実行
    result = call_tool("preview_url", workspace=str(root), diff=KNOWN_SET_ID)
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["url"].startswith(URL_PREFIX)
    assert result.data["url"].endswith(f"{PAGE_PATH}#diff={KNOWN_SET_ID}")
    assert result.data["started"] is True
    # 直下の README のプレビューの節の URL はハッシュを持たない
    readme_text = (root / "README.md").read_text(encoding="utf-8")
    assert "#diff=" not in section_of(readme_text, "## プレビュー")
    # diff を渡さずに呼び直すと、ハッシュの無い同じポートの URL が返る
    again = call_tool("preview_url", workspace=str(root))
    assert again.data is not None
    assert again.data["url"] == result.data["url"].split("#")[0]
    assert again.data["started"] is False


def test_error_when_diff_not_found(
    make_workspace: MakeWorkspace, call_tool: CallTool, start_server: StartServer
) -> None:
    """記録に無いまとまりを diff に渡すと、配信を立てずに終わる（異常系）。"""
    # 準備
    root = _make_workspace_with_set_unserved(make_workspace, start_server)
    # 実行
    result = call_tool("preview_url", workspace=str(root), diff=UNKNOWN_SET_ID)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: diff:")
    assert UNKNOWN_SET_ID in result.text
    # 配信を立てていないので、diff を渡さずに呼ぶと立てる
    again = call_tool("preview_url", workspace=str(root))
    assert again.data is not None
    assert again.data["started"] is True


def test_normal_when_diff_given_while_serving(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """既に配っているワークスペースで diff を渡すと、同じポートでハッシュを付けた URL を返す（正常系）。"""
    # 準備
    root = _make_workspace_with_set(make_workspace, call_tool)
    first = call_tool("preview_url", workspace=str(root))
    assert first.data is not None
    # 実行
    result = call_tool("preview_url", workspace=str(root), diff=KNOWN_SET_ID)
    # 検証
    assert result.is_error is False
    assert result.data is not None
    assert result.data["url"] == f"{first.data['url']}#diff={KNOWN_SET_ID}"
    assert result.data["started"] is False


def test_error_when_diff_not_found_while_serving(
    make_workspace: MakeWorkspace, call_tool: CallTool
) -> None:
    """既に配っているワークスペースでも、記録に無いまとまりを diff に渡すとエラーになる（異常系）。"""
    # 準備
    root = _make_workspace_with_set(make_workspace, call_tool)
    first = call_tool("preview_url", workspace=str(root))
    assert first.data is not None
    # 実行
    result = call_tool("preview_url", workspace=str(root), diff=UNKNOWN_SET_ID)
    # 検証
    assert result.is_error is True
    assert result.text.startswith("エラー: 引数の誤り: diff:")
    assert UNKNOWN_SET_ID in result.text
    # 配信は止まらない
    assert http_request(first.data["url"], PAGE_PATH).status == 200


def test_error_when_workspace_id_conflicts(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
) -> None:
    """配っている別のフォルダと ID が同じフォルダを指すと、配らずに終わる（異常系）。"""
    # 準備（B は config.yaml の id を持つ A のフォルダを丸ごと写し、記録の題だけを変える）
    record = tmp_path / "start-hook.txt"
    folder_a = make_workspace(
        make_item("D-1", title="A の検討事項"),
        settings={**valid_settings, "id": CONFLICT_ID},
        name="話し合いA",
    )
    server = start_server(extra_env={START_HOOK_ENV: recording_hook(record)})
    served_a = server.call("preview_url", workspace=str(folder_a))
    assert served_a.data is not None, served_a.text
    folder_b = tmp_path / "話し合いB"
    shutil.copytree(folder_a, folder_b)
    decisions_b = folder_b / RECORD_DIR / "decisions.yaml"
    decisions_b.write_text(
        decisions_b.read_text(encoding="utf-8").replace("A の検討事項", "B の検討事項"),
        encoding="utf-8",
    )
    readme_b = (folder_b / "README.md").read_bytes()
    # 実行
    result = server.call("preview_url", workspace=str(folder_b))
    # 検証
    assert result.is_error is True
    assert CONFLICT_ID in result.text
    assert str(folder_a.resolve()) in result.text
    records = http_request(served_a.data["url"], "/api/records")
    assert records.status == 200
    assert [item["title"] for item in records.json()["decisions"]] == ["A の検討事項"]
    assert (folder_b / "README.md").read_bytes() == readme_b
    # フックが呼ばれるなら届くはずの間だけ待ち、B の行が無いことを確かめる
    time.sleep(HOOK_SETTLE_SEC)
    assert all("話し合いB" not in line for line in read_hook_lines(record))


def test_normal_when_folder_moved(
    tmp_path: Path,
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_server: StartServer,
) -> None:
    """配っているフォルダを移した先を指すと、前のフォルダの配信をやめて移した先を同じ URL で配る（正常系）。"""
    # 準備
    start_record = tmp_path / "start-hook.txt"
    stop_record = tmp_path / "stop-hook.txt"
    folder_a = make_workspace(
        make_item("D-1", title="移す前の検討事項"),
        settings={**valid_settings, "id": CONFLICT_ID},
        name="話し合いA",
    )
    server = start_server(
        extra_env={
            START_HOOK_ENV: recording_hook(start_record),
            STOP_HOOK_ENV: recording_hook(stop_record),
        }
    )
    first = server.call("preview_url", workspace=str(folder_a))
    assert first.data is not None, first.text
    moved = tmp_path / "移した先"
    folder_a.rename(moved)
    decisions = moved / RECORD_DIR / "decisions.yaml"
    decisions.write_text(
        decisions.read_text(encoding="utf-8").replace("移す前の検討事項", "移した先の検討事項"),
        encoding="utf-8",
    )
    # 実行
    result = server.call("preview_url", workspace=str(moved))
    # 検証
    assert result.is_error is False, result.text
    assert result.data is not None
    assert (result.data["url"], result.data["started"]) == (first.data["url"], True)
    records = http_request(result.data["url"], "/api/records")
    assert [item["title"] for item in records.json()["decisions"]] == ["移した先の検討事項"]
    parts = urlsplit(result.data["url"])
    assert read_settled_hook_lines(stop_record) == [f"{parts.port} 話し合いA {parts.path}"]
    assert read_settled_hook_lines(start_record) == [
        f"{parts.port} 話し合いA {parts.path}",
        f"{parts.port} 移した先 {parts.path}",
    ]
