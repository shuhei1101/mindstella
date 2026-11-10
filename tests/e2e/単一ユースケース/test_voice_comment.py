"""音声でコメントする（コメント・返信の入力のマイクのボタンで話した内容を文字起こしし、送信するか入力欄へ挿入する）の E2E テスト。

voice-paste の代わりの偽の文字起こしのサービスを 127.0.0.1 で起動し、常駐の MCP サーバーをそこへ向けて起動する。
サーバーが配るプレビューを、偽のマイク（Web Audio の音を流すトラック）を持つ実際のブラウザで開く。描画のライブラリは CDN から読む。
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page, expect
from preview_helpers import DETAIL_FORM, DETAIL_MESSAGE, DETAIL_TEXTAREA, REPLY_FORM, REPLY_MESSAGE, REPLY_TEXTAREA, open_thread
from voice_helpers import (
    DENIED_MIC_SCRIPT,
    DENIED_REASON,
    FAKE_MIC_SCRIPT,
    NO_MIC_REASON,
    NO_MIC_SCRIPT,
    SENT_TEXT,
    STOPPED_REASON,
    UNSUPPORTED_REASON,
    VOICE_TIMEOUT_MS,
    ServeVoiceWorkspace,
    StartFakeTranscriber,
    expect_idle,
    expect_mic_blocked,
    open_with_status,
    read_items,
    record,
)
from workspace_fixtures import MakeComment, MakeItem, MakePost, MakeThread

# D-1 の詳細パネルを開いた検討事項のボード
BOARD_D1_HASH = "#tab=decisions&view=board&id=D-1"

# 偽のサーバーが返す文字起こしの結果
TRANSCRIBED = "案 A にする"

# 文字起こしに失敗したときの結果の行の文
FAILED_TEXT = "文字起こしできませんでした。もう一度お試しください。"


def _settings(valid_settings: dict[str, Any], transcription: dict[str, Any]) -> dict[str, Any]:
    """作成を済ませた設定に、文字起こしの設定を加えた設定を返す。"""
    return {**valid_settings, "transcription": transcription}


def test_normal(
    page: Page,
    make_item: MakeItem,
    make_comment: MakeComment,
    valid_settings: dict[str, Any],
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """詳細パネルのコメントの入力で話すと、結果がその 1 件だけのスレッドになり、レビュー中の書き込みは残る（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, root = serve_voice_workspace(
        fake.url,
        make_item("D-1"),
        settings=_settings(valid_settings, {"preset": "開発"}),
        comments=(make_comment("C-1", body="案 B も見たい"),),
    )
    page.add_init_script(FAKE_MIC_SCRIPT)
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    form = page.locator(DETAIL_FORM)
    # 実行
    record(form)
    form.get_by_role("button", name="文字起こし").click()
    # 検証
    expect(page.locator(DETAIL_MESSAGE)).to_have_text(SENT_TEXT, timeout=VOICE_TIMEOUT_MS)
    threads = read_items(root, "threads.yaml")
    assert [(item["status"], item["target"]) for item in threads] == [("open", "D-1")]
    post = threads[0]["posts"][0]
    assert (post["author"], post["body"], post["read"], post["taken"]) == ("user", "案 A にする", False, None)
    assert [item["body"] for item in read_items(root, "comments.yaml")] == ["案 B も見たい"]
    assert [job.preset for job in fake.jobs] == ["開発"]
    expect(page.locator(DETAIL_TEXTAREA)).to_have_value("")
    expect_idle(form)


def test_normal_when_sent_after_typed_text(
    page: Page,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """打ちかけの文字の末尾で話すと、続けた全文がその 1 件だけのスレッドになる（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, root = serve_voice_workspace(fake.url, make_item("D-1"))
    page.add_init_script(FAKE_MIC_SCRIPT)
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    form = page.locator(DETAIL_FORM)
    page.fill(DETAIL_TEXTAREA, "確認: ")
    # 実行
    record(form)
    form.get_by_role("button", name="文字起こし").click()
    # 検証
    expect(page.locator(DETAIL_MESSAGE)).to_have_text(SENT_TEXT, timeout=VOICE_TIMEOUT_MS)
    threads = read_items(root, "threads.yaml")
    assert [(item["target"], item["posts"][0]["author"], item["posts"][0]["body"]) for item in threads] == [
        ("D-1", "user", "確認: 案 A にする")
    ]
    assert read_items(root, "comments.yaml") == []
    expect(page.locator(DETAIL_TEXTAREA)).to_have_value("")
    expect_idle(form)


def test_normal_when_reply_sent(
    page: Page,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    make_comment: MakeComment,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """スレッドの返信の入力で話すと、結果がスレッドの末尾に足され、レビュー中の返信は残る（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    reply = make_comment("C-1", body="了解", thread="TH-1")
    del reply["target"]
    url, root = serve_voice_workspace(
        fake.url,
        make_item("D-1"),
        threads=(
            make_thread(
                "TH-1",
                make_post("TH-1-1", body="どちらにしますか", read=True, taken="2026-01-01T00:00:00+00:00"),
                make_post("TH-1-2", author="ai", body="案 A と案 B があります"),
                target="D-1",
            ),
        ),
        comments=(reply,),
    )
    page.add_init_script(FAKE_MIC_SCRIPT)
    open_with_status(page, f"{url}#tab=decisions&view=board")
    open_thread(page, "TH-1")
    form = page.locator(REPLY_FORM)
    # 実行
    record(form)
    form.get_by_role("button", name="文字起こし").click()
    # 検証
    expect(page.locator(REPLY_MESSAGE)).to_have_text(SENT_TEXT, timeout=VOICE_TIMEOUT_MS)
    posts = read_items(root, "threads.yaml")[0]["posts"]
    assert (len(posts), posts[-1]["author"], posts[-1]["body"], posts[-1]["read"], posts[-1]["taken"]) == (
        3,
        "user",
        "案 A にする",
        False,
        None,
    )
    assert [(item.get("thread"), item["body"]) for item in read_items(root, "comments.yaml")] == [("TH-1", "了解")]
    expect(form.locator("textarea")).to_have_value("")
    expect_idle(form)


def test_normal_when_inserted(
    page: Page,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """文字起こし後の挙動が insert のときは、結果をカーソルの位置に挿入し、何も送らない（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, root = serve_voice_workspace(
        fake.url, make_item("D-1"), settings=_settings(valid_settings, {"action": "insert"})
    )
    page.add_init_script(FAKE_MIC_SCRIPT)
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    form = page.locator(DETAIL_FORM)
    page.fill(DETAIL_TEXTAREA, "確認: ")
    # 実行
    record(form)
    form.get_by_role("button", name="文字起こし").click()
    # 検証
    expect(page.locator(DETAIL_TEXTAREA)).to_have_value("確認: 案 A にする", timeout=VOICE_TIMEOUT_MS)
    assert page.eval_on_selector(DETAIL_TEXTAREA, "(field) => field.selectionStart") == 10
    assert read_items(root, "threads.yaml") == []
    assert read_items(root, "comments.yaml") == []


def test_normal_when_cancelled(
    page: Page,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """録音中に「キャンセル」を押すと、録音を捨て、入力欄と記録を変えずに元のボタンへ戻す（正常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, root = serve_voice_workspace(fake.url, make_item("D-1"))
    page.add_init_script(FAKE_MIC_SCRIPT)
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    form = page.locator(DETAIL_FORM)
    page.fill(DETAIL_TEXTAREA, "案 B も見たい")
    # 実行
    record(form)
    form.get_by_role("button", name="キャンセル").click()
    # 検証
    expect_idle(form)
    expect(page.locator(DETAIL_TEXTAREA)).to_have_value("案 B も見たい")
    assert fake.jobs == []
    assert read_items(root, "threads.yaml") == []
    assert read_items(root, "comments.yaml") == []


def test_error_when_transcriber_stopped(
    page: Page,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    unreachable_transcriber_url: str,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """文字起こしのサービスに届かないときは、コメントと返信の入力のマイクのボタンを押せなくし、理由を出す（異常系）。"""
    # 準備
    url, _ = serve_voice_workspace(
        unreachable_transcriber_url,
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", author="ai", body="どちらにしますか"), target="D-1"),),
    )
    page.add_init_script(FAKE_MIC_SCRIPT)
    # 実行
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    open_thread(page, "TH-1")
    # 「レビューに追加」を押せるはずの状態にする（返信の入力は本文が空のとき押せない）
    page.fill(DETAIL_TEXTAREA, "案 B も見たい")
    page.fill(REPLY_TEXTAREA, "了解")
    # 検証
    expect_mic_blocked(page.locator(DETAIL_FORM), STOPPED_REASON)
    expect_mic_blocked(page.locator(REPLY_FORM), STOPPED_REASON)
    expect(page.locator("body")).not_to_contain_text("voice-paste")


def test_error_when_web_disabled(
    page: Page,
    make_item: MakeItem,
    make_post: MakePost,
    make_thread: MakeThread,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """文字起こしのサービスが音声の受け付けに対応していないときは、マイクのボタンを押せなくし、理由を出す（異常系）。"""
    # 準備
    fake = start_fake_transcriber("unsupported")
    url, _ = serve_voice_workspace(
        fake.url,
        make_item("D-1"),
        threads=(make_thread("TH-1", make_post("TH-1-1", author="ai", body="どちらにしますか"), target="D-1"),),
    )
    page.add_init_script(FAKE_MIC_SCRIPT)
    # 実行
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    open_thread(page, "TH-1")
    # 「レビューに追加」を押せるはずの状態にする（返信の入力は本文が空のとき押せない）
    page.fill(DETAIL_TEXTAREA, "案 B も見たい")
    page.fill(REPLY_TEXTAREA, "了解")
    # 検証
    expect_mic_blocked(page.locator(DETAIL_FORM), UNSUPPORTED_REASON)
    expect_mic_blocked(page.locator(REPLY_FORM), UNSUPPORTED_REASON)


def test_error_when_microphone_unavailable(
    page: Page,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """マイクの機能を持たないページでは、マイクのボタンを押せなくし、HTTPS か localhost で開く旨を出す（異常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, _ = serve_voice_workspace(fake.url, make_item("D-1"))
    page.add_init_script(NO_MIC_SCRIPT)
    # 実行
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    # 検証
    expect_mic_blocked(page.locator(DETAIL_FORM), NO_MIC_REASON)


def test_error_when_microphone_denied(
    page: Page,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """マイクの許可を拒否したブラウザでは、録音を始めず、許可が要る旨を出す（異常系）。"""
    # 準備
    fake = start_fake_transcriber("done")
    url, _ = serve_voice_workspace(fake.url, make_item("D-1"))
    page.add_init_script(DENIED_MIC_SCRIPT)
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    form = page.locator(DETAIL_FORM)
    # 実行
    form.get_by_role("button", name="音声で入力").click()
    # 検証
    expect(page.locator(DETAIL_MESSAGE)).to_have_text(DENIED_REASON, timeout=VOICE_TIMEOUT_MS)
    expect_idle(form)
    assert fake.jobs == []


def test_error_when_transcription_failed(
    page: Page,
    make_item: MakeItem,
    start_fake_transcriber: StartFakeTranscriber,
    serve_voice_workspace: ServeVoiceWorkspace,
) -> None:
    """文字起こしに失敗したときは、失敗した旨を出し、入力欄と記録を変えずに元のボタンへ戻す（異常系）。"""
    # 準備
    fake = start_fake_transcriber("failed")
    url, root = serve_voice_workspace(fake.url, make_item("D-1"))
    page.add_init_script(FAKE_MIC_SCRIPT)
    open_with_status(page, f"{url}{BOARD_D1_HASH}")
    form = page.locator(DETAIL_FORM)
    page.fill(DETAIL_TEXTAREA, "案 B も見たい")
    # 実行
    record(form)
    form.get_by_role("button", name="文字起こし").click()
    # 検証
    expect(page.locator(DETAIL_MESSAGE)).to_have_text(FAILED_TEXT, timeout=VOICE_TIMEOUT_MS)
    expect(page.locator(DETAIL_TEXTAREA)).to_have_value("案 B も見たい")
    expect_idle(form)
    assert read_items(root, "threads.yaml") == []
    assert read_items(root, "comments.yaml") == []
