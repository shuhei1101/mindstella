"""graph/looks.ts（ネットワークの 5 つの見た目の描き方と、一度だけ焼く絵）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 名前の色の fallback（tokens.css の名前の色の代わり）
FALLBACK_COLOR = "#111111"

# 光の玉の絵の一辺（px）
GLOW_SIZE = 128

# 注目の起点と、それにつながる線を持つ 1 コマを、時刻と動きを減らす設定を変えて描き、画素の指紋を返す JavaScript。
# 玉と線の位置は画面の px、`project` は {x, y, depth, scale}、`rotate` は {x, y, z}、`near` は Set を渡す
DRAW_SCRIPT = """({look, times}) => {
    const WIDTH = 240;
    const HEIGHT = 160;
    const CAMERA_DISTANCE = 500;
    const FOCAL = 400;
    const FNV_OFFSET = 2166136261;
    const FNV_PRIME = 16777619;
    const canvas = document.createElement("canvas");
    canvas.width = WIDTH;
    canvas.height = HEIGHT;
    const context = canvas.getContext("2d", {willReadFrequently: true});
    // 視点を縦の軸まわりに少し回す
    const rotate = (v) => {
        const cos = Math.cos(0.4);
        const sin = Math.sin(0.4);
        return {x: v.x * cos + v.z * sin, y: v.y, z: -v.x * sin + v.z * cos};
    };
    // カメラから見た透視
    const project = (v) => {
        const depth = CAMERA_DISTANCE + v.z;
        const scale = FOCAL / depth;
        return {x: WIDTH / 2 + v.x * scale, y: HEIGHT / 2 + v.y * scale, depth, scale};
    };
    const colors = {line: "#7fbfb0", ring: "#ffffff", dot: "#a0f0d7"};
    const makeStar = (id, kind, degree, x, y, extra) => ({
        id, kind, degree, x, y, radius: 6, alpha: 1, color: "#38bdf8",
        selected: false, hover: false, strong: false, seed: 0.37, ...extra,
    });
    // 作り直すたびに同じ玉と線を返す（描き方が玉を書き換えても次のコマに持ち越さない）
    const makeFrame = (now, reducedMotion) => {
        const focus = makeStar("D-3", "decisions", 3, 120, 80, {color: "#f59e0b", selected: true, strong: true, seed: 0.11});
        const decision = makeStar("D-1", "decisions", 1, 60, 50, {color: "#38bdf8", seed: 0.23});
        const task = makeStar("T-2", "tasks", 1, 180, 50, {color: "#a78bfa", seed: 0.58});
        const research = makeStar("R-1", "research", 1, 70, 120, {color: "#34d399", seed: 0.71});
        const note = makeStar("N-1", "notes", 1, 190, 120, {color: "#9ca3af", seed: 0.89});
        const link = (a, b, type) => ({
            from: {x: a.x, y: a.y}, to: {x: b.x, y: b.y}, type,
            fromColor: a.color, toColor: b.color, alpha: 0.8,
        });
        const focusLinks = [link(focus, decision, "depends"), link(task, focus, "for"), link(focus, research, "related")];
        return {
            context, width: WIDTH, height: HEIGHT, dark: true, colors, now,
            stars: [note, research, task, decision, focus],
            links: [...focusLinks, link(research, note, "source")],
            focusLinks, focusId: "D-3", near: new Set(["D-1", "T-2", "R-1"]),
            rotate, project, spread: 120, reducedMotion,
        };
    };
    // 1 コマ描いて、画素全体の指紋（FNV-1a）を返す
    const fingerprint = (now, reducedMotion) => {
        context.setTransform(1, 0, 0, 1, 0, 0);
        context.globalAlpha = 1;
        context.globalCompositeOperation = "source-over";
        context.setLineDash([]);
        context.clearRect(0, 0, WIDTH, HEIGHT);
        MindmapPreview.drawLook({look, frame: makeFrame(now, reducedMotion)});
        const data = context.getImageData(0, 0, WIDTH, HEIGHT).data;
        let hash = FNV_OFFSET;
        for (let i = 0; i < data.length; i++) hash = Math.imul(hash ^ data[i], FNV_PRIME) >>> 0;
        return hash;
    };
    const still = times.map((now) => fingerprint(now, true));
    const moving = times.map((now) => fingerprint(now, false));
    return {
        stillAllSame: new Set(still).size === 1,
        movingDiffers: new Set(moving).size > 1,
    };
}"""

# 色と減衰ごとに光の玉の絵を作り、作った canvas の数と返り値を集めて返す JavaScript
BAKE_GLOW_SCRIPT = """({color, otherFalloff, falloff}) => {
    const created = [];
    const original = document.createElement.bind(document);
    document.createElement = (tag, ...rest) => {
        const element = original(tag, ...rest);
        if (tag === "canvas") created.push(element);
        return element;
    };
    const first = MindmapPreview.bakeGlow({color, falloff});
    const second = MindmapPreview.bakeGlow({color, falloff});
    const other = MindmapPreview.bakeGlow({color, falloff: otherFalloff});
    document.createElement = original;
    return {
        sameCanvas: first === second,
        differentCanvas: first !== other,
        width: first.width,
        height: first.height,
        createdCount: created.length,
    };
}"""


@pytest.mark.parametrize("look", ["glow", "starlight", "constellation", "deep", "dust"])
def test_draw_look_when_reduced_motion(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, look: str
) -> None:
    """動きを減らす設定では、時刻が進んでも同じ絵を描く（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行（時刻 0・950・1,800ms の 3 枚を、動きを減らす設定の有無で描く）
    observed = preview_page.evaluate(DRAW_SCRIPT, {"look": look, "times": [0, 950, 1800]})
    # 検証
    assert observed["stillAllSame"] is True
    assert observed["movingDiffers"] is True


@pytest.mark.parametrize(
    ("look", "dark", "expected"),
    [
        pytest.param("deep", True, "#dfe6ff", id="deep_dark"),
        pytest.param("deep", False, FALLBACK_COLOR, id="deep_light"),
        pytest.param("dust", True, "#c9ced6", id="dust_dark"),
        pytest.param("dust", False, "#2a2f36", id="dust_light"),
        pytest.param("glow", True, FALLBACK_COLOR, id="glow_dark"),
    ],
)
def test_look_label_color(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    look: str,
    dark: bool,
    expected: str,
) -> None:
    """見た目とライト / ダークで名前の色を読み分ける（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    color = preview_page.evaluate(
        "(args) => MindmapPreview.lookLabelColor(args)",
        {"look": look, "dark": dark, "fallback": FALLBACK_COLOR},
    )
    # 検証
    assert color == expected


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        pytest.param("#000000", "#ffffff", "#808080", id="black_white"),
        pytest.param("#ff0000", "#0000ff", "#800080", id="red_blue"),
        pytest.param("#123456", "#123456", "#123456", id="same"),
    ],
)
def test_mid_color(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    start: str,
    end: str,
    expected: str,
) -> None:
    """成分ごとの平均を四捨五入する（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    color = preview_page.evaluate(
        "(args) => MindmapPreview.midColor({from: args.start, to: args.end})",
        {"start": start, "end": end},
    )
    # 検証
    assert color == expected


def test_bake_glow(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """色と減衰ごとに一度だけ作る（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行（#2dd4bf・減衰 2 を 2 回、#2dd4bf・減衰 1.4 を 1 回）
    observed = preview_page.evaluate(
        BAKE_GLOW_SCRIPT, {"color": "#2dd4bf", "falloff": 2, "otherFalloff": 1.4}
    )
    # 検証
    assert observed["sameCanvas"] is True
    assert observed["differentCanvas"] is True
    assert observed["width"] == GLOW_SIZE
    assert observed["height"] == GLOW_SIZE
    assert observed["createdCount"] == 2
