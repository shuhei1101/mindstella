import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { PanelResizer } from "@/shared/components/panel-resizer";

type FrameCallback = (time: number) => void;

/** 手で進めるフレームの呼び出しの待ち */
let frames: FrameCallback[] = [];

/** 待っているフレームの呼び出しを全て実行する */
const flushFrames = (): void => {
  const pending = frames;
  frames = [];
  for (const callback of pending) callback(0);
};

/** requestAnimationFrame をすぐ実行する関数に差し替える */
const stubImmediateFrames = (): void => {
  vi.stubGlobal("requestAnimationFrame", (callback: FrameCallback) => {
    callback(0);
    return 1;
  });
};

beforeEach(() => {
  // jsdom はポインターの捕捉を持たないため、捕捉の呼び出しだけを受ける
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  frames = [];
});

type Side = "left" | "right";

const renderResizer = ({ side, width, min = 320, max = 1040 }: { side: Side; width: number; min?: number; max?: number }) => {
  const onChange = vi.fn<(width: number) => void>();
  const onCommit = vi.fn<(width: number) => void>();
  render(
    <PanelResizer side={side} width={width} min={min} max={max} step={16} label="パネルの幅" onChange={onChange} onCommit={onCommit} />,
  );
  return { separator: screen.getByRole("separator", { name: "パネルの幅" }), onChange, onCommit };
};

describe("PanelResizer", () => {
  // 左端の区切りを左へドラッグすると広がる（正常系）
  test("panel_resizer_when_left_drag", () => {
    // 準備
    stubImmediateFrames();
    const { separator, onChange, onCommit } = renderResizer({ side: "left", width: 640 });
    // 実行
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 700 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 600 });
    fireEvent.pointerUp(separator, { pointerId: 1, clientX: 600 });
    // 検証
    expect(onChange).toHaveBeenLastCalledWith(740);
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit).toHaveBeenCalledWith(740);
  });

  // 右端の区切りを右へドラッグすると広がる（正常系）
  test("panel_resizer_when_right_drag", () => {
    // 準備
    stubImmediateFrames();
    const { separator, onChange, onCommit } = renderResizer({ side: "right", width: 384 });
    // 実行
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 400 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 500 });
    fireEvent.pointerUp(separator, { pointerId: 1, clientX: 500 });
    // 検証
    expect(onChange).toHaveBeenLastCalledWith(484);
    expect(onCommit).toHaveBeenCalledWith(484);
  });

  // 下限・上限に収める（正常系）
  test.each([
    { name: "下限を超えて狭める", moveTo: 900, expected: 320 },
    { name: "上限を超えて広げる", moveTo: 0, expected: 800 },
  ])("panel_resizer_when_clamped: $name", ({ moveTo, expected }) => {
    // 準備
    stubImmediateFrames();
    const { separator, onChange } = renderResizer({ side: "left", width: 400, min: 320, max: 800 });
    // 実行
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 500 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: moveTo });
    // 検証
    expect(onChange).toHaveBeenLastCalledWith(expected);
  });

  // ドラッグ中の onChange を 1 フレームに 1 回にまとめる（正常系）
  test("panel_resizer_when_frames_coalesced", () => {
    // 準備
    vi.stubGlobal("requestAnimationFrame", (callback: FrameCallback) => {
      frames.push(callback);
      return frames.length;
    });
    const { separator, onChange, onCommit } = renderResizer({ side: "left", width: 640 });
    // 実行
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 700 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 690 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 680 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 670 });
    flushFrames();
    // 検証
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(670);
    expect(onCommit).not.toHaveBeenCalled();
  });

  // ドラッグが中断しても確定する（正常系）
  test.each(["pointerCancel", "lostPointerCapture"] as const)("panel_resizer_when_drag_cancelled: %s", (endEvent) => {
    // 準備
    stubImmediateFrames();
    const { separator, onCommit } = renderResizer({ side: "left", width: 640 });
    // 実行
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 700 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 650 });
    fireEvent[endEvent](separator, { pointerId: 1, clientX: 650 });
    // 検証
    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(onCommit).toHaveBeenCalledWith(690);
  });

  // 矢印キー・Home・End で幅を変えて確定する（正常系）
  test.each([
    { name: "左端で ←", side: "left", key: "ArrowLeft", expected: 656 },
    { name: "右端で →", side: "right", key: "ArrowRight", expected: 656 },
    { name: "Home", side: "left", key: "Home", expected: 480 },
    { name: "End", side: "left", key: "End", expected: 1040 },
  ] as const)("panel_resizer_when_keys: $name", ({ side, key, expected }) => {
    // 準備
    const { separator, onChange, onCommit } = renderResizer({ side, width: 640, min: 480, max: 1040 });
    // 実行
    const notCanceled = fireEvent.keyDown(separator, { key });
    // 検証
    expect(onChange).toHaveBeenCalledWith(expected);
    expect(onCommit).toHaveBeenCalledWith(expected);
    expect(notCanceled).toBe(false);
  });

  // 指のドラッグでも幅が変わる（正常系）
  test("panel_resizer_when_touch", () => {
    // 準備
    stubImmediateFrames();
    const { separator, onChange, onCommit } = renderResizer({ side: "left", width: 640 });
    // 実行
    fireEvent.pointerDown(separator, { pointerType: "touch", pointerId: 1, clientX: 700 });
    fireEvent.pointerMove(separator, { pointerType: "touch", pointerId: 1, clientX: 600 });
    fireEvent.pointerUp(separator, { pointerType: "touch", pointerId: 1, clientX: 600 });
    // 検証（左へ 100px 動かした分だけ広がる）
    expect(onChange).toHaveBeenLastCalledWith(740);
    expect(onCommit).toHaveBeenCalledWith(740);
  });

  // 読み上げの属性を持つ（正常系）
  test("panel_resizer_aria", () => {
    // 準備・実行
    const onChange = vi.fn<(width: number) => void>();
    render(
      <PanelResizer side="right" width={384} min={320} max={800} step={16} label="コメントの一覧の幅" onChange={onChange} onCommit={onChange} />,
    );
    // 検証
    const separator = screen.getByRole("separator", { name: "コメントの一覧の幅" });
    expect(separator).toHaveAttribute("aria-orientation", "vertical");
    expect(separator).toHaveAttribute("aria-valuenow", "384");
    expect(separator).toHaveAttribute("aria-valuemin", "320");
    expect(separator).toHaveAttribute("aria-valuemax", "800");
    expect(separator).toHaveAttribute("tabindex", "0");
  });
});
