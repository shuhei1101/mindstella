// Markdownの本文のストーリー（部品設計『Markdownの本文.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { waitFor } from "storybook/test";

import { MarkdownBody, type MarkdownBodyProps } from "@/shared/components/markdown-body";
import { BODY_VIEW_DEFAULT } from "@/shared/core/markdown-decorate";

/** ストーリーの引数 */
type Args = MarkdownBodyProps;

/** 表の行（ID・状態・名前・担当・期限・種別・優先度・説明の 8 列）を `count` 行分並べた Markdown の表 */
const tableSource = (count: number): string => {
  const rows = Array.from({ length: count }, (_, offset) => {
    const no = String(offset + 1);
    return `| D-${no} | 検討中 | 本文の表の見せ方を決める ${no} | 佐藤 | 2026-10-${no.padStart(2, "0")} | 設計 | 高 | 表は mdmark の表の機能で描き、表が本文の幅に収まらないときは表の中だけで横にスクロールする。 |`;
  });
  return ["| ID | 状態 | 名前 | 担当 | 期限 | 種別 | 優先度 | 説明 |", "| --- | --- | --- | --- | --- | --- | --- | --- |", ...rows, ""].join("\n");
};

/** 2 列の小さな表 */
const SMALL_TABLE_SOURCE = "| 項目 | 値 |\n| --- | --- |\n| 状態 | 検討中 |\n| 担当 | 佐藤 |\n";

/** 見出しの階層を 3 つ使い、中身の無い見出しも持つ本文 */
const SECTIONS_SOURCE = ["## 候補", "", "候補の説明です。", "", "### 料金", "", "料金の説明です。", "", "#### 内訳", "", "内訳の説明です。", "", "## まとめ", "", "まとめの説明です。", "", "## 付録", ""].join("\n");

/** 言語を書いたコードブロックと、書かないコードブロック */
const CODE_SOURCE = [
  "言語を書いたコードブロック。",
  "",
  "```bash",
  "echo hello",
  "ls -la /very/long/path/that/keeps/going/and/going/until/the/line/is/wider/than/the/block/so/it/scrolls/sideways/inside/the/block/instead/of/wrapping/onto/the/next/line/and/breaking/the/layout",
  "```",
  "",
  "言語を書かないコードブロック。",
  "",
  "```",
  "plain text",
  "```",
  "",
].join("\n");

/** Alert の 5 種類と、印の無い引用 */
const CALLOUT_SOURCE = [
  "> [!NOTE]",
  "> 知っておくと理解が早いこと。",
  "",
  "> [!TIP]",
  "> 知っていると楽になること。",
  "",
  "> [!IMPORTANT]",
  "> 進めるのに欠かせないこと。",
  "",
  "> [!WARNING]",
  "> 守らないと壊れること。",
  "",
  "> [!CAUTION]",
  "> 取り返しが付かなくなること。",
  "",
  "> ただの引用です。",
  "",
].join("\n");

/** 埋め込んだ HTML の範囲に置くチャート（JSON の定義） */
const EMBEDDED_CHART = JSON.stringify({
  type: "bar",
  title: "件数",
  scope: "10 月",
  updated: "2026-10-27",
  x: { label: "窓口", ticks: ["メール", "電話"] },
  y: { label: "件" },
  series: [{ name: "自動返信", points: [10, 20] }],
});

/** 埋め込んだ HTML の範囲に置く、キー rps のスライダーを持つ操作できる部品（JSON の定義） */
const EMBEDDED_PARAM = JSON.stringify({
  title: "リクエスト数の見積もり",
  knob: { key: "rps", label: "リクエスト数", min: 0, max: 10, step: 1, value: 5 },
  chart: { title: "応答時間", scope: "ピーク時", updated: "2026-10-27", x: { label: "経過", ticks: ["0", "1"] }, y: { label: "ミリ秒", min: 0, max: 100, step: 50 } },
  table: Object.fromEntries(Array.from({ length: 11 }, (_, value) => [String(value), [value * 10, value * 10 + 5]])),
});

/** 範囲の前に見出しと表、範囲の中に見出し・表・チャート・スライダー、範囲の後に見出しを持つ本文 */
const EMBEDDED_SOURCE = [
  "## 前の見出し",
  "",
  SMALL_TABLE_SOURCE,
  "<!-- html -->",
  "```html",
  "<h3>範囲の見出し</h3>",
  "<table><tr><th>項目</th><td>値</td></tr></table>",
  `<mdmark-chart>${EMBEDDED_CHART}</mdmark-chart>`,
  `<mdmark-param>${EMBEDDED_PARAM}</mdmark-param>`,
  "```",
  "<!-- /html -->",
  "",
  "### 後ろの見出し",
  "",
].join("\n");

/** mdmark が描き、見せ方を当て終わった要素を待って返す */
const rendered = async (canvas: HTMLElement, selector: string): Promise<HTMLElement> =>
  waitFor(() => {
    const element = canvas.querySelector<HTMLElement>(selector);
    if (element === null) throw new Error(`${selector} がまだありません`);
    return element;
  });

const meta = {
  title: "Shared/MarkdownBody",
  component: MarkdownBody,
  render: (props: Args) => (
    <div style={{ width: "min(720px, 100%)" }}>
      <MarkdownBody {...props} />
    </div>
  ),
  args: { source: tableSource(6), display: BODY_VIEW_DEFAULT, fold: true },
} satisfies Meta<Args>;

export default meta;

type Story = StoryObj<Args>;

/** 8 列の表。mdmark の表の機能で描かれ、列の幅と折り返し・並べ替え・ピン止め・列の幅の変更のボタンは mdmark のまま。表が本文の幅からはみ出すため、先頭の列が左端に留まり、表の中だけが横にスクロールする。画面の CSS が当てた列の幅・フェード・しま模様は無い */
export const MdmarkTable: Story = {};

/** 「名前」のピン止めのボタンを押して右へスクロールした。ID と名前の 2 列が左端に留まり、その間の状態の列は留まらない */
export const PinnedColumns: Story = {
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, 'button.mdmark-pin[aria-label="「名前」の列をピン止め"]')).click();
    const scroll = canvasElement.querySelector<HTMLElement>(".mdmark-table-scroll");
    if (scroll !== null) scroll.scrollLeft = scroll.scrollWidth;
  },
};

/** 本文の背景は周りの面になじむ透明で、ピン止めした列・表の左右の端の影を隠す覆い・ツールチップは周りの面の色（`--mdmark-color-bg-opaque`）で塗られる。横にスクロールできない側の端に影が出ない */
export const OpaqueBackground: Story = {
  play: async ({ canvasElement }) => {
    const scroll = await rendered(canvasElement, ".mdmark-table-scroll");
    scroll.scrollLeft = Math.floor((scroll.scrollWidth - scroll.clientWidth) / 2);
  },
};

/** 本文で使っている上位 2 つの階層の見出しの頭に開閉の矢印を置き、開いた状態で描く。中身の無い見出しには置かない。見出しの文言は選べる */
export const Sections: Story = { args: { source: SECTIONS_SOURCE } };

/** 「料金」の矢印を押して畳んだ。次の同じか上の階層の見出しまでを隠し、下の階層の見出しも一緒に隠す。矢印は `aria-expanded="false"` */
export const Folded: Story = {
  args: { source: SECTIONS_SOURCE },
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, 'button.md-fold[aria-label="料金を開閉"]')).click();
  },
};

/** 表示の設定でセクションの折りたたみをオフにした。見出しに開閉を置かない */
export const FoldOff: Story = { args: { source: SECTIONS_SOURCE, display: { ...BODY_VIEW_DEFAULT, fold: false } } };

/** 言語を書いたコードブロックは左上に言語の札を出し、ホバーで右上にコピーのボタンを出す。言語を書かないコードブロックには札を出さない。長い行は折り返さず、コードブロックの中だけで横に送れる。言語の札とコピーのボタンは横に送っても同じ位置に残る */
export const CodeBlock: Story = { args: { source: CODE_SOURCE } };

/** コピーのボタンを押した直後。ボタンがチェックのマーカーに変わり、クリップボードには札とボタンを含まないコードだけが入る */
export const CodeCopied: Story = {
  args: { source: CODE_SOURCE },
  play: async ({ canvasElement }) => {
    const button = await rendered(canvasElement, "button.code-copy");
    // ストーリーの画面ではクリップボードの許可に左右されないよう、書き込みを受けるだけの代わりを置く
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: () => Promise.resolve() } });
    // 元のコピーのマーカーへ戻す待ちを止め、押した直後の状態のまま残す
    const setTimer = window.setTimeout.bind(window);
    window.setTimeout = (() => 0) as unknown as typeof window.setTimeout;
    button.click();
    await new Promise((resolve) => requestAnimationFrame(resolve));
    window.setTimeout = setTimer;
    button.focus({ focusVisible: true });
  },
};

/** `> [!NOTE]`・`[!TIP]`・`[!IMPORTANT]`・`[!WARNING]`・`[!CAUTION]` の引用を、種類の色の薄い面と細い枠で囲み、見出しにアイコンと「補足」「ヒント」「重要」「警告」「注意」を出す。印の無い引用は今の見た目のまま */
export const Callouts: Story = { args: { source: CALLOUT_SOURCE } };

/** 画面の幅 320px。表は mdmark の表のまま表の中だけで横にスクロールし、本文の区画は横にスクロールしない */
export const Narrow: Story = {
  args: { source: tableSource(6) },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 320px", styles: { width: "320px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** スレッドの書き込みの本文。コードブロックの言語の札とコピーのボタン、Alert の見出しのアイコンを当て、表は mdmark の表の機能をオフにした共通のスタイルのまま描き、セクションの開閉は当てない */
export const InThreadPost: Story = {
  args: { source: [CODE_SOURCE, CALLOUT_SOURCE, tableSource(3)].join("\n"), fold: false, tables: false },
};

/** 本文に `<!-- html -->` の範囲（`.mdmark-html`）があり、中に表・見出し・チャート・スライダーを持つ。範囲の中の見出しには開閉を当てず、範囲の中の表・見出しは書いた HTML と mdmark の部品の見た目のまま描く。範囲の前後の見出しには今までどおり開閉を当てる */
export const EmbeddedHtml: Story = { args: { source: EMBEDDED_SOURCE } };

/** 本文の差分の中の表。足した行・消した行を持ち、mdmark の表で描かれる。足した行・消した行の面の色と消した行の取り消し線は、ピン止めして左端に留まった列のセルにも付き、開閉を置かない */
export const TableInDiff: Story = {
  args: { source: `${SECTIONS_SOURCE}\n${tableSource(6)}`, fold: false },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement, ".mdmark-table");
    const rows = canvasElement.querySelectorAll("tbody tr");
    rows[1]?.classList.add("df-row", "df-add");
    rows[2]?.classList.add("df-row", "df-del");
  },
};
