import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import type { GraphCanvas } from "@/features/graph/graph/components/graph-canvas";
import { useGraphLock } from "@/features/graph/graph/store";
import { readPrefs } from "@/shared/stores/prefs-store";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

// キャンバスは jsdom で描けないため、受け取った props を外から読める差し替えにする
const canvasProps: { current: Parameters<typeof GraphCanvas>[0] | null } = { current: null };
vi.mock("@/features/graph/graph/components/graph-canvas", () => ({
  GraphCanvas: (props: Parameters<typeof GraphCanvas>[0]) => {
    canvasProps.current = props;
    return <canvas id="graph-canvas" aria-label="ネットワーク" />;
  },
}));

/** ロックを外して始め、以後のロックを読めるようにする（store は画面の外にあるため別に描いた部品から読む） */
const watchLock = () => {
  const lock: { current: string | null; set: (id: string | null) => void } = { current: null, set: () => undefined };
  const Probe = () => {
    const [locked, setLocked] = useGraphLock();
    lock.current = locked;
    lock.set = setLocked;
    return null;
  };
  render(<Probe />);
  act(() => {
    lock.set(null);
  });
  return lock;
};

beforeEach(() => {
  // 幅 901px 以上（ロックできる幅）にする
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: query.includes("min-width"), media: query, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  canvasProps.current = null;
});

describe("GraphScreen", () => {
  // キャンバスと見た目のドロップダウンを描く（正常系）
  test("graph_screen", async () => {
    // 実行
    renderRoute("/spa/?tab=graph");
    // 検証
    expect(await screen.findByLabelText("ネットワーク")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "ネットワークの見た目" })).toHaveTextContent("深宇宙");
  });

  // 条件に合う項目が無い（正常系）
  test("graph_screen_when_filtered_empty", async () => {
    // 実行
    renderRoute("/spa/?tab=graph&f.type=%E7%84%A1%E3%81%84%E7%A8%AE%E9%A1%9E");
    // 検証
    expect(await screen.findByText("表示する項目はありません。")).toBeInTheDocument();
  });

  // 見た目を選ぶと端末に残す（正常系）
  test("graph_screen_when_look_selected", async () => {
    // 準備
    const requests: string[] = [];
    server.events.on("request:start", ({ request }) => {
      requests.push(new URL(request.url).pathname);
    });
    renderRoute("/spa/?tab=graph");
    await screen.findByLabelText("ネットワーク");
    const before = requests.filter((path) => path === "/api/records").length;
    // 実行
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "ネットワークの見た目" }), "星図");
    // 検証
    expect(readPrefs().look).toBe("constellation");
    expect(requests.filter((path) => path === "/api/records")).toHaveLength(before);
    server.events.removeAllListeners();
  });

  // 詳細を開いている項目を押すとロックする（正常系）
  test("graph_screen_when_lock_tapped", async () => {
    // 準備
    const lock = watchLock();
    renderRoute("/spa/?tab=graph&id=D-1");
    await screen.findByLabelText("ネットワーク");
    // 実行
    act(() => {
      canvasProps.current?.onPress("D-1");
    });
    // 検証
    await waitFor(() => expect(lock.current).toBe("D-1"));
    expect(new URLSearchParams(window.location.search).get("id")).toBe("D-1");
  });

  // L キーでロックを外す（正常系）
  test("graph_screen_when_lock_key", async () => {
    // 準備
    const lock = watchLock();
    renderRoute("/spa/?tab=graph&id=D-1");
    await screen.findByLabelText("ネットワーク");
    act(() => {
      canvasProps.current?.onPress("D-1");
    });
    await waitFor(() => expect(lock.current).toBe("D-1"));
    // 実行
    await userEvent.keyboard("l");
    // 検証
    await waitFor(() => expect(lock.current).toBeNull());
  });

  // ピン止めしたコメントの一覧を開いたままでも L キーでロックする（正常系）
  test("graph_screen_when_lock_key_pinned_panel", async () => {
    // 準備
    const lock = watchLock();
    renderRoute("/spa/?tab=graph&id=D-1");
    await screen.findByLabelText("ネットワーク");
    const panel = document.createElement("section");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "false");
    document.body.append(panel);
    // 実行
    await userEvent.keyboard("l");
    // 検証
    await waitFor(() => expect(lock.current).toBe("D-1"));
    panel.remove();
  });

  // 入力欄では L キーを受けない（正常系）
  test("graph_screen_when_lock_key_typing", async () => {
    // 準備
    const lock = watchLock();
    renderRoute("/spa/?tab=graph&id=D-1");
    await screen.findByLabelText("ネットワーク");
    const input = document.createElement("input");
    document.body.append(input);
    input.focus();
    // 実行
    await userEvent.keyboard("l");
    // 検証
    expect(lock.current).toBeNull();
    input.remove();
  });
});
