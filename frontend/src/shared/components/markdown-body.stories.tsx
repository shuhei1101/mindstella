// Markdownの本文のストーリー（部品設計『Markdownの本文.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useEffect, useRef } from "react";
import { waitFor } from "storybook/test";

import { MarkdownBody, type MarkdownBodyProps } from "@/shared/components/markdown-body";
import { BODY_VIEW_DEFAULT, bindTableHeads } from "@/shared/core/markdown-decorate";

/** ストーリーの引数（`height` を渡すと、高さを限った本文のスクロール領域に入れる） */
type Args = MarkdownBodyProps & { height?: number };

/** 表の行（ID・状態・名前・担当・期限・種別・優先度・説明の 8 列）を `count` 行分並べた Markdown の表 */
const tableSource = (count: number): string => {
  const rows = Array.from({ length: count }, (_, offset) => {
    const no = String(offset + 1);
    return `| D-${no} | 検討中 | 本文の表の見せ方を決める ${no} | 佐藤 | 2026-10-${no.padStart(2, "0")} | 設計 | 高 | 列の文字数で幅と折り返しを決め、表が本文の幅に収まらないときは表の中だけで横に送れるようにする。 |`;
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
  "ls -la /very/long/path/that/keeps/going/and/going/until/the/line/has/to/wrap/inside/the/block",
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

/** 高さを限った本文のスクロール領域に本文を入れ、表の見出しの固定をつなぐ */
const Scroller = ({ height, ...props }: MarkdownBodyProps & { height: number }) => {
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = scroller.current;
    return element === null ? undefined : bindTableHeads(element);
  }, []);
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- 本文のスクロール領域をキーボードで送れるようにする（詳細パネルの本文と同じ）
    <div ref={scroller} className="panel-body" tabIndex={0} role="region" aria-label="詳細の本文" style={{ height: `${String(height)}px`, overflow: "auto" }}>
      <MarkdownBody {...props} />
    </div>
  );
};

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
  render: ({ height, ...props }: Args) => (
    <div style={{ width: "min(720px, 100%)" }}>
      {height === undefined ? <MarkdownBody {...props} /> : <Scroller height={height} {...props} />}
    </div>
  ),
  args: { source: tableSource(6), display: BODY_VIEW_DEFAULT, fold: true },
} satisfies Meta<Args>;

export default meta;

type Story = StoryObj<Args>;

/** 8 列の表。短い列は折り返さず、長文の列は 24em で折り返し、中くらいの列は文節の区切りで折り返す。表は本文より広く、表の中だけで横に送れ、右端がフェードする */
export const ColumnWidths: Story = {};

/** 2 列の表。本文の幅いっぱいに広げず、中身の幅で描き、フェードを出さない */
export const SmallTable: Story = { args: { source: SMALL_TABLE_SOURCE } };

/** 列の見出しにポインターを載せた。最後の列を除く見出しに固定のボタンが出る（フォーカスで同じ見え方にする） */
export const PinHover: Story = {
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, "button.md-pin")).focus({ focusVisible: true });
  },
};

/** 「名前」の固定のボタンを押して右へ送った。「名前」より左の列が左端に残り、固定した列の右端に影が付き、ボタンは `aria-pressed="true"` */
export const Pinned: Story = {
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, 'button.md-pin[aria-label="名前まで固定"]')).click();
    const wrap = canvasElement.querySelector<HTMLElement>(".md-table-wrap");
    if (wrap !== null) wrap.scrollLeft = wrap.scrollWidth;
  },
};

/** 表示の設定で列の固定をオフにした。見出しに固定のボタンを置かない */
export const PinOff: Story = { args: { display: { ...BODY_VIEW_DEFAULT, pin: false } } };

/** 縦に高さを限った本文の区画の中で、長い表の途中まで送った。見出しの行が区画の上端に残り、下の境に影が付く。表の下端を越えては残らない */
export const HeadStuck: Story = {
  args: { source: tableSource(30), height: 280 },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement, "table.md-head-stick");
    const scroller = canvasElement.querySelector<HTMLElement>(".panel-body");
    if (scroller !== null) scroller.scrollTop = 160;
  },
};

/** 表示の設定で見出しの固定をオフにした。見出しの行も本文と一緒に送られる */
export const HeadOff: Story = {
  args: { source: tableSource(30), height: 280, display: { ...BODY_VIEW_DEFAULT, head: false } },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement, ".md-table-wrap");
    const scroller = canvasElement.querySelector<HTMLElement>(".panel-body");
    if (scroller !== null) scroller.scrollTop = 160;
  },
};

/** 表示の設定でしま模様をオンにした。本体の行を 1 行おきに塗り分ける */
export const Stripes: Story = { args: { display: { ...BODY_VIEW_DEFAULT, stripes: true } } };

/** 本文の差分でしま模様をオンにした。足した行と消した行は差分の面のままで、開閉を置かない */
export const StripesInDiff: Story = {
  args: { source: `${SECTIONS_SOURCE}\n${tableSource(6)}`, display: { ...BODY_VIEW_DEFAULT, stripes: true }, fold: false },
  play: async ({ canvasElement }) => {
    await rendered(canvasElement, "table.md-stripes");
    const rows = canvasElement.querySelectorAll("tbody tr");
    rows[1]?.classList.add("df-row", "df-add");
    rows[2]?.classList.add("df-row", "df-del");
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

/** 画面の幅 390px。列の固定と固定のボタンを出さず、見出しの固定は残す。表は表の中だけで横に送れる */
export const Narrow: Story = {
  args: { source: tableSource(30), height: 360 },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};

/** スレッドの書き込みの本文。コードブロックの言語の札とコピーのボタン、Alert の見出しのアイコンを当て、表の列の幅・フェード・固定・見出しの固定とセクションの開閉は当てない */
export const InThreadPost: Story = {
  args: { source: [CODE_SOURCE, CALLOUT_SOURCE, tableSource(3)].join("\n"), fold: false, tables: false },
};

/** 本文に `<!-- html -->` の範囲があり、中に表・見出し・チャート・スライダーを持つ。範囲の中の表・見出しには列の幅・フェード・固定・見出しの固定・しま模様・開閉を当てず、書いた HTML と mdmark の部品の見た目のまま描く。範囲の前後の表と見出しには今までどおり当てる */
export const EmbeddedHtml: Story = { args: { source: EMBEDDED_SOURCE } };
