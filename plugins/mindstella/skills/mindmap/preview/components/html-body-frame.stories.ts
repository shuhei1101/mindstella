// HTML の本文の枠のストーリー（部品設計『HTMLの本文の枠』の状態）。

import type { Meta, StoryObj } from "@storybook/html-vite";

/** 見出し・段落・表・図を持つ本文（行の印つき） */
const RENDERED = [
  "<style>table { border-collapse: collapse } td, th { border: 1px solid #999; padding: 4px 8px }</style>",
  '<h1 data-line="2">画面の流れ</h1>',
  '<p data-line="3">一覧から詳細を開く流れです。</p>',
  '<table data-line="4"><tr data-line="4"><th data-line="4">画面</th><th data-line="4">操作</th></tr><tr data-line="5"><td data-line="5">一覧</td><td data-line="5">1 件を選ぶ</td></tr></table>',
  '<svg data-line="6" width="240" height="60" viewBox="0 0 240 60" role="img" aria-label="一覧から詳細へ"><rect x="4" y="12" width="90" height="36" fill="#dbeafe" stroke="#2563eb"/><rect x="146" y="12" width="90" height="36" fill="#dcfce7" stroke="#16a34a"/><path d="M94 30h52" stroke="#444"/></svg>',
].join("\n");

/** 本文の `<style>` が `*`・`body`・`p` を塗る本文 */
const STYLE_ISOLATED =
  '<style>* { margin: 40px !important } body, p { color: rgb(255, 0, 0) !important; background: rgb(0, 0, 255) !important }</style>\n<p data-line="2">枠の中の段落</p>';

/** スクリプトを持つ本文 */
const WITH_SCRIPTS = [
  '<h1 data-line="1">保存のボタンの見本</h1>',
  '<p data-line="2">下のボタンを押しても何も起きません。</p>',
  '<script>document.body.append("スクリプトが動きました")</script>',
  '<img data-line="4" src="data:," onerror="document.body.append(\'画像のエラーが動きました\')">',
  '<button data-line="5" type="button" onclick="document.body.append(\'ボタンが動きました\')">保存</button>',
].join("\n");

/** 差分の印を付ける本文 */
const DIFF_BODY = [
  '<h1 data-line="1">画面の流れ</h1>',
  '<p data-line="2">一つ目の段落</p>',
  '<p data-line="3">変えた二つ目の段落</p>',
  '<p data-line="4">三つ目の段落</p>',
  '<p data-line="5">足した四つ目の段落</p>',
].join("\n");

const meta = {
  title: "Preview/HtmlBodyFrame",
  render: (args) => {
    const stage = document.createElement("div");
    stage.append(MindmapPreview.htmlBodyFrame(args));
    return stage;
  },
  args: { source: RENDERED },
} satisfies Meta<MindmapPreview.HtmlBodyFrameProps>;

export default meta;

type Story = StoryObj<MindmapPreview.HtmlBodyFrameProps>;

/** 見出し・段落・表・`<svg>` の図を持つ本文。枠の高さが中身に合い、枠の中にスクロールの帯が出ない。地は白で、ダークでも資料の色のまま */
export const Rendered: Story = {};

/** 本文の `<style>` が `*`・`body`・`p` の色と余白を `!important` で塗っても、枠の外の見本の段落・見出しは変わらない */
export const StyleIsolated: Story = {
  args: { source: STYLE_ISOLATED },
  render: (args) => {
    const stage = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = "枠の外の見出し";
    const paragraph = document.createElement("p");
    paragraph.textContent = "枠の外の段落";
    stage.append(heading, paragraph, MindmapPreview.htmlBodyFrame(args));
    return stage;
  },
};

/** 描く前。枠は 120px の高さを取り、描いた後に中身の高さへ伸びる */
export const Loading: Story = {
  render: (args) => {
    const stage = document.createElement("div");
    // 描く前の枠（本文を渡さず、高さを合わせる動きも付けない）。CSS の 120px の高さを見せる
    stage.append(
      MindmapPreview.h({
        tag: "iframe",
        attrs: { class: "html-frame", sandbox: "allow-same-origin", title: args.label ?? "本文（HTML）" },
      }),
    );
    return stage;
  },
};

/** `<script>`・`onerror` の画像・`onclick` のボタンを持つ本文。見出し・段落は描き、ボタンを押しても何も起きない */
export const WithScripts: Story = { args: { source: WITH_SCRIPTS } };

/** Markdown の中の `html` のコードブロック。行の印を持たず、枠の中で選んでも「選び終えた」を知らせない */
export const CodeBlock: Story = {
  args: { source: "<p>コードブロックの HTML</p>", selectable: false, label: "html のコードブロック" },
};

/** 2 つ目の段落を変え、4 つ目の段落を足した本文。変えた段落に破線、足した段落に実線の印を付け、ほかの段落には付けない */
export const DiffMarks: Story = { args: { source: DIFF_BODY, marks: { added: [5], changed: [3] } } };

/** 幅 390px。本文の図・表が枠の幅に収まる */
export const Narrow: Story = {
  parameters: {
    viewport: {
      options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } },
    },
  },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
