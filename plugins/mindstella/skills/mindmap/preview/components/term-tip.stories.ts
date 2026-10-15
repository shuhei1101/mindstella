// 本文の印のツールチップのストーリー（部品設計『本文の印のツールチップ』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";
import { fn } from "storybook/test";

/** ストーリーで使う引数（部品の引数に、印を本文のどこに置くかを足したもの。`anchor` は描くときに本文の印へ替える） */
type Args = MindmapPreview.TermTipProps & {
  /** 印を置く本文の段落の上の余白（CSS の長さ） */
  markTop: string;
};

/** 見本の項目を作る */
function item(id: string, title: string, extra: Partial<MindmapPreview.Item> = {}): MindmapPreview.Item {
  return { id, title, created: "2026-10-01T00:00:00+00:00", updated: "2026-10-01T00:00:00+00:00", ...extra };
}

/** 用語 1 件 */
const term = { kind: "terms", item: item("G-1", "特殊効果", { meaning: "画面に重ねる演出" }) } as const;

/** 資料 6 件（説明つき） */
const docs = [
  ["A-2", "特殊効果のスキーマ", "特殊効果の設定ファイルのキーと型"],
  ["A-3", "炎ノード", "炎を揺らしながら画面の下から重ねるノード"],
  ["A-4", "煙ノード", "薄い煙を流して奥行きを出すノード"],
  ["A-5", "光の粒ノード", "光の粒を散らして画面を明るく見せるノード"],
  ["A-6", "画面の揺れノード", "大きな出来事のときに画面全体を短く揺らすノード"],
  ["A-7", "特殊効果の重ね順の決め方", "複数のノードを重ねるときの前後の決め方と、同じ順のときの扱い"],
].map(([id, title, description]) => ({ kind: "docs", item: item(id!, title!, { description }) }) as const);

/** 調査 1 件 */
const research = {
  kind: "research",
  item: item("R-1", "特殊効果を重ねたときの描画の負荷", {
    description: "ノードを 1～8 個重ねたときの、OBS のブラウザソースのフレームレートの測り方と結果",
  }),
} as const;

/** 用語 1・資料 6・調査 1 に一致した印の項目 */
const many: MindmapPreview.TermTipEntry[] = [term, ...docs, research];

const meta = {
  title: "Preview/TermTip",
  render: ({ markTop, ...args }) => {
    // 本文の印（`a.term`）を持つ本文を置き、その印にツールチップを付ける
    const mark = document.createElement("a");
    mark.className = "term";
    mark.href = "#";
    mark.textContent = "特殊効果";
    const paragraph = document.createElement("p");
    paragraph.style.marginTop = markTop;
    paragraph.append("配信の画面に重ねる", mark, "を、ノードをつないで組み立てる。");
    const stage = document.createElement("div");
    stage.className = "md";
    stage.append(paragraph, MindmapPreview.termTip({ ...args, anchor: mark }));
    return stage;
  },
  // 文書に入ったあと、ツールチップを開く（開いたとき印の上に置く）
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>("[popover]")?.showPopover();
  },
  args: {
    entries: [term],
    anchor: document.createElement("a"),
    pinned: false,
    on: { open: fn(), close: fn() },
    markTop: "45vh",
  },
} satisfies Meta<Args>;

export default meta;

type Story = StoryObj<Args>;

/** 用語だけに一致した印。今と同じく用語・ID・意味だけを出し、リンクを持たない */
export const TermOnly: Story = {};

/** 用語・資料・調査に 1 件ずつ一致した印。種類ごとの見出しと区切り線で分け、全てのタイトルがリンクになる */
export const Few: Story = {
  args: { entries: [term, docs[0]!, research] },
};

/** 資料 1 件だけに一致した印。「資料 1」の見出しの下に 1 件 */
export const DocOnly: Story = {
  args: { entries: [docs[0]!] },
};

/** 説明を持たない資料。タイトルと ID だけを出す */
export const NoDescription: Story = {
  args: { entries: [term, { kind: "docs", item: item("A-9", "演出の一覧") }, docs[1]!] },
};

/** 用語 1・資料 6・調査 1 に一致した印。最大の高さ（360px）で止まり、中をスクロールして末尾の調査まで読める */
export const Many: Story = {
  args: { entries: many, markTop: "60vh" },
  play: ({ canvasElement }) => {
    const tip = canvasElement.querySelector<HTMLElement>("[popover]");
    tip?.showPopover();
    // 中を末尾までスクロールして見せる
    requestAnimationFrame(() => {
      if (tip !== null && tip !== undefined) tip.scrollTop = tip.scrollHeight;
    });
  },
};

/** 印の上に収まらない。印の下に出す */
export const Below: Story = {
  args: { entries: many, markTop: "8px" },
};

/** 上下どちらにも収まらない。広い側（上）に出してその高さに縮め、下端を印に留める */
export const Shrunk: Story = {
  args: { entries: many, markTop: "62vh" },
  parameters: {
    viewport: {
      options: { short: { name: "高さ 420px", styles: { width: "1000px", height: "420px" } } },
    },
  },
  globals: { viewport: { value: "short", isRotated: false } },
};

/** 用語 2 件だけに一致した印（ある用語のタイトルが別の用語の別名と同じ）。「用語 2」の見出しの下に 2 件を区切り線で分けて並べ、それぞれ用語・ID・意味を出してタイトルをリンクにする */
export const SeveralTerms: Story = {
  args: { entries: [term, { kind: "terms", item: item("G-2", "演出効果", { meaning: "特殊効果の別の言い方として使う用語" }) }] },
};

/** 印から Tab で中の最初のリンクへ移った。印の色の輪でフォーカスを示す */
export const LinkFocus: Story = {
  args: { entries: [term, docs[0]!, docs[1]!, research], pinned: true },
  play: ({ canvasElement }) => {
    canvasElement.querySelector<HTMLElement>("[popover]")?.showPopover();
    canvasElement.querySelector<HTMLElement>("a.tt-link")?.focus();
  },
};

/** 長いタイトル・説明を幅 390px で出す。折り返し、画面の端から 8px の内側に収める */
export const LongNarrow: Story = {
  args: {
    entries: [
      term,
      {
        kind: "docs",
        item: item(
          "A-10",
          "配信の途中で視聴者のコメントの量に合わせて特殊効果の強さを上げ下げするときの閾値と、急に変えないための遅らせ方",
          { description: "コメントの量を 10 秒ごとに数え、閾値をまたいだときだけ強さを 1 段ずつ変える" },
        ),
      },
      docs[1]!,
    ],
  },
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
