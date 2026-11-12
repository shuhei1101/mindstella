import { afterEach, describe, expect, test, vi } from "vitest";

import { createGraphRenderer } from "@/features/graph/graph/graph-renderer";
import { createRecordingContext } from "@/testing/fake-canvas";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

/** キャンバスと重ねる層を用意し、コマの関数を手で進められるようにする */
const setup = () => {
  const frames: FrameRequestCallback[] = [];
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frames.push(callback);
    return frames.length;
  });
  const cancel = vi.fn();
  vi.stubGlobal("cancelAnimationFrame", cancel);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function (this: HTMLCanvasElement) {
    return createRecordingContext(this).context;
  });
  const canvas = document.createElement("canvas");
  const overlay = document.createElement("div");
  document.body.append(canvas, overlay);
  return { frames, cancel, canvas, overlay };
};

describe("createGraphRenderer", () => {
  // 止めた後はコマを描かない（正常系）
  test("create_graph_renderer_when_destroyed", () => {
    // 準備
    const { frames, cancel, canvas, overlay } = setup();
    const renderer = createGraphRenderer({ canvas, overlay, onPress: vi.fn() });
    const before = frames.length;
    // 実行
    renderer.destroy();
    for (const frame of frames.splice(0)) frame(16);
    // 検証
    expect(before).toBeGreaterThan(0);
    expect(cancel).toHaveBeenCalled();
    expect(frames).toHaveLength(0);
  });

  // 余白を押すと null を渡す（正常系）
  test("create_graph_renderer_when_pressed", () => {
    // 準備
    const { canvas, overlay } = setup();
    const onPress = vi.fn();
    const renderer = createGraphRenderer({ canvas, overlay, onPress });
    // 実行
    canvas.dispatchEvent(new PointerEvent("pointerdown", { clientX: 5, clientY: 5, button: 0, bubbles: true }));
    canvas.dispatchEvent(new PointerEvent("pointerup", { clientX: 5, clientY: 5, button: 0, bubbles: true }));
    // 検証
    expect(onPress).toHaveBeenCalledTimes(1);
    expect(onPress).toHaveBeenCalledWith(null);
    renderer.destroy();
  });
});
