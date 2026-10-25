// 描画のライブラリ（雛形が CDN から読むグローバル）の型。npm の同じ版の型を割り当てる。出力しない。

/** Markdown を共通のスタイルで HTML に描き、無害化する mdmark（`loadMdmark` が ES モジュールを読んでグローバルに置く） */
declare const mdmark: {
  /** 要素の中に Markdown を描き、描き直しと片付けの関数を返す。描いたブロックは `data-source-line`（0 始まりのブロックの開始行）を持つ */
  mount: (
    el: HTMLElement,
    opts: { markdown: string; config?: { features?: Record<string, boolean> } },
  ) => { update: (markdown: string) => void; destroy: () => void };
  /** 読み込んだ mdmark のバージョン */
  version: () => string;
};

/** Markdown を HTML に描く marked（本文の差分の塊を分ける `marked.lexer` だけに使う） */
declare const marked: typeof import("marked").marked;

/** マップの配置を計算する ELK（`new ELK().layout(...)` で使う） */
declare const ELK: typeof import("elkjs").default;

/** 図を SVG に描く mermaid */
declare const mermaid: typeof import("mermaid").default;

/** 本文と図の差分を計算する jsdiff（`Diff.diffLines`・`Diff.diffArrays`） */
declare const Diff: typeof import("diff");
