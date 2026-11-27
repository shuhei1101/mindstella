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

/** 8 列の表。mdmark の表の機能で描かれ、列の幅と折り返し・並べ替え・ピン止め・列の幅の変更のボタンは mdmark のまま。表が本文の幅からはみ出し、表の中だけが横にスクロールする。描いた直後はどの列も左端に留まらない。画面の CSS が当てた列の幅・フェード・しま模様は無い */
export const MdmarkTable: Story = {};

/** 「ID」と「名前」のピン止めのボタンを押して右へスクロールした。ID と名前の 2 列が左端に留まり、その間の状態の列は留まらない */
export const PinnedColumns: Story = {
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, 'button.mdmark-pin[aria-label="「ID」の列をピン止め"]')).click();
    (await rendered(canvasElement, 'button.mdmark-pin[aria-label="「名前」の列をピン止め"]')).click();
    const scroll = canvasElement.querySelector<HTMLElement>(".mdmark-table-scroll");
    if (scroll !== null) scroll.scrollLeft = scroll.scrollWidth;
  },
};

/** 本文の背景は周りの面になじむ透明で、ピン止めのボタンで留めた列・表の左右の端の影を隠す覆い・ツールチップは周りの面の色（`--mdmark-color-bg-opaque`）で塗られる。横にスクロールできない側の端に影が出ない */
export const OpaqueBackground: Story = {
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, 'button.mdmark-pin[aria-label="「ID」の列をピン止め"]')).click();
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

/** 言語を書いたコードブロックは mdmark のコードブロックのバー（言語の札・コピー）と行の部品と色分けで描き、画面の言語の札とコピーのボタンを重ねない。長い行は折り返さず、コードブロックの中だけで横にスクロールできる。言語の札とコピーのボタンは横にスクロールしても同じ位置に残る */
export const CodeBlock: Story = { args: { source: CODE_SOURCE } };

/** mdmark のコピーのボタンを押した直後。ボタンの見た目は mdmark のままで、クリップボードには札とボタンを含まないコードだけが入る */
export const CodeCopied: Story = {
  args: { source: CODE_SOURCE },
  play: async ({ canvasElement }) => {
    const button = await rendered(canvasElement, "button.mdmark-code-copy");
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

/** 言語 markdown のコードブロック。mdmark が描いた結果で出し、バーの「Raw」を押すと元の Markdown のコードに切り替わる */
export const CodeMarkdownRaw: Story = {
  args: { source: ["```markdown", "## 見出し", "", "- 項目 1", "- 項目 2", "```"].join("\n") },
  play: async ({ canvasElement }) => {
    const raw = await rendered(canvasElement, "button.mdmark-code-raw");
    raw.click();
  },
};

/** 言語 python の 2 階層の字下げを持つコードブロック。字下げの縦線と行の開閉のボタンがあり、キーワードが色分けされる */
export const CodeIndentGuides: Story = {
  args: { source: ["```python", "def total(items):", "    result = 0", "    for item in items:", "        if item > 0:", "            result += item", "    return result", "```"].join("\n") },
};

/** 見出しの下に段落・表・map の図・リストと小見出しを並べた本文。見出しごとに包む要素（md-section-body）の直下のブロック同士に、mdmark の本文と同じ間（--mdmark-space）が空き、小見出しの上の間は mdmark の見出しの間のまま */
export const SectionSpacing: Story = {
  args: {
    source: [
      "## 候補",
      "",
      "候補の説明です。",
      "",
      "| 案 | 内容 |",
      "| --- | --- |",
      "| A | 先に試す |",
      "",
      "<!-- map -->",
      "",
      "```mermaid",
      "flowchart LR",
      "  a --> b",
      "```",
      "",
      "<!-- /map -->",
      "",
      "- 項目 1",
      "- 項目 2",
      "",
      "まとめの段落です。",
      "",
      "### 料金",
      "",
      "料金の説明です。",
    ].join("\n"),
  },
};

/** 本文に外部の URL へのリンクと、同じオリジン・# で始まるリンクを持つ。外部の URL へのリンクだけが target="_blank" と rel="noopener noreferrer" を持つ */
export const ExternalLink: Story = {
  args: { source: ["[外部のページ](https://example.com/)", "", "[同じオリジン](/w/sample/)", "", "[D-1](#id=D-1)"].join("\n") },
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

/** 音声を埋め込んだ本文（`files/sample.wav` は Storybook の静的なファイル） */
const AUDIO_SOURCE = ["セリフの音声を確かめる。", "", "![セリフの音声](../files/sample.wav)", "", "音声の後ろの段落。", ""].join("\n");

/** 本文に埋め込んだ音声。mdmark が描いた再生バーを、入れ物の高さ・`overflow`・`line-height` で上下を切らずに全体を表示する */
export const AudioEmbed: Story = { args: { source: AUDIO_SOURCE } };

/** 幅 390px で埋め込んだ音声。再生バーを本文の幅に収め、上下を切らず、本文の区画を横にスクロールさせない */
export const AudioEmbedNarrow: Story = {
  args: { source: AUDIO_SOURCE },
  parameters: {
    viewport: {
      options: { narrow390: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow390", isRotated: false } },
};

/** スレッドの書き込みの本文。コードブロックの言語の札とコピーのボタン、Alert の見出しのアイコンを当て、表は mdmark の表の機能をオフにした共通のスタイルのまま描き、セクションの開閉は当てない */
export const InThreadPost: Story = {
  args: { source: [CODE_SOURCE, CALLOUT_SOURCE, tableSource(3)].join("\n"), fold: false, tables: false },
};

/** 本文に `<!-- html -->` の範囲（`.mdmark-html`）があり、中に表・見出し・チャート・スライダーを持つ。範囲の中の見出しには開閉を当てず、範囲の中の表・見出しは書いた HTML と mdmark の部品の見た目のまま描く。範囲の前後の見出しには今までどおり開閉を当てる */
export const EmbeddedHtml: Story = { args: { source: EMBEDDED_SOURCE } };

/** 本文の差分の中の表。足した行・消した行を持ち、mdmark の表で描かれる。足した行・消した行の面の色と消した行の取り消し線は、ピン止めのボタンで左端に留めた列のセルにも付き、開閉を置かない */
export const TableInDiff: Story = {
  args: { source: `${SECTIONS_SOURCE}\n${tableSource(6)}`, fold: false },
  play: async ({ canvasElement }) => {
    (await rendered(canvasElement, 'button.mdmark-pin[aria-label="「ID」の列をピン止め"]')).click();
    const rows = canvasElement.querySelectorAll("tbody tr");
    rows[1]?.classList.add("df-row", "df-add");
    rows[2]?.classList.add("df-row", "df-del");
  },
};

/** 選んだ時点の本文（段落 3 つと箇条書き） */
const DIFF_BEFORE = [
  "# 保存先の決め方",
  "",
  "記録はワークスペースのフォルダに配置する。",
  "",
  "保存先は話し合いを始めるときに一度だけ決め、途中では変えない。",
  "",
  "保存した記録は、保持する回数を超えたものから削除する。",
  "",
  "- 記録の YAML",
  "- 本文の Markdown",
  "",
].join("\n");

/** 今の本文（1 つ目の段落の単語を書き換え、3 つ目の段落を削除し、箇条書きに 1 行追加した） */
const DIFF_AFTER = [
  "# 保存先の決め方",
  "",
  "記録はワークスペースのフォルダにまとめて配置する。",
  "",
  "保存先は話し合いを始めるときに一度だけ決め、途中では変えない。",
  "",
  "- 記録の YAML",
  "- 本文の Markdown",
  "- 添付したファイル",
  "",
].join("\n");

/** 差分の表示で「描いた結果」。書き換えた段落と追加した箇条書きの項目は追加の色と左の余白の `+`、削除した段落は削除の色と `−` で変更前の位置に出る。書き換えた段落の前の文と変わった単語は出さない */
export const DiffRendered: Story = { args: { source: DIFF_AFTER, base: DIFF_BEFORE, fold: false } };

/** 差分の表示で「原文の差分」。mdmark の「変更表示」を押した状態で、前と後のリビジョンの欄に「選んだ時点」「今」が入り、書き換えた行の変わった単語だけが濃い色になる */
export const DiffSource: Story = { args: { source: DIFF_AFTER, base: DIFF_BEFORE, diffView: "source", fold: false } };

/** 差分の表示で、選んだ時点から変わっていない本文。色を付けずに今の本文だけを出す */
export const DiffUnchanged: Story = { args: { source: DIFF_AFTER, base: DIFF_AFTER, fold: false } };

/** 列が多く画面の幅を超える表を、最も狭めたパネルの幅（320px）の本文の区画で描く。表は表の部品の中だけで横にスクロールし、本文の区画は横にスクロールせず、区画の幅を超えて描かれない */
export const WideTableInNarrowPane: Story = {
  args: { source: tableSource(12) },
  render: (props: Args) => (
    <div data-part="narrow-pane" style={{ width: "320px" }} className="min-w-0 border border-border">
      <MarkdownBody {...props} />
    </div>
  ),
};
