import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, test, vi } from "vitest";

import { connectEvents } from "@/shared/adapters/events-client";
import { resetEmbeddedDataForTest } from "@/shared/core/embedded";
import { useRefreshHoldStore } from "@/shared/stores/refresh-hold-store";
import { resetVoiceStore } from "@/shared/stores/voice-store";
import { FakeEventSource } from "@/testing/fake-event-source";
import { installFakeMedia, removeFakeMedia } from "@/testing/fake-media";
import { installFakeWakeLock, removeFakeWakeLock } from "@/testing/fake-wake-lock";
import { stubRecords } from "@/testing/msw/fixtures";
import { RECORDS } from "@/testing/msw/handlers";
import { server } from "@/testing/msw/server";
import { renderRoute } from "@/testing/render";

afterEach(() => {
  document.body.querySelector("#mindmap-data")?.remove();
  resetEmbeddedDataForTest();
  useRefreshHoldStore.setState({ focused: false, pending: false, heldElement: null, anchor: null });
  resetVoiceStore();
  removeFakeMedia();
  removeFakeWakeLock();
  vi.unstubAllGlobals();
});

/** 音声入力を使える状態にする */
const enableVoice = (): void => {
  installFakeMedia();
  installFakeWakeLock();
  server.use(http.get("/api/transcription", () => HttpResponse.json({ available: true, reason: null, detail: null, presets: [], action: "review", preset: null })));
};

describe("PreviewShell", () => {
  // tab の画面を描く（正常系）
  test("preview_shell", async () => {
    // 実行
    renderRoute("/?tab=tasks");
    // 検証
    expect(await screen.findByRole("group", { name: "表示形式" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "T-1の題" })).toBeInTheDocument();
  });

  // id で詳細パネルを重ねる（正常系）
  test("preview_shell_when_item", async () => {
    // 実行
    renderRoute("/?tab=tasks&id=T-1");
    // 検証
    expect(await screen.findByRole("complementary", { name: /詳細/ })).toBeInTheDocument();
  });

  // full で全画面にする（正常系）
  test("preview_shell_when_full", async () => {
    // 実行
    renderRoute("/?tab=tasks&id=T-1&full=1");
    // 検証
    expect(await screen.findByRole("dialog", { name: /T-1の題/ })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /詳細/ })).not.toBeInTheDocument();
  });

  // 設定の画面を開く（正常系）
  test("preview_shell_when_settings", async () => {
    // 実行
    renderRoute("/?tab=settings");
    // 検証
    expect(await screen.findByRole("heading", { name: "設定", level: 1 })).toBeInTheDocument();
    expect(screen.queryByRole("link", { current: "page" })).not.toBeInTheDocument();
  });

  // 記録に合わない値を外す（正常系）
  test("preview_shell_when_search_mismatched", async () => {
    // 実行
    renderRoute("/?tab=tasks&view=cards&id=T-99");
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=tasks"));
  });
  // コメントの一覧を開く（正常系）
  test("preview_shell_when_comments", async () => {
    // 準備
    renderRoute("/?tab=tasks");
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /コメント/ }));
    // 検証
    expect(await screen.findByRole("dialog", { name: "コメント" })).toBeInTheDocument();
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("panel")).toBe("comments"));
  });

  // 表示の設定を開く（正常系）
  test("preview_shell_when_display", async () => {
    // 実行
    renderRoute("/?panel=display");
    // 検証
    expect(await screen.findByRole("dialog", { name: "表示の設定" })).toBeInTheDocument();
  });

  // トップバーの高さを CSS 変数に書く（正常系）
  test("preview_shell_when_topbar_height", async () => {
    // 準備（観測している要素ごとに、知らせる関数を控える）
    const observers: { callback: ResizeObserverCallback; targets: Element[] }[] = [];
    class FakeResizeObserver {
      private readonly entry: { callback: ResizeObserverCallback; targets: Element[] };
      constructor(callback: ResizeObserverCallback) {
        this.entry = { callback, targets: [] };
        observers.push(this.entry);
      }
      observe(target: Element): void {
        this.entry.targets.push(target);
      }
      unobserve(): void {}
      disconnect(): void {
        this.entry.targets = [];
      }
    }
    vi.stubGlobal("ResizeObserver", FakeResizeObserver);
    // トップバーを包む要素の高さを変えて知らせる
    const resize = (height: number): void => {
      const banner = screen.getByRole("banner");
      for (const observer of observers) {
        const targets = observer.targets.filter((target) => target.contains(banner));
        if (targets.length === 0) continue;
        const entries = targets.map((target) => {
          vi.spyOn(target, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 1280, height));
          return { target, contentRect: new DOMRect(0, 0, 1280, height), borderBoxSize: [{ blockSize: height, inlineSize: 1280 }], contentBoxSize: [{ blockSize: height, inlineSize: 1280 }], devicePixelContentBoxSize: [] };
        });
        act(() => {
          observer.callback(entries, observer as unknown as ResizeObserver);
        });
      }
    };
    const topbarHeight = (): string => document.documentElement.style.getPropertyValue("--topbar-height");
    const { unmount } = renderRoute("/?tab=tasks");
    await screen.findByRole("group", { name: "表示形式" });
    // 実行
    resize(52);
    // 検証
    await waitFor(() => expect(topbarHeight()).toBe("52px"));
    // 実行
    resize(96);
    // 検証
    await waitFor(() => expect(topbarHeight()).toBe("96px"));
    // 実行
    unmount();
    // 検証
    expect(topbarHeight()).toBe("");
  });

  // 削除したネットワーク・検討事項のマップを指す URL は概要・ボードで開く（正常系）
  test.each([
    { name: "graph", url: "/?tab=graph", search: "" },
    { name: "map", url: "/?tab=decisions&view=map", search: "?tab=decisions" },
  ])("preview_shell_when_removed_view ($name)", async ({ url, search }) => {
    // 実行
    renderRoute(url);
    // 検証
    await waitFor(() => expect(window.location.search).toBe(search));
    expect(screen.queryByRole("link", { name: /ネットワーク/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "マップ" })).not.toBeInTheDocument();
  });

  // 検索の結果から項目を開く（正常系）
  test("preview_shell_when_search", async () => {
    // 準備
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "", until_seq: 1, added: ["D-1"], changed: [], removed: [] }], pending: { added: [], changed: [] } } });
    renderRoute("/?tab=tasks&search=1&q=D-1%E3%81%AE%E9%A1%8C&diff=V-1");
    const before = window.history.length;
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /D-1の題/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=decisions&id=D-1&diff=V-1"));
    expect(screen.queryByRole("dialog", { name: /検索/ })).not.toBeInTheDocument();
    expect(window.history.length).toBe(before + 1);
  });

  // 全体の検索の絞り込みの候補を選ぶ（正常系）
  test("preview_shell_when_search_filter_candidate", async () => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "資料 1", status: "確認中", tags: [{ name: "画面" }] }, { id: "A-2", title: "資料 2", status: "確認中", tags: [{ name: "画面" }, { name: "廃止" }] }] });
    renderRoute("/?tab=docs&search=1&q=%E5%BB%83");
    const before = window.history.length;
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /タグ = 廃止/ }));
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("f.tags")).toBe("廃止"));
    expect(new URLSearchParams(window.location.search).get("search")).toBeNull();
    expect(new URLSearchParams(window.location.search).get("q")).toBeNull();
    expect(screen.queryByRole("dialog", { name: /検索/ })).not.toBeInTheDocument();
    expect(window.history.length).toBe(before + 1);
  });

  // 同じ画面の項目は履歴に積まずに詳細パネルを開く（正常系）
  test("preview_shell_when_search_same_tab", async () => {
    // 準備
    renderRoute("/?tab=decisions&view=table&search=1&q=D-1%E3%81%AE%E9%A1%8C");
    const before = window.history.length;
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /D-1の題/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?tab=decisions&id=D-1"));
    expect(window.history.length).toBe(before);
  });

  // 表示しない種類の項目は概要で開く（正常系）
  test("preview_shell_when_search_hidden_kind", async () => {
    // 準備
    stubRecords({ settings: { ...RECORDS.settings, display: { visible_kinds: ["decisions", "tasks"] } }, notes: [{ id: "N-1", title: "N-1のメモ" }] });
    renderRoute("/?tab=tasks&search=1&q=N-1%E3%81%AE%E3%83%A1%E3%83%A2");
    // 実行
    await userEvent.click(await screen.findByRole("option", { name: /N-1のメモ/ }));
    // 検証
    await waitFor(() => expect(window.location.search).toBe("?id=N-1"));
    expect(await screen.findByRole("complementary", { name: /詳細/ })).toBeInTheDocument();
  });

  // 録音中にほかの画面へ移り、トップバーから録音中の入力欄へ戻る（正常系）
  test("preview_shell_when_voice", async () => {
    // 準備
    enableVoice();
    renderRoute("/?tab=tasks&id=T-1");
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    // 実行
    await userEvent.click(screen.getByRole("button", { name: /^コメント（/ }));
    expect(await screen.findByRole("dialog", { name: "コメント" })).toBeInTheDocument();
    const voice = screen.getByRole("button", { name: /^音声入力中（T-1 へのコメント）/ });
    await userEvent.click(voice);
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("id")).toBe("T-1"));
    expect(new URLSearchParams(window.location.search).get("panel")).toBeNull();
    await waitFor(() => expect(screen.getByRole("button", { name: "文字起こし" })).toHaveFocus());
  });

  // 録音中に行き先の項目が無くなったら録音を捨てて帯を出す（正常系）
  test("preview_shell_when_voice_target_removed", async () => {
    // 準備
    enableVoice();
    const view = renderRoute("/?tab=tasks&id=T-1");
    await userEvent.click(await screen.findByRole("button", { name: "音声で入力" }));
    await screen.findByRole("button", { name: /^音声入力中（T-1 へのコメント）/ });
    stubRecords({ tasks: [] });
    // 実行
    await act(() => view.queryClient.invalidateQueries());
    // 検証
    expect(await screen.findByText("T-1 が削除されたため、録音を破棄しました。")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^音声入力中/ })).toBeNull();
  });
  // 修正の入力で録音中にトップバーから戻ると修正の入力のまま開き、コメントが無くなって読み直すと録音を捨てる（正常系）
  test("preview_shell_when_review_voice", async () => {
    // 準備
    enableVoice();
    const items = [{ id: "C-1", thread: null, target: "T-1", target_title: "T-1の題", loc: null, body: "確認: ", created: "2026-11-01T00:01:00+00:00" }];
    server.use(http.get("/api/comments", () => HttpResponse.json({ items, drafts: [] })));
    const view = renderRoute("/?panel=comments&review=1");
    await userEvent.click(await screen.findByRole("button", { name: "T-1 へのコメントを修正" }));
    const edit = (await screen.findByRole("textbox", { name: "T-1 へのコメントの本文" })).closest("form");
    if (edit === null) throw new Error("修正の入力が無い");
    await userEvent.click(within(edit).getByRole("button", { name: "音声で入力" }));
    await userEvent.click(screen.getByRole("button", { name: "戻る" }));
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /^音声入力中（T-1 へのコメントの修正）/ }));
    // 検証
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("review")).toBe("1"));
    await waitFor(() => expect(screen.getByRole("button", { name: "文字起こし" })).toHaveFocus());
    // 準備
    server.use(http.get("/api/comments", () => HttpResponse.json({ items: [], drafts: [] })));
    // 実行
    await act(() => view.queryClient.invalidateQueries());
    // 検証
    expect(await screen.findByText("C-1 が削除されたため、録音を破棄しました。")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^音声入力中/ })).toBeNull();
  });

  // 入力中に書き換わったら保留し、離れたら反映する（正常系）
  test("preview_shell_when_records_changed_while_typing", async () => {
    // 準備
    const view = renderRoute("/?tab=tasks&id=T-1");
    const close = connectEvents(view.queryClient);
    const input = await screen.findByRole("textbox", { name: /T-1 へのコメント/ });
    await userEvent.type(input, "途中まで");
    stubRecords({ tasks: [...RECORDS.tasks, { id: "T-2", title: "T-2の題", status: "未着手" }] });
    // 実行
    act(() => FakeEventSource.last?.emit("changed"));
    // 検証
    await waitFor(() => expect(FakeEventSource.last).not.toBeNull());
    // 更新のボタンのツールチップ（読み上げから外した要素）の文言は帯に数えない
    expect(screen.queryByText(/更新があります/, { ignore: "[aria-hidden='true'] *" })).toBeNull();
    expect(screen.queryByRole("button", { name: "T-2の題" })).toBeNull();
    // 実行
    await userEvent.click(screen.getByRole("group", { name: "表示形式" }));
    // 検証
    expect(await screen.findByRole("button", { name: "T-2の題" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /T-1 へのコメント/ })).toHaveValue("途中まで");
    close();
  });

  // 読み直しで入力欄を作り直さない（正常系）
  test("preview_shell_when_records_changed", async () => {
    // 準備
    const view = renderRoute("/?tab=tasks&id=T-1");
    const close = connectEvents(view.queryClient);
    const input = await screen.findByRole("textbox", { name: /T-1 へのコメント/ });
    await userEvent.type(input, "途中まで");
    await userEvent.click(screen.getByRole("group", { name: "表示形式" }));
    stubRecords({ tasks: [...RECORDS.tasks, { id: "T-2", title: "T-2の題", status: "未着手" }] });
    // 実行
    act(() => FakeEventSource.last?.emit("changed"));
    // 検証
    expect(await screen.findByRole("button", { name: "T-2の題" })).toBeInTheDocument();
    const after = screen.getByRole("textbox", { name: /T-1 へのコメント/ });
    expect(after).toBe(input);
    expect(after).toHaveValue("途中まで");
    close();
  });

  // 配る書き出しは書き込む操作を出さない（正常系）
  test("preview_shell_when_embedded", async () => {
    // 準備
    const data = document.createElement("script");
    data.type = "application/json";
    data.id = "mindmap-data";
    data.textContent = JSON.stringify(RECORDS);
    document.body.append(data);
    // 実行
    renderRoute("/x/export.html#/?tab=tasks&id=T-1&panel=display");
    // 検証
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    expect(await screen.findByText("表示する種類")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^コメント/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^保存待ち/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "タスクの項目を追加" })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "編集する" })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: /確認済み/ })).not.toBeInTheDocument();
    expect(within(panel).queryByRole("textbox")).not.toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "T-1 のコメントの一覧を開く" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ワークスペースの既定にする" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "設定を編集する" })).not.toBeInTheDocument();
  });
  // コメントの一覧から開いた詳細パネルだけをグレーアウトの上に出す（正常系）
  test("preview_shell_when_detail_from_comments", async () => {
    // 準備
    window.innerWidth = 1440;
    stubRecords({ tasks: [{ id: "T-1", title: "T-1の題", status: "未着手" }] });
    const thread = { id: "TH-1", status: "open", summary: "T-1 の相談", tags: [], target: "T-1", target_title: "T-1の題", loc: null, events: [], posts: [{ id: "TH-1-1", author: "ai", body: "質問", created: "2026-11-01T00:00:00+00:00", seen: true }] };
    server.use(http.get("*/api/threads", () => HttpResponse.json({ threads: [thread] })));
    renderRoute("/?tab=tasks&panel=comments&thread=TH-1");
    const comments = await screen.findByRole("dialog", { name: "コメント" });
    // 実行
    await userEvent.click(await within(comments).findByRole("button", { name: /T-1の題/ }));
    // 検証
    const detail = await screen.findByRole("complementary", { name: /詳細/ });
    expect(detail).toHaveAttribute("data-raised");
    expect(screen.getByRole("dialog", { name: "コメント" })).not.toHaveAttribute("aria-modal", "true");
  });

  // 先に開いていた詳細パネルは、トップバーからコメントの一覧を開いても上に出さない（正常系）
  test("preview_shell_when_detail_before_comments", async () => {
    // 準備
    window.innerWidth = 1440;
    stubRecords({ tasks: [{ id: "T-1", title: "T-1の題", status: "未着手" }] });
    renderRoute("/?tab=tasks&id=T-1");
    const detail = await screen.findByRole("complementary", { name: /詳細/ });
    // 実行
    await userEvent.click(await screen.findByRole("button", { name: /^コメント（/ }));
    // 検証
    expect(await screen.findByRole("dialog", { name: "コメント" })).toHaveAttribute("aria-modal", "true");
    expect(detail).not.toHaveAttribute("data-raised");
  });

  // 差分の表示の間、変更を持つ種類のタブにだけ点を付ける（正常系）
  test("preview_shell_when_tab_marked", async () => {
    // 準備
    const marker = "新規・変更・削除した項目があります";
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: ["D-1"] }], pending: { added: [], changed: [] } } });
    const view = renderRoute("/?tab=decisions&diff=V-1");
    // 検証
    await waitFor(() => expect(screen.getByRole("link", { name: /検討事項/ })).toHaveTextContent(marker));
    expect(screen.getByRole("link", { name: /概要/ })).not.toHaveTextContent(marker);
    expect(screen.getByRole("link", { name: /タスク/ })).not.toHaveTextContent(marker);
    // 実行（diff を外して開き直す）
    view.unmount();
    renderRoute("/?tab=decisions");
    // 検証
    await screen.findByRole("link", { name: /検討事項/ });
    expect(screen.getByRole("link", { name: /検討事項/ })).not.toHaveTextContent(marker);
  });

  // 未読のまとまりの件数をトップバーに出し、書き換えの通知で増えたまとまりを加える（正常系）
  test("preview_shell_when_history_unread", async () => {
    // 準備
    localStorage.removeItem("mindmap-read-changes");
    const set = (id: string, seq: number) => ({ id, at: `2026-11-0${String(seq)}T00:00:00+00:00`, summary: `${String(seq)} 回目`, until_seq: seq, added: [], changed: ["D-1"] });
    stubRecords({ changes: { last_seq: 2, sets: [set("V-2", 2), set("V-1", 1)], pending: { added: [], changed: [] } } });
    const view = renderRoute("/?tab=decisions");
    const close = connectEvents(view.queryClient);
    // 検証
    expect(await screen.findByRole("button", { name: "変更履歴（未読 2 件）" })).toBeInTheDocument();
    // 実行
    stubRecords({ changes: { last_seq: 3, sets: [set("V-3", 3), set("V-2", 2), set("V-1", 1)], pending: { added: [], changed: [] } } });
    act(() => FakeEventSource.last?.emit("changed"));
    // 検証
    expect(await screen.findByRole("button", { name: "変更履歴（未読 3 件）" })).toBeInTheDocument();
    close();
  });

  // 記録に無いまとまりを既読から削除する（正常系）
  test("preview_shell_when_read_pruned", async () => {
    // 準備
    localStorage.setItem("mindmap-read-changes", JSON.stringify({ state: { read: { "": ["V-1", "V-9"] } }, version: 0 }));
    stubRecords({ changes: { last_seq: 1, sets: [{ id: "V-1", at: "2026-11-01T00:00:00+00:00", summary: "1 回目", until_seq: 1, added: [], changed: ["D-1"] }], pending: { added: [], changed: [] } } });
    // 実行
    renderRoute("/?tab=decisions");
    // 検証
    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem("mindmap-read-changes") ?? "{}") as { state?: { read?: Record<string, string[]> } };
      expect(Object.values(stored.state?.read ?? {})).toEqual([["V-1"]]);
    });
  });

  // 外枠をビューポートの高さに収め、外枠ではスクロールさせない（正常系）
  test("preview_shell_when_page_height", async () => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "A-1の題", status: "下書き", body: "docs/A-1.md" }], bodies: { "docs/A-1.md": "長い本文の行\n".repeat(200) } });
    // 実行
    renderRoute("/?tab=docs&id=A-1");
    await screen.findByRole("complementary", { name: /詳細/ });
    // 検証
    const shell = document.querySelector(".h-dvh");
    expect(shell).not.toBeNull();
    expect(shell).toHaveClass("overflow-hidden");
    expect(screen.getByRole("region", { name: "詳細の本文" })).toHaveClass("overflow-y-auto");
  });
});
