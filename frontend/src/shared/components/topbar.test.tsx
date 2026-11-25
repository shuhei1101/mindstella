import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { Topbar } from "@/shared/components/topbar";

const TABS = [
  { key: "overview", label: "概要", icon: "home" },
  { key: "decisions", label: "検討事項", icon: "decision", count: 2 },
] as const;

describe("Topbar", () => {
  // タブを押すと onNavigate（正常系）
  test("topbar_when_navigate", async () => {
    // 準備
    const onNavigate = vi.fn();
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" onNavigate={onNavigate} />);
    // 実行
    await userEvent.click(screen.getByRole("link", { name: /検討事項/ }));
    // 検証
    expect(onNavigate).toHaveBeenCalledTimes(1);
    expect(onNavigate).toHaveBeenCalledWith("decisions");
  });

  // 差分の表示中は変更履歴のボタンに点と × だけを出す（正常系）
  test("topbar_when_diff_point", async () => {
    // 準備
    const onClearDiff = vi.fn();
    const { rerender } = render(
      <Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" diffPoint={{ name: "前回開いてから", sub: "10/04 13:05 より後" }} onOpenHistory={vi.fn()} onClearDiff={onClearDiff} />,
    );
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "差分の表示をやめる" }));
    // 検証
    expect(screen.getByRole("button", { name: "変更履歴（過去の差分を表示中）" })).toBeInTheDocument();
    expect(screen.queryByText(/前回開いてから/)).toBeNull();
    expect(screen.queryByText(/10\/04 13:05/)).toBeNull();
    expect(onClearDiff).toHaveBeenCalledTimes(1);
    // 差分を出していないときは × が無い
    rerender(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" diffPoint={null} onOpenHistory={vi.fn()} onClearDiff={onClearDiff} />);
    expect(screen.getByRole("button", { name: "変更履歴" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "差分の表示をやめる" })).toBeNull();
  });

  // offline で接続の状態を出す（正常系）
  test("topbar_when_offline", () => {
    // 実行
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" connection="offline" readAt="2026-10-04T02:21:00+00:00" />);
    // 検証
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("サーバーにつながりません（10/04 11:21 に読んだ記録）");
    expect(status).not.toHaveAttribute("title");
  });

  // 100 件以上は 99+（正常系）
  test("topbar_when_many_comments", () => {
    // 実行
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" comments commentCount={120} />);
    // 検証
    const button = screen.getByRole("button", { name: /120/ });
    expect(button).toHaveTextContent("99+");
  });

  // 音声入力中の表示と知らせの帯（正常系）
  test("topbar_when_voice", async () => {
    // 準備
    const onOpenVoice = vi.fn();
    const onDismissVoiceNotice = vi.fn();
    const { rerender } = render(
      <Topbar
        title="話し合い"
        tabs={[...TABS]}
        current="overview"
        theme="light"
        comments
        voice={{ state: "recording", label: "D-022 へのコメント", elapsed: 12 }}
        onOpenVoice={onOpenVoice}
        onDismissVoiceNotice={onDismissVoiceNotice}
      />,
    );
    // 実行
    const voice = screen.getByRole("button", { name: "音声入力中（D-022 へのコメント）。録音中の入力欄へ移動" });
    await userEvent.click(voice);
    // 検証
    expect(voice).toHaveTextContent("0:12");
    expect(voice.compareDocumentPosition(screen.getByRole("button", { name: /コメント（/ })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(onOpenVoice).toHaveBeenCalledTimes(1);
    rerender(
      <Topbar
        title="話し合い"
        tabs={[...TABS]}
        current="overview"
        theme="light"
        comments
        voice={{ state: "transcribing", label: "D-022 へのコメント", elapsed: 0 }}
        onOpenVoice={onOpenVoice}
        onDismissVoiceNotice={onDismissVoiceNotice}
      />,
    );
    expect(screen.getByRole("button", { name: "文字起こし中（D-022 へのコメント）。入力欄へ移動" })).not.toHaveTextContent("文字起こし中");
    rerender(
      <Topbar
        title="話し合い"
        tabs={[...TABS]}
        current="overview"
        theme="light"
        comments
        voiceNotice={{ kind: "failed", text: "D-022 へのコメントをレビュー中に追加できませんでした。文字起こしの結果は入力欄に残しています。" }}
        onOpenVoice={onOpenVoice}
        onDismissVoiceNotice={onDismissVoiceNotice}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("D-022 へのコメントをレビュー中に追加できませんでした。");
    await userEvent.click(screen.getByRole("button", { name: "入力欄を開く" }));
    await userEvent.click(screen.getByRole("button", { name: "閉じる" }));
    expect(onOpenVoice).toHaveBeenCalledTimes(2);
    expect(onDismissVoiceNotice).toHaveBeenCalledTimes(1);
  });

  // 更新のボタンを押すと onRefresh、保留中は点と「更新があります」（正常系）
  test("topbar_when_refresh", async () => {
    // 準備
    const onRefresh = vi.fn();
    const { rerender } = render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" onRefresh={onRefresh} />);
    // 実行
    await userEvent.click(screen.getByRole("button", { name: "最新の記録を読み込む" }));
    // 検証
    expect(onRefresh).toHaveBeenCalledTimes(1);
    rerender(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" onRefresh={onRefresh} stale />);
    expect(screen.getByRole("button", { name: "更新があります。最新の記録を読み込む" })).toBeInTheDocument();
    rerender(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" onRefresh={onRefresh} refreshing />);
    const busy = screen.getByRole("button", { name: "最新の記録を読み込む" });
    expect(busy).toHaveAttribute("aria-busy", "true");
    expect(busy).toBeDisabled();
    rerender(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" />);
    expect(screen.queryByRole("button", { name: /最新の記録を読み込む/ })).toBeNull();
  });

  // ボタンは名前を文字で出さず、ツールチップと読み上げに持つ（正常系）
  test("topbar_when_icon_only", async () => {
    // 準備
    const { container } = render(
      <Topbar
        title="話し合い"
        tabs={[...TABS]}
        current="decisions"
        theme="light"
        comments
        commentCount={3}
        filter
        onToggleFilter={vi.fn()}
        pending
        pendingCount={4}
        onTogglePending={vi.fn()}
        onToggleSettings={vi.fn()}
      />,
    );
    // 実行
    screen.getByRole("button", { name: "表示の設定" }).focus();
    await userEvent.keyboard("{Escape}");
    // 検証
    for (const name of ["表示の設定", "絞り込み", "保存待ち（4 件）", "コメント（レビュー中 3 件）"]) {
      const button = screen.getByRole("button", { name });
      expect(button).not.toHaveTextContent(name.replace(/（.*/, ""));
    }
    for (const label of ["表示の設定", "絞り込み", "保存待ち", "コメント"]) {
      const tips = screen.getAllByText(label, { selector: "[aria-hidden='true'] *" });
      expect(tips.length).toBeGreaterThan(0);
    }
    // 話し合いの題名の全文（部品設計の引数 title）を除き、状態の表示とボタンは title 属性を持たない
    expect(container.querySelectorAll("button[title], [role='status'][title], button [title]")).toHaveLength(0);
    expect(container.querySelector("[data-tipsoff]")).not.toBeNull();
  });

  // 重なった ID の通知を出す（正常系）
  test("topbar_when_duplicate_ids", () => {
    // 実行
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" duplicateIds={[{ id: "D-12", kind: "検討事項" }]} />);
    // 検証
    expect(screen.getByRole("alert")).toHaveTextContent("同じ ID の項目が 2 件あります");
    expect(screen.getByRole("link", { name: "D-12" })).toBeInTheDocument();
  });
});
