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

  // offline で接続の状態を出す（正常系）
  test("topbar_when_offline", () => {
    // 実行
    render(<Topbar title="話し合い" tabs={[...TABS]} current="overview" theme="light" connection="offline" readAt="2026-10-04T02:21:00+00:00" />);
    // 検証
    expect(screen.getByText(/サーバーにつながりません/)).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "文字起こし中（D-022 へのコメント）。入力欄へ移動" })).toHaveTextContent("文字起こし中");
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
});
