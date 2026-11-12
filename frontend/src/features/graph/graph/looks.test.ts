import { afterEach, describe, expect, test, vi } from "vitest";

import { bakeGlow, drawLook, lookLabelColor, midColor, type LookFrame, type LookStar, type Vec3 } from "@/features/graph/graph/looks";
import type { NetworkLook } from "@/shared/core/records";
import { createRecordingContext } from "@/testing/fake-canvas";

const LOOKS: NetworkLook[] = ["glow", "starlight", "constellation", "deep", "dust"];

const WIDTH = 240;
const HEIGHT = 160;

afterEach(() => {
  vi.restoreAllMocks();
});

/** 光の玉の絵などの作り置きのキャンバスにも、記録する文脈を返させる */
const stubCanvasContext = () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function (this: HTMLCanvasElement) {
    return createRecordingContext(this).context;
  } as unknown as HTMLCanvasElement["getContext"]);
};

const makeStar = (id: string, kind: LookStar["kind"], x: number, y: number, extra: Partial<LookStar> = {}): LookStar => ({
  id, kind, degree: 1, x, y, radius: 6, alpha: 1, color: "#38bdf8", selected: false, hover: false, strong: false, seed: 0.37, ...extra,
});

/** 注目の起点とつながる線を 1 本持つ 1 コマ（呼ぶたびに作り直す） */
const makeFrame = (context: CanvasRenderingContext2D, now: number, reducedMotion: boolean): LookFrame => {
  const focus = makeStar("D-3", "decisions", 120, 80, { color: "#f59e0b", selected: true, strong: true, seed: 0.11, degree: 2 });
  const decision = makeStar("D-1", "decisions", 60, 50, { seed: 0.23 });
  const task = makeStar("T-2", "tasks", 180, 50, { color: "#a78bfa", seed: 0.58 });
  const link = (a: LookStar, b: LookStar, type: "depends" | "for") => ({ from: { x: a.x, y: a.y }, to: { x: b.x, y: b.y }, type, fromColor: a.color, toColor: b.color, alpha: 0.8 });
  const focusLinks = [link(focus, decision, "depends"), link(task, focus, "for")];
  const rotate = (v: Vec3): Vec3 => ({ x: v.x * Math.cos(0.4) + v.z * Math.sin(0.4), y: v.y, z: -v.x * Math.sin(0.4) + v.z * Math.cos(0.4) });
  const project = (v: Vec3) => {
    const depth = 500 + v.z;
    const scale = 400 / depth;
    return { x: WIDTH / 2 + v.x * scale, y: HEIGHT / 2 + v.y * scale, depth, scale };
  };
  return {
    context, width: WIDTH, height: HEIGHT, dark: true, colors: { line: "#7fbfb0", ring: "#ffffff", dot: "#a0f0d7" }, now,
    stars: [task, decision, focus], links: focusLinks, focusLinks, focusId: "D-3", near: new Set(["D-1", "T-2"]),
    rotate, project, spread: 120, reducedMotion,
  };
};

/** 1 コマ描いて、記録した命令と引数を文字列にする */
const recordFrame = (look: NetworkLook, now: number, reducedMotion: boolean): string => {
  const { context, calls } = createRecordingContext();
  drawLook({ look, frame: makeFrame(context, now, reducedMotion) });
  return JSON.stringify(calls.map((call) => [call.name, call.args.map((arg) => (arg instanceof HTMLCanvasElement ? "canvas" : arg))]));
};

describe("drawLook", () => {
  // 動きを減らす設定では、時刻が進んでも同じ描画の命令を出す（正常系）
  test.each(LOOKS)("draw_look_when_reduced_motion %s", (look) => {
    // 準備
    stubCanvasContext();
    const times = [0, 950, 1800];
    // 実行
    const still = times.map((now) => recordFrame(look, now, true));
    const moving = times.map((now) => recordFrame(look, now, false));
    // 検証
    expect(new Set(still).size).toBe(1);
    expect(new Set(moving).size).toBeGreaterThan(1);
  });
});

describe("lookLabelColor", () => {
  // 見た目とライト / ダークで名前の色を読み分ける（正常系）
  test.each([
    ["deep", true, "#dfe6ff"],
    ["deep", false, "#111111"],
    ["dust", true, "#c9ced6"],
    ["dust", false, "#2a2f36"],
    ["glow", true, "#111111"],
  ] as const)("look_label_color %s %s", (look, dark, expected) => {
    expect(lookLabelColor({ look, dark, fallback: "#111111" })).toBe(expected);
  });
});

describe("midColor", () => {
  // 成分ごとの平均を四捨五入する（正常系）
  test.each([
    ["#000000", "#ffffff", "#808080"],
    ["#ff0000", "#0000ff", "#800080"],
    ["#123456", "#123456", "#123456"],
  ])("mid_color %s %s", (from, to, expected) => {
    expect(midColor({ from, to })).toBe(expected);
  });
});

describe("bakeGlow", () => {
  // 色と減衰ごとに一度だけ作る（正常系）
  test("bake_glow", () => {
    // 準備
    stubCanvasContext();
    const create = vi.spyOn(document, "createElement");
    // 実行
    const first = bakeGlow({ color: "#2dd4bf", falloff: 2 });
    const second = bakeGlow({ color: "#2dd4bf", falloff: 2 });
    bakeGlow({ color: "#2dd4bf", falloff: 1.4 });
    // 検証
    expect(second).toBe(first);
    expect(first.width).toBe(128);
    expect(create.mock.calls.filter(([tag]) => tag === "canvas")).toHaveLength(2);
  });
});
