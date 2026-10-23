// Markdown の本文のストーリー（部品設計『Markdownの本文』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

/** ストーリーの引数（部品の引数の `root` は、ストーリーが `source` を描いて作る） */
type Args = {
  /** 描く Markdown */
  source: string;
  display: MindmapPreview.BodyView;
  fold: boolean;
  /** 本文のスクロール領域の高さ（px）。省くと領域を作らない */
  height?: number;
};

/** 表の行（ID・状態・名前・担当・期限・種別・優先度・説明の 8 列）を `count` 行分並べた Markdown の表 */
function tableSource(count: number): string {
  const rows = Array.from({ length: count }, (_, offset) => {
    const no = offset + 1;
    return `| D-${no} | 検討中 | 本文の表の見せ方を決める ${no} | 佐藤 | 2026-10-${String(no).padStart(2, "0")} | 設計 | 高 | 列の文字数で幅と折り返しを決め、表が本文の幅に収まらないときは表の中だけで横に送れるようにする。 |`;
  });
  return ["| ID | 状態 | 名前 | 担当 | 期限 | 種別 | 優先度 | 説明 |", "| --- | --- | --- | --- | --- | --- | --- | --- |", ...rows, ""].join("\n");
}

/** 2 列の小さな表 */
const SMALL_TABLE_SOURCE = "| 項目 | 値 |\n| --- | --- |\n| 状態 | 検討中 |\n| 担当 | 佐藤 |\n";

/** 見出しの階層を 3 つ使い、中身の無い見出しも持つ本文 */
const SECTIONS_SOURCE = [
  "## 候補",
  "",
  "候補の説明です。",
  "",
  "### 料金",
  "",
  "料金の説明です。",
  "",
  "#### 内訳",
  "",
  "内訳の説明です。",
  "",
  "## まとめ",
  "",
  "まとめの説明です。",
  "",
  "## 付録",
  "",
].join("\n");

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

const { h } = MindmapPreview;

/** 表と見出しを持つ本文に、ストーリーの引数で見せ方を当てる。高さを渡したときは、本文のスクロール領域に入れて表の見出しの固定を受け付ける */
function build({ source, display, fold, height }: Args): HTMLElement {
  const root = MindmapPreview.renderMarkdown(source);
  // 見出しの名前（`data-heading`）は、詳細の本文と同じく先に付ける
  MindmapPreview.linkHeadings({ root, onHeading: () => undefined, onChangeSet: () => undefined });
  MindmapPreview.decorateMarkdown({ root, display, fold });
  const stage = h({ tag: "div", attrs: { class: "story-stage" }, children: [root] });
  if (height === undefined) return stage;
  const scroller = h({ tag: "div", attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" }, children: [root] });
  scroller.style.cssText = `height: ${height}px; overflow: auto;`;
  MindmapPreview.bindTableHeads(scroller);
  stage.replaceChildren(scroller);
  return stage;
}

const meta = {
  title: "Preview/MarkdownBody",
  render: (args) => {
    const stage = build(args);
    stage.style.width = "min(720px, 100%)";
    return stage;
  },
  args: { source: tableSource(6), display: MindmapPreview.BODY_VIEW_DEFAULT, fold: true },
} satisfies Meta<Args>;

export default meta;

type Story = StoryObj<Args>;

/** 8 列の表。ID のように 8 文字以下の列は折り返さず、25 文字以上の列は 24em で折り返し、その間の列は文字数の半分 + 2em を最小の幅に文節の区切りでだけ折り返す。表は本文より広く、表の中だけで横に送れ、右端がフェードする */
export const ColumnWidths: Story = {};

/** 2 列の表。本文の幅いっぱいに広げず、中身の幅で描き、フェードを出さない */
export const SmallTable: Story = { args: { source: SMALL_TABLE_SOURCE } };

/** 列の見出しにポインターを載せた。最後の列を除く見出しに固定のボタンが出る（フォーカスで同じ見え方にする） */
export const PinHover: Story = {
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>("button.md-pin")?.focus({ focusVisible: true });
  },
};

/** 「名前」の固定のボタンを押して右へ送った。「名前」より左の列が左端に残り、固定した列の右端に影が付き、ボタンは `aria-pressed="true"` */
export const Pinned: Story = {
  play: ({ canvasElement }) => {
    const buttons = canvasElement.querySelectorAll<HTMLElement>("button.md-pin");
    buttons[2]?.click();
    const wrap = canvasElement.querySelector<HTMLElement>(".md-table-wrap");
    if (wrap !== null) wrap.scrollLeft = wrap.scrollWidth;
  },
};

/** 表示の設定で列の固定をオフにした。見出しに固定のボタンを置かない */
export const PinOff: Story = { args: { display: { ...MindmapPreview.BODY_VIEW_DEFAULT, pin: false } } };

/** 縦に高さを限った本文の区画の中で、長い表の途中まで送った。見出しの行が区画の上端に残り、下の境に影が付く。表の下端を越えては残らない */
export const HeadStuck: Story = {
  args: { source: tableSource(30), height: 280 },
  play: ({ canvasElement }) => {
    const scroller = canvasElement.querySelector<HTMLElement>(".panel-body");
    if (scroller !== null) scroller.scrollTop = 160;
  },
};

/** 表示の設定で見出しの固定をオフにした。見出しの行も本文と一緒に送られる */
export const HeadOff: Story = {
  args: { source: tableSource(30), height: 280, display: { ...MindmapPreview.BODY_VIEW_DEFAULT, head: false } },
  play: ({ canvasElement }) => {
    const scroller = canvasElement.querySelector<HTMLElement>(".panel-body");
    if (scroller !== null) scroller.scrollTop = 160;
  },
};

/** 表示の設定でしま模様をオンにした。本体の行を 1 行おきに塗り分ける */
export const Stripes: Story = { args: { display: { ...MindmapPreview.BODY_VIEW_DEFAULT, stripes: true } } };

/** 本文の差分でしま模様をオンにした。足した行と消した行は差分の面のままで、開閉を置かない */
export const StripesInDiff: Story = {
  args: { source: `${SECTIONS_SOURCE}\n${tableSource(6)}`, display: { ...MindmapPreview.BODY_VIEW_DEFAULT, stripes: true }, fold: false },
  play: ({ canvasElement }) => {
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
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>('[data-heading="料金"] button.md-fold')?.click();
  },
};

/** 表示の設定でセクションの折りたたみをオフにした。見出しに開閉を置かない */
export const FoldOff: Story = { args: { source: SECTIONS_SOURCE, display: { ...MindmapPreview.BODY_VIEW_DEFAULT, fold: false } } };

/** 言語を書いたコードブロックは左上に言語の札を出し、ホバーで右上にコピーのボタンを出す。言語を書かないコードブロックには札を出さない。長い行は折り返す */
export const CodeBlock: Story = { args: { source: CODE_SOURCE } };

/** コピーのボタンを押した直後。ボタンがチェックのマーカーに変わり、クリップボードには札とボタンを含まないコードだけが入る */
export const CodeCopied: Story = {
  args: { source: CODE_SOURCE },
  play: async ({ canvasElement }) => {
    // ストーリーの画面ではクリップボードの許可に左右されないよう、書き込みを受けるだけの代わりを置く
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: () => Promise.resolve() } });
    const button = canvasElement.querySelector<HTMLElement>("button.code-copy");
    // 元のコピーのマーカーへ戻す待ちを止め、押した直後の状態のまま残す
    const setTimer = window.setTimeout;
    window.setTimeout = (() => 0) as unknown as typeof window.setTimeout;
    button?.click();
    await new Promise((resolve) => requestAnimationFrame(resolve));
    window.setTimeout = setTimer;
    button?.focus({ focusVisible: true });
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
