"""core/lock.ts（ロックの押下の判定・2 回押しの読み替え・鍵の震えの量）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 前の押下（時刻 1000ms・位置 (100, 100)・項目 D-1）
LAST_PRESS = {"time": 1000, "x": 100, "y": 100, "id": "D-1"}

# 振れの比べに許す誤差（sin(5π) などの浮動小数点の丸め）
WAVE_TOLERANCE = 1e-9


@pytest.mark.parametrize(
    ("locked", "pressed", "open_id", "expected_action", "expected_locked"),
    [
        pytest.param(None, "D-1", "D-1", "lock", "D-1", id="unlocked_press_open_item"),
        pytest.param(None, "D-2", "D-1", "open", None, id="unlocked_press_other_item"),
        pytest.param(None, None, "D-1", "blank", None, id="unlocked_press_blank"),
        pytest.param("D-1", "D-1", "D-1", "unlock", None, id="locked_press_locked_item_opened"),
        pytest.param("D-1", "D-1", "D-2", "open", "D-1", id="locked_press_locked_item_not_opened"),
        pytest.param("D-1", "D-2", "D-2", "shake", "D-1", id="locked_press_open_other_item"),
        pytest.param("D-1", None, "D-2", "shake", "D-1", id="locked_press_blank"),
        pytest.param("D-1", "D-3", "D-2", "open", "D-1", id="locked_press_unopened_other_item"),
    ],
)
def test_lock_tap(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    locked: str | None,
    pressed: str | None,
    open_id: str | None,
    expected_action: str,
    expected_locked: str | None,
) -> None:
    """ロックの有無・押した項目・開いている項目ですることを読み分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        "(args) => MindmapPreview.lockTap(args)",
        {"locked": locked, "pressed": pressed, "open": open_id},
    )
    # 検証
    assert result == {"action": expected_action, "locked": expected_locked}


@pytest.mark.parametrize(
    ("last", "press", "expected"),
    [
        pytest.param(
            LAST_PRESS,
            {"time": 1449, "x": 123, "y": 100, "id": "D-2"},
            "D-1",
            id="within_time_and_distance",
        ),
        pytest.param(
            LAST_PRESS,
            {"time": 1450, "x": 100, "y": 100, "id": "D-2"},
            "D-2",
            id="time_at_limit",
        ),
        pytest.param(
            LAST_PRESS,
            {"time": 1100, "x": 124, "y": 100, "id": "D-2"},
            "D-2",
            id="distance_at_limit",
        ),
        pytest.param(
            LAST_PRESS,
            {"time": 1100, "x": 100, "y": 100, "id": None},
            "D-1",
            id="blank_press_within_limit",
        ),
        pytest.param(
            None,
            {"time": 1100, "x": 100, "y": 100, "id": "D-2"},
            "D-2",
            id="no_last_press",
        ),
    ],
)
def test_resolve_press(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    last: dict[str, Any] | None,
    press: dict[str, Any],
    expected: str,
) -> None:
    """間隔と位置のずれが両方満たすときだけ前の項目に読み替える（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    resolved = preview_page.evaluate(
        "(args) => MindmapPreview.resolvePress(args)", {"last": last, "press": press}
    )
    # 検証
    assert resolved == expected


@pytest.mark.parametrize(
    ("elapsed", "expected_decay", "expected_wave"),
    [
        pytest.param(0, 1, 0, id="start"),
        pytest.param(50, 0.95, 1, id="first_peak"),
        pytest.param(500, 0.5, 0, id="half"),
    ],
)
def test_shake_at(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    elapsed: int,
    expected_decay: float,
    expected_wave: float,
) -> None:
    """始めは振れなく最も大きく、半分で半分に収まる（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    shake = preview_page.evaluate("(elapsed) => MindmapPreview.shakeAt(elapsed)", elapsed)
    # 検証
    assert shake["decay"] == pytest.approx(expected_decay, abs=WAVE_TOLERANCE)
    assert shake["wave"] == pytest.approx(expected_wave, abs=WAVE_TOLERANCE)
