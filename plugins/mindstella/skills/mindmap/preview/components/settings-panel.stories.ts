// 表示の設定のストーリー（部品設計『表示の設定』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** 表示する種類の全て */
const ALL_KINDS = new Set(["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]);

/** メモを除いた 6 種類 */
const KINDS_WITHOUT_NOTES = new Set(["decisions", "tasks", "research", "docs", "terms", "logs"]);

/** 種類ごとの件数 */
const COUNTS = { decisions: 12, tasks: 8, research: 3, docs: 5, terms: 9, notes: 4, logs: 20 };

const meta = {
  title: "Preview/SettingsPanel",
  // 見ている画面に重ねて左から出すパネルの中に入れて見せる（開いた状態にする）
  render: (args) => {
    const drawer = MindmapPreview.settingsDrawer({ panel: args });
    drawer.classList.add("open");
    return drawer;
  },
  args: {
    look: "deep",
    defaultLook: "deep",
    kinds: ALL_KINDS,
    defaultKinds: ALL_KINDS,
    counts: COUNTS,
    overrides: [],
    canSave: true,
    on: { kinds: fn(), minimap: fn(), bodyView: fn(), reset: fn(), save: fn(), close: fn() },
  },
} satisfies Meta<MindmapPreview.SettingsPanelProps>;

export default meta;

type Story = StoryObj<MindmapPreview.SettingsPanelProps>;

/** 開いた直後（ワークスペースの既定のまま）。「既定に戻す」と「ワークスペースの既定にする」を出さず、そのことを文言で示す */
export const Default: Story = {};

/** この端末で変えている。上書きを持つ 5 項目を並べて「既定に戻す」を出し、線で区切った下に「ワークスペースの既定にする」を置く */
export const Overridden: Story = {
  args: {
    look: "dust",
    defaultLook: "starlight",
    defaultKinds: KINDS_WITHOUT_NOTES,
    overrides: ["ネットワークの見た目", "表示する種類", "ライト / ダーク", "表の列（調査）", "絞り込み（タスク）"],
  },
};

/** 用語集と会話ログを外した。「すべて」を途中の印にし、`5/7` を出す */
export const SomeKindsHidden: Story = {
  args: {
    kinds: new Set(["decisions", "tasks", "research", "docs", "notes"]),
    overrides: ["表示する種類"],
  },
};

/** 既定にした直後。今の選びが既定と同じになり、ボタンの代わりにそのことと保存した知らせを出す */
export const Saved: Story = {
  args: {
    look: "glow",
    defaultLook: "glow",
    overrides: ["ネットワークの見た目"],
    message: { kind: "ok", text: "ワークスペースの既定にしました（10/05 14:20）。" },
  },
};

/** 他の人が保存した既定が届いた。上書きを持たない項目に新しい既定が当たり、パネルに知らせを残す */
export const DefaultsArrived: Story = {
  args: {
    look: "starlight",
    defaultLook: "starlight",
    message: { kind: "info", text: "ワークスペースの既定が変わりました（10/05 14:22）。" },
  },
};

/** 端末の保存領域に書けない。選んだ表示は当てるが、開いている間だけであることを先頭に出す */
export const NoStorage: Story = {
  args: { storageOk: false, look: "glow", overrides: ["ネットワークの見た目"] },
};

/** 配る書き出し。見た目・表示する種類は変えられ、「ワークスペースの既定にする」は出さない */
export const Export: Story = {
  args: { canSave: false, look: "glow", overrides: ["ネットワークの見た目"] },
};

/** 幅 390px。画面の幅いっぱいに出し、行の高さと押せる的は変えない */
export const Narrow: Story = {
  args: { look: "dust", defaultLook: "starlight", overrides: ["ネットワークの見た目", "表示する種類"] },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** 差分のミニマップだけを表示しないにした。「詳細に表示するもの」のチェックを外し、変えている項目に「差分のミニマップ」と「既定に戻す」を出す。見た目と表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「見た目と表示する種類は、ワークスペースの既定と同じです。」を出す */
export const MinimapHidden: Story = {
  args: { minimap: false, overrides: ["差分のミニマップ"] },
};

/** 詳細で本文の差分を左右に並べるを選んだ。変えている項目に「本文の差分の並べ方」と「既定に戻す」を出す。見た目と表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「見た目と表示する種類は、ワークスペースの既定と同じです。」を出す */
export const BodyDiffLayoutOverridden: Story = {
  args: { overrides: ["本文の差分の並べ方"] },
};

/** 表のしま模様をオンにし、セクションの折りたたみをオフにした。「詳細に表示するもの」の 2 つのチェックを切り替え、変えている項目に「表のしま模様」「セクションの折りたたみ」と「既定に戻す」を出す。見た目と表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「見た目と表示する種類は、ワークスペースの既定と同じです。」を出す */
export const BodyViewOverridden: Story = {
  args: {
    bodyView: { pin: true, head: true, stripes: true, fold: false },
    overrides: ["表のしま模様", "セクションの折りたたみ"],
  },
};
