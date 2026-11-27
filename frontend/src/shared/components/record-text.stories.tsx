// 記録の文字の部品のストーリー（モック）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { fn, userEvent } from "storybook/test";

import { RecordText, type RecordTextProps } from "@/shared/components/record-text";
import type { LookupRecordId, RecordIdTarget } from "@/shared/core/record-ids";

/** 見本の記録にある項目・スレッド。D-99 は記録に無い */
const TARGETS: Record<string, RecordIdTarget> = {
  "D-1": { id: "D-1", kind: "item", title: "保存先の決め方", kindLabel: "検討事項", status: "未決定" },
  "D-2": { id: "D-2", kind: "item", title: "D-1 の見直し", kindLabel: "検討事項", status: "決定済み" },
  "TH-1": { id: "TH-1", kind: "thread", title: "保存先の候補", kindLabel: "スレッド", status: "オープン" },
};

const lookup: LookupRecordId = (id) => TARGETS[id] ?? null;

/** 見出しのタイトルに描き、押して開いた ID を下に並べて出す（指で押したストーリーで、1 回で開いたかを確かめる） */
const OpenedIds = (args: RecordTextProps) => {
  const [opened, setOpened] = useState<string[]>([]);
  return (
    <>
      <h2 className="m-0 text-h2 font-semibold">
        <RecordText
          {...args}
          onOpen={(id) => {
            args.onOpen?.(id);
            setOpened((ids) => [...ids, id]);
          }}
        />
      </h2>
      <output data-part="opened">{opened.join(",")}</output>
    </>
  );
};

const meta = {
  title: "Shared/RecordText",
  component: RecordText,
  args: { text: "D-1 の比較（TH-1 の続き、D-99 は除く）", mode: "link", lookup, onOpen: fn() },
} satisfies Meta<typeof RecordText>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 詳細パネルの見出しのタイトル。記録にある D-1・TH-1 をリンクにし、記録に無い D-99 は文字のまま */
export const HeadingLinks: Story = {
  render: (args) => (
    <h2 className="m-0 text-h2 font-semibold">
      <RecordText {...args} />
    </h2>
  ),
};

/** 詳細パネルの「関連する項目」の行。ID のボタンの外側のタイトルの中の D-1 をリンクにする */
export const RelatedTitleLinks: Story = {
  args: { text: "D-1 の見直し" },
  render: (args) => (
    <ul className="m-0 flex list-none flex-col gap-1 p-0">
      <li className="flex items-center gap-2 text-small">
        <button type="button" className="cursor-pointer font-mono text-xs">
          D-2
        </button>
        <span className="min-w-0 flex-1 truncate">
          <RecordText {...args} />
        </span>
      </li>
    </ul>
  ),
};

/** 項目のカードのタイトルのボタンの中。ID はリンクにせず点線の下線のマーカーにし、ボタンの `aria-describedby` で ID の項目を読み上げる。カードの中にフォーカスできる要素は増えない */
export const CardTitleMarkers: Story = {
  args: { text: "D-1 の比較（D-99 は除く）", mode: "marker", descriptionId: "card-a1-ids" },
  render: (args) => (
    <div className="w-64 rounded-card border border-border-soft bg-card p-2">
      <button type="button" aria-describedby="card-a1-ids" className="cursor-pointer text-left text-small font-medium">
        <RecordText {...args} />
      </button>
      <span className="block font-mono text-xs text-muted-foreground">A-1</span>
    </div>
  ),
};

/** タスクのカードの進める検討事項の行。カード全体を押すと開くため、タイトルの中の D-1 はマーカーにする */
export const CardLinkRowMarkers: Story = {
  args: { text: "D-1 の見直し", mode: "marker", descriptionId: "card-t1-for" },
  render: (args) => (
    <div className="w-64 rounded-card border border-border-soft bg-card p-2">
      <button type="button" aria-describedby="card-t1-for" className="cursor-pointer text-left text-small font-medium">
        保存先を決める
      </button>
      <span className="block text-xs text-muted-foreground">
        <span className="font-mono">D-2</span> <RecordText {...args} />
      </span>
    </div>
  ),
};

/** 全体の検索の結果の行（`option`）。中にフォーカスできる要素を配置せず、マーカーにする */
export const SearchResultMarkers: Story = {
  args: { text: "D-1 の比較（D-99 は除く）", mode: "marker", descriptionId: "result-a1-ids" },
  render: (args) => (
    <div role="listbox" aria-label="検索の結果" className="w-full max-w-96">
      <div role="option" aria-selected="true" aria-describedby="result-a1-ids" tabIndex={-1} className="flex items-center gap-2 rounded-control bg-row-selected px-2 py-1.5 text-small">
        <span className="font-mono text-xs text-muted-foreground">A-1</span>
        <span className="min-w-0 flex-1 truncate">
          <RecordText {...args} />
        </span>
      </div>
    </div>
  ),
};

/** ID を持たないタイトル。文字をそのまま描く */
export const NoIds: Story = {
  args: { text: "保存先の比較" },
  render: (args) => (
    <h2 className="m-0 text-h2 font-semibold">
      <RecordText {...args} />
    </h2>
  ),
};

/** 長いタイトル（幅 240px）。タイトルの文字は折り返し、枠の外へはみ出さない */
export const LongTitle: Story = {
  args: { text: "D-1 と TH-1 で話した保存先の候補を、運用の手間・費用・書き込みの速さで比べ直し、D-2 の見直しの結論を反映した資料（D-99 は対象外）" },
  render: (args) => (
    <h2 className="m-0 w-60 text-h2 font-semibold">
      <RecordText {...args} />
    </h2>
  ),
};

/** 見出しのタイトルの D-1 のリンクに乗せた。D-1 のタイトルと ID・「検討事項」・状態のツールチップを出す */
export const LinkHover: Story = {
  ...HeadingLinks,
  play: async ({ canvasElement }) => {
    const link = canvasElement.querySelector<HTMLElement>('[data-record-id="D-1"]');
    if (link !== null) await userEvent.hover(link);
  },
};

/** 指で見出しのタイトルの D-1 のリンクを押した。ツールチップを出さず、1 回で onOpen("D-1") を呼ぶ */
export const TouchLinkTap: Story = {
  args: { text: "D-1 の比較（TH-1 の続き、D-99 は除く）", mode: "link" },
  render: (args) => <OpenedIds {...args} />,
  play: async ({ canvasElement }) => {
    const link = canvasElement.querySelector<HTMLElement>('[data-record-id="D-1"]');
    if (link !== null) await userEvent.pointer([{ keys: "[TouchA]", target: link }]);
  },
};

/** カードのタイトルの D-1 のマーカーに乗せた。D-1 のタイトルと状態のツールチップを出し、押すとカードを開く操作は変わらない */
export const MarkerHover: Story = {
  ...CardTitleMarkers,
  play: async ({ canvasElement }) => {
    const marker = canvasElement.querySelector<HTMLElement>('[data-record-id="D-1"]');
    if (marker !== null) await userEvent.hover(marker);
  },
};

/** カードのタイトルのボタンに Tab でフォーカスした。行の中の ID のツールチップを出し、ボタンの aria-describedby で D-1 の説明を読み上げる */
export const MarkerRowFocus: Story = {
  ...CardTitleMarkers,
  play: async () => {
    await userEvent.tab();
  },
};

/** スレッドの行のボタンの中。D-1 は点線の下線のマーカーのままで、乗せてもボタンにフォーカスしてもツールチップを出さない。ボタンの aria-describedby の説明は残る */
export const MarkerNoTooltip: Story = {
  args: { text: "D-1 の決め方（TH-1 の続き）", mode: "marker", descriptionId: "thread-th2-ids", tooltip: false },
  render: (args) => (
    <div className="w-64 rounded-card border border-border-soft bg-card p-2">
      <button type="button" aria-describedby="thread-th2-ids" className="cursor-pointer text-left text-small font-medium">
        <RecordText {...args} />
      </button>
    </div>
  ),
  play: async ({ canvasElement }) => {
    const marker = canvasElement.querySelector<HTMLElement>('[data-record-id="D-1"]');
    if (marker !== null) await userEvent.hover(marker);
    await userEvent.tab();
  },
};
