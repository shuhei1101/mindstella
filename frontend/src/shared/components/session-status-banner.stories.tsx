// MindStella のセッションの状態のバーのストーリー（状態ごと）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { SessionStatusBanner } from "@/shared/components/session-status-banner";

/** 再起動に失敗した理由（claude-balancer の標準エラー） */
const REASON = "空いたアカウントがありません（claude-balancer: all accounts are at the usage limit）。";

const meta = {
  title: "Shared/SessionStatusBanner",
  component: SessionStatusBanner,
  args: { status: { kind: "restarting", waiting: 0 }, onRestart: fn(), onClose: fn() },
} satisfies Meta<typeof SessionStatusBanner>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 再起動の途中。回るマーカーと「MindStella のセッションを再起動しています」。送信したコメントは準備ができてから入力する */
export const Restarting: Story = {};

/** 再起動の途中にコメントを 2 件送信した。入力を待っている件数を出す */
export const RestartingWithWaiting: Story = { args: { status: { kind: "restarting", waiting: 2 } } };

/** 再起動に失敗した。理由（`last_error`）と「再起動」のボタンを出す */
export const Failed: Story = { args: { status: { kind: "failed", reason: REASON, retrying: false } } };

/** 「再起動」を押してから起動中に戻るまで。ボタンを押せなくし、回るマーカーと「再起動中」 */
export const Retrying: Story = { args: { status: { kind: "failed", reason: REASON, retrying: true } } };

/** 追加の MCP とプラグインの記録が無い警告（`launch_record_missing`）。閉じるボタンで閉じる */
export const LaunchRecordMissing: Story = { args: { status: { kind: "launch_record_missing" } } };

/** 起動中。何も出さない */
export const Running: Story = { args: { status: { kind: "running" } } };

/** 長い理由。パスや標準エラーの切れ目の無い文字を折り返し、「再起動」のボタンを押し出さない */
export const LongText: Story = {
  args: {
    status: {
      kind: "failed",
      reason:
        "追加のプラグインのフォルダ /home/user/.local/state/mindstella/workspaces/very-long-workspace-name-0123456789abcdef/plugins/mindstella-extra-plugin-with-a-very-long-name/.claude-plugin/plugin.json を読めませんでした。claude-balancer の標準エラー: lease-rejected:account-a(5h=98%),account-b(5h=97%),account-c(weekly=100%),exit-code=-125",
      retrying: false,
    },
  },
};

/** 理由が空。見出しと「再起動」のボタンだけを出す */
export const Empty: Story = { args: { status: { kind: "failed", reason: "", retrying: false } } };

/** 幅 390px。本文を折り返し、「再起動」のボタンを右に残す */
export const Narrow: Story = {
  args: { status: { kind: "failed", reason: REASON, retrying: false } },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
