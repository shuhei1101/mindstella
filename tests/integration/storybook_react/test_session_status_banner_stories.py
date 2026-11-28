"""部品設計『MindStellaのセッションの状態のバー.tsx』の状態（React の Storybook のストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .storybook_react_fixture_types import OpenStory

# 部品設計の状態（何も描かない Running は test_running で確かめる）
STATES = (
    "shared-sessionstatusbanner--restarting",
    "shared-sessionstatusbanner--restarting-with-waiting",
    "shared-sessionstatusbanner--failed",
    "shared-sessionstatusbanner--retrying",
    "shared-sessionstatusbanner--launch-record-missing",
    "shared-sessionstatusbanner--long-text",
    "shared-sessionstatusbanner--empty",
    "shared-sessionstatusbanner--narrow",
)

# 再起動に失敗した見出し
FAILED_TITLE = "MindStella のセッションを再起動できませんでした"


@pytest.mark.parametrize("state", STATES)
def test_state_renders(open_story: OpenStory, page_errors: list[str], state: str) -> None:
    """全ての状態のストーリーをエラーなく描く（正常系）。"""
    # 準備・実行
    page = open_story(state)
    # 検証
    assert "sb-show-errordisplay" not in (page.get_attribute("body", "class") or "")
    assert page_errors == []


def test_restarting(open_story: OpenStory) -> None:
    """再起動の途中。role="status" で見出しと準備ができてから入力する旨を出す（正常系）。"""
    # 準備・実行
    status = open_story("shared-sessionstatusbanner--restarting").get_by_role("status")
    # 検証
    expect(status).to_contain_text("MindStella のセッションを再起動しています")
    expect(status).to_contain_text("送信したコメントは、準備ができてから入力します。")


def test_restarting_with_waiting(open_story: OpenStory) -> None:
    """再起動の途中にコメントを 2 件送信した。入力を待っている件数を出す（正常系）。"""
    # 準備・実行
    status = open_story("shared-sessionstatusbanner--restarting-with-waiting").get_by_role("status")
    # 検証
    expect(status).to_contain_text("送信したコメント 2 件は、準備ができてから入力します。")


def test_failed(open_story: OpenStory) -> None:
    """再起動に失敗した。role="alert" で理由と押せる「再起動」を出す（正常系）。"""
    # 準備・実行
    alert = open_story("shared-sessionstatusbanner--failed").get_by_role("alert")
    # 検証
    expect(alert).to_contain_text(FAILED_TITLE)
    expect(alert).to_contain_text("空いたアカウントがありません")
    expect(alert.get_by_role("button", name="再起動")).to_be_enabled()


def test_retrying(open_story: OpenStory) -> None:
    """「再起動」を押してから戻るまで。ボタンを押せなくし「再起動中」にする（正常系）。"""
    # 準備・実行
    alert = open_story("shared-sessionstatusbanner--retrying").get_by_role("alert")
    # 検証
    expect(alert.get_by_role("button", name="再起動中")).to_be_disabled()


def test_launch_record_missing(open_story: OpenStory) -> None:
    """記録が無い警告。role="alert" で見出しと閉じるボタンを出す（正常系）。"""
    # 準備・実行
    alert = open_story("shared-sessionstatusbanner--launch-record-missing").get_by_role("alert")
    # 検証
    expect(alert).to_contain_text("追加の MCP とプラグインの記録がありません")
    expect(alert.get_by_role("button", name="警告を閉じる")).to_be_visible()


def test_running(page: Page, page_errors: list[str], storybook_react_url: str) -> None:
    """起動中。何も出さない（正常系）。"""
    # 準備・実行（ストーリーの根に中身が入らないので、描き終えるのを待ってから確かめる）
    page.goto(f"{storybook_react_url}/iframe.html?id=shared-sessionstatusbanner--running&viewMode=story")
    page.wait_for_load_state("networkidle")
    # 検証
    assert page_errors == []
    expect(page.locator("#storybook-root > *")).to_have_count(0)
    expect(page.get_by_role("status")).to_have_count(0)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_long_text(open_story: OpenStory) -> None:
    """長い理由を折り返し、「再起動」のボタンを押し出さない（正常系）。"""
    # 準備・実行
    page = open_story("shared-sessionstatusbanner--long-text")
    alert = page.get_by_role("alert")
    button = alert.get_by_role("button", name="再起動").bounding_box()
    box = alert.bounding_box()
    # 検証
    assert button is not None
    assert box is not None
    assert button["x"] + button["width"] <= box["x"] + box["width"]
    assert alert.evaluate("e => e.scrollWidth <= e.clientWidth") is True


def test_empty(open_story: OpenStory) -> None:
    """理由が空。見出しと「再起動」のボタンだけを出す（正常系）。"""
    # 準備・実行
    alert = open_story("shared-sessionstatusbanner--empty").get_by_role("alert")
    # 検証
    expect(alert).to_contain_text(FAILED_TITLE)
    expect(alert.get_by_role("button", name="再起動")).to_be_visible()


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。本文を折り返し、横にスクロールさせず、「再起動」のボタンを右に残す（正常系）。"""
    # 準備・実行
    page = open_story("shared-sessionstatusbanner--narrow")
    alert = page.get_by_role("alert")
    # 検証
    assert alert.evaluate("e => e.scrollWidth <= e.clientWidth") is True
    expect(alert.get_by_role("button", name="再起動")).to_be_in_viewport()
