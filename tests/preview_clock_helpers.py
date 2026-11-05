"""プレビューのテストが共有する、ブラウザの時刻を止めるスクリプト。"""

from __future__ import annotations

__all__ = ["FREEZE_PERFORMANCE_NOW_JS"]

# `performance.now()` を当てた時刻で止めるスクリプト。開く前は `page.add_init_script`、開いた後は `page.evaluate` で当てる。
# 語の差分の打ち切り時刻（行の差分を呼ぶ直前の時刻 + `LINE_DIFF_TIMEOUT_MS`）が、その間の描画にかかった時間で過ぎないようにする
FREEZE_PERFORMANCE_NOW_JS = """{
    const frozen = performance.now();
    performance.now = () => frozen;
}"""
