// 既定の保存の確かめのストーリー（部品設計『既定の保存の確かめ』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 表示する種類の全て */
const ALL_KINDS = new Set(["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]);

/** メモを除いた 6 種類 */
const KINDS_WITHOUT_NOTES = new Set(["decisions", "tasks", "research", "docs", "terms", "logs"]);

const meta = {
  title: "Preview/SettingsSaveConfirm",
  // 呼ぶ側が開くのと同じく、文書に入れて `showModal()` で開く
  render: (args) => {
    const stage = document.createElement("div");
    const dialog = MindmapPreview.settingsConfirm(args);
    stage.append(dialog);
    requestAnimationFrame(() => dialog.showModal());
    return stage;
  },
  args: {
    from: { look: "deep", kinds: ALL_KINDS },
    to: { look: "glow", kinds: ALL_KINDS },
    on: { save: fn(), cancel: fn() },
  },
} satisfies Meta<MindmapPreview.SettingsConfirmProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SettingsConfirmProps>;

/** 2 つの項目を変える。今の既定と保存する値を矢印で並べる。最初のフォーカスは取り消す */
export const BothChanged: Story = {
  args: {
    from: { look: "starlight", kinds: KINDS_WITHOUT_NOTES },
    to: { look: "dust", kinds: ALL_KINDS },
  },
};

/** 表示する種類を変えない。今の値に「変えない」の札を付ける */
export const OneUnchanged: Story = {};

/** 保存している途中。ボタンを押せなくし、保存するボタンに待つ印を出す */
export const Busy: Story = { args: { busy: true } };

/** ワークスペースのフォルダに書き込めず保存できなかった。理由と直し方を出し、もう一度保存できる */
export const ErrorReadOnly: Story = {
  args: {
    error:
      "保存できませんでした。ワークスペースのフォルダに書き込めません（読み取り専用）。フォルダに書き込めるようにしてから、もう一度保存してください。",
  },
};

/** サーバーが止まっていて保存できなかった。コメントを送れなかったときと同じ直し方を出す */
export const ErrorOffline: Story = {
  args: {
    error:
      "保存できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから保存してください。",
  },
};

/** 幅 320px で外した種類が多い。値を折り返す */
export const Narrow: Story = {
  args: { to: { look: "constellation", kinds: new Set(["logs"]) } },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 320px", styles: { width: "320px", height: "720px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
