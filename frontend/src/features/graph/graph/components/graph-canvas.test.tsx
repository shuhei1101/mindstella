import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { GraphCanvas } from "@/features/graph/graph/components/graph-canvas";
import { createGraphRenderer, type GraphRenderer } from "@/features/graph/graph/graph-renderer";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { useThemeStore } from "@/shared/stores/theme-store";

vi.mock("@/features/graph/graph/graph-renderer", () => ({ createGraphRenderer: vi.fn() }));

const empty = { decisions: [], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { next: [] } };
const indexWith = (title: string) => buildIndex({ ...empty, decisions: [{ id: "D-1", title }] } as unknown as MindmapData);
const graph = { nodes: [{ id: "D-1", kind: "decisions" as const }], links: [] };

let renderer: { [K in keyof GraphRenderer]: ReturnType<typeof vi.fn> };

beforeEach(() => {
  renderer = { setGraph: vi.fn(), setLook: vi.fn(), setTheme: vi.fn(), setFocus: vi.fn(), setComments: vi.fn(), shake: vi.fn(), destroy: vi.fn() };
  vi.mocked(createGraphRenderer).mockReturnValue(renderer as unknown as GraphRenderer);
  useThemeStore.getState().setTheme("light");
});

afterEach(() => {
  vi.mocked(createGraphRenderer).mockReset();
});

const props = (patch: Partial<Parameters<typeof GraphCanvas>[0]> = {}) => ({
  graph, index: indexWith("前提"), look: "deep" as const, selectedId: null, lockedId: null, comments: {}, shakeSignal: 0, onPress: vi.fn(), ...patch,
});

describe("GraphCanvas", () => {
  // マウントで描画を始め、アンマウントで止める（正常系）
  test("graph_canvas", () => {
    // 実行
    const view = render(<GraphCanvas {...props()} />);
    view.unmount();
    // 検証
    expect(createGraphRenderer).toHaveBeenCalledTimes(1);
    expect(renderer.destroy).toHaveBeenCalledTimes(1);
  });

  // 見た目の変更は作り直さない（正常系）
  test("graph_canvas_when_look_changed", () => {
    // 準備
    const first = props();
    const view = render(<GraphCanvas {...first} />);
    // 実行
    view.rerender(<GraphCanvas {...first} look="dust" />);
    // 検証
    expect(renderer.setLook).toHaveBeenLastCalledWith("dust");
    expect(renderer.setGraph).toHaveBeenCalledTimes(1);
  });

  // ライト / ダークの変更は作り直さない（正常系）
  test("graph_canvas_when_theme_changed", () => {
    // 準備
    render(<GraphCanvas {...props()} />);
    // 実行
    act(() => {
      useThemeStore.getState().setTheme("dark");
    });
    // 検証
    expect(renderer.setTheme).toHaveBeenLastCalledWith("dark");
    expect(renderer.setGraph).toHaveBeenCalledTimes(1);
  });

  // 記録が変わると作り直す（正常系）
  test("graph_canvas_when_index_changed", () => {
    // 準備
    const first = props();
    const view = render(<GraphCanvas {...first} />);
    const next = indexWith("前提（改）");
    // 実行
    view.rerender(<GraphCanvas {...first} index={next} />);
    // 検証
    expect(renderer.setGraph).toHaveBeenCalledTimes(2);
    expect(renderer.setGraph).toHaveBeenLastCalledWith({ graph, index: next });
  });
});
