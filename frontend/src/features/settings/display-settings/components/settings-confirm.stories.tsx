// 既定の保存の確かめのストーリー（部品設計『既定の保存の確かめ.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { SettingsConfirm } from "@/features/settings/display-settings/components/settings-confirm";
import { KIND_KEYS } from "@/shared/core/records";

const meta = {
  title: "Settings/SettingsConfirm",
  component: SettingsConfirm,
  args: { from: { visibleKinds: KIND_KEYS.filter((kind) => kind !== "notes") }, to: { visibleKinds: [...KIND_KEYS] }, busy: false, error: null, onSave: fn(), onCancel: fn() },
} satisfies Meta<typeof SettingsConfirm>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 表示する種類を変える。今の既定と保存する値を矢印で並べる。最初のフォーカスは取り消す */
export const KindsChanged: Story = { args: { from: {"visibleKinds": ["decisions", "tasks", "research", "docs", "terms", "logs"]}, to: {"visibleKinds": ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]} } };

/** 保存している途中。ボタンを押せなくし、保存するボタンに待つ印を出す */
export const Busy: Story = { args: { busy: true } };

/** ワークスペースのフォルダに書き込めず保存できなかった。理由と直し方を出し、もう一度保存できる */
export const ErrorReadOnly: Story = { args: { error: "保存できませんでした。ワークスペースのフォルダに書き込めません（読み取り専用）。フォルダに書き込めるようにしてから、もう一度保存してください。" } };

/** サーバーが止まっていて保存できなかった。コメントを送れなかったときと同じ直し方を出す */
export const ErrorOffline: Story = { args: { error: "保存できませんでした。サーバーが止まっています。起動スクリプトで再起動し、示された新しい URL で開いてから保存してください。" } };

/** 幅 320pxで外した種類が多い。値を折り返す */
export const Narrow: Story = { args: { to: {"visibleKinds": ["logs"]} } };
