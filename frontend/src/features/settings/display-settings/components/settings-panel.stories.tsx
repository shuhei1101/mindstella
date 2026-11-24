// 表示の設定のストーリー（部品設計『表示の設定.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { SettingsPanel } from "@/features/settings/display-settings/components/settings-panel";
import { KIND_KEYS } from "@/shared/core/records";

const meta = {
  title: "Settings/SettingsPanel",
  component: SettingsPanel,
  args: { visibleKinds: [...KIND_KEYS], defaultKinds: [...KIND_KEYS], counts: { decisions: 12, tasks: 8, research: 3, docs: 5, terms: 9, notes: 4, logs: 20 }, overrides: [], canSave: true, message: null, storageAvailable: true, minimap: true, bodyView: { fold: true }, onKindsChange: fn(), onReset: fn(), onSaveDefault: fn(), onClose: fn(), onMinimapChange: fn(), onBodyViewChange: fn(), focusAfterAdd: "auto", pointerCoarse: false, onFocusAfterAddChange: fn(), singleKeyShortcuts: true, onSingleKeyShortcutsChange: fn() },
  // パネルの中と同じ見出しの順にするため、パネルの見出し「表示の設定」（h2）の下に置く
  decorators: [
    (Story) => (
      <section>
        <h2 className="m-0 text-body font-medium">表示の設定</h2>
        <Story />
      </section>
    ),
  ],
} satisfies Meta<typeof SettingsPanel>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 開いた直後（ワークスペースの既定のまま）。「既定に戻す」と「ワークスペースの既定にする」を出さず、そのことを文言で示す */
export const Default: Story = { args: { overrides: [] } };

/** この端末で変えている。上書きを持つ 4 項目を並べて「既定に戻す」を出し、線で区切った下に「ワークスペースの既定にする」を置く */
export const Overridden: Story = { args: { defaultKinds: ["decisions", "tasks", "research", "docs", "terms", "logs"], overrides: ["表示する種類", "ライト / ダーク", "表の列（調査）", "絞り込み（タスク）"] } };

/** 用語集と会話ログを外した。「すべて」を途中の印にし、`5/7` を出す */
export const SomeKindsHidden: Story = { args: { visibleKinds: ["decisions", "tasks", "research", "docs", "notes"], overrides: ["表示する種類"] } };

/** 既定にした直後。今の選びが既定と同じになり、ボタンの代わりにそのことと保存した知らせを出す */
export const Saved: Story = { args: { visibleKinds: ["decisions", "tasks", "research", "docs", "terms", "notes"], defaultKinds: ["decisions", "tasks", "research", "docs", "terms", "notes"], overrides: ["表示する種類"], message: {"kind": "ok", "text": "ワークスペースの既定にしました（10/05 14:20）。"} } };

/** 他の人が保存した既定が届いた。上書きを持たない項目に新しい既定が当たり、パネルに知らせを残す */
export const DefaultsArrived: Story = { args: { visibleKinds: ["decisions", "tasks", "research", "docs", "terms", "notes"], defaultKinds: ["decisions", "tasks", "research", "docs", "terms", "notes"], message: {"kind": "info", "text": "ワークスペースの既定が変わりました（10/05 14:22）。"} } };

/** 端末の保存領域に書けない。選んだ表示は当てるが、開いている間だけであることを先頭に出す */
export const NoStorage: Story = { args: { storageAvailable: false, visibleKinds: ["decisions", "tasks", "research", "docs", "terms", "notes"], overrides: ["表示する種類"] } };

/** 配る書き出し。表示する種類は変えられ、「ワークスペースの既定にする」は出さない */
export const Export: Story = { args: { canSave: false, visibleKinds: ["decisions", "tasks", "research", "docs", "terms", "notes"], overrides: ["表示する種類"] } };

/** 幅 390px。画面の幅いっぱいに出し、行の高さと押せる的は変えない */
export const Narrow: Story = { args: { visibleKinds: ["decisions", "tasks", "research", "docs", "terms", "logs"], overrides: ["表示する種類"] } };

/** 差分のミニマップだけを表示しないにした。「詳細に表示するもの」のチェックを外し、変えている項目に「差分のミニマップ」と「既定に戻す」を出す。表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「表示する種類は、ワークスペースの既定と同じです。」を出す */
export const MinimapHidden: Story = { args: { minimap: false, overrides: ["差分のミニマップ"] } };

/** 詳細のレビュー中のコメントの並びを古い順にした。変えている項目に「コメントの並び」と「既定に戻す」を出す。表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「表示する種類は、ワークスペースの既定と同じです。」を出す */
export const ReviewOrderOverridden: Story = { args: { overrides: ["コメントの並び"] } };

/** セクションの折りたたみをオフにした。「詳細に表示するもの」のチェックを切り替え、変えている項目に「セクションの折りたたみ」と「既定に戻す」を出す。表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「表示する種類は、ワークスペースの既定と同じです。」を出す */
export const BodyViewOverridden: Story = { args: { bodyView: { fold: false }, overrides: ["セクションの折りたたみ"] } };

/** タッチが主な端末で「レビューに追加した後のフォーカス」が自動。「自動」の下に「この端末では戻しません」を出す */
export const FocusAfterAddCoarse: Story = { args: { focusAfterAdd: "auto", pointerCoarse: true, overrides: [] } };

/** 「レビューに追加した後のフォーカス」を「戻さない」にした。変えている項目に「レビューに追加した後のフォーカス」と「既定に戻す」を出す。表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「表示する種類は、ワークスペースの既定と同じです。」を出す */
export const FocusAfterAddOverridden: Story = { args: { focusAfterAdd: "none", overrides: ["レビューに追加した後のフォーカス"] } };

/** 1 文字のショートカットをオフにした。区画「キーボード」のチェックを外し、変えている項目に「1 文字のショートカット」と「既定に戻す」を出す。表示する種類は既定のままなので、「ワークスペースの既定にする」の代わりに「表示する種類は、ワークスペースの既定と同じです。」を出す */
export const SingleKeyShortcutsOff: Story = { args: { singleKeyShortcuts: false, overrides: ["1 文字のショートカット"] } };
