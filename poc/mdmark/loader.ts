// PoC: 名前空間のスクリプトから mdmark の ES モジュールを読み、mindstella と重なる機能を止めて本文を描く。

namespace MindmapPreview {
  /** mdmark の mount が返す、描き直しと片付けの関数 */
  type MdmarkHandle = { update: (markdown: string) => void; destroy: () => void };

  /** mdmark のモジュールのうち、PoC で使う関数 */
  export type Mdmark = {
    mount: (el: HTMLElement, opts: { markdown: string; config?: { features?: Record<string, boolean> } }) => MdmarkHandle;
    version: () => string;
  };

  /** mindstella 側の機能と重なるため止める mdmark の機能 */
  export const MDMARK_FEATURES_OFF: Record<string, boolean> = {
    glossary: false,
    backlinks: false,
    comments: false,
    print: false,
    anchors: false,
    sections: false,
    table: false,
    toc: false,
    views: false,
  };

  /** URL の mdmark を動的 import で読む */
  export function loadMdmark(url: string): Promise<Mdmark> {
    return import(url) as Promise<Mdmark>;
  }

  /** ページの中に持った mdmark の JavaScript を、Blob の URL にして動的 import で読む（配る書き出し） */
  export function loadMdmarkFromSource(source: string): Promise<Mdmark> {
    const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
    return import(url) as Promise<Mdmark>;
  }

  /** 要素の中に、重なる機能を止めた mdmark で本文を描く */
  export function mountMdmark({ mdmark, el, markdown }: { mdmark: Mdmark; el: HTMLElement; markdown: string }): MdmarkHandle {
    return mdmark.mount(el, { markdown, config: { features: MDMARK_FEATURES_OFF } });
  }
}
