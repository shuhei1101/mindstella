// 描画のライブラリ（marked・DOMPurify・elkjs・mermaid）と差分のライブラリ（jsdiff）の有無と呼び出し、選んだ範囲から箇所を求める処理。読めなかったときは名前を出し、代わりの読み込みはしない。

namespace MindmapPreview {
  /** 描画のライブラリの名前 → 読めたときに置かれるグローバルの名前 */
  export const LIBRARIES = {
    marked: "marked",
    DOMPurify: "DOMPurify",
    elkjs: "ELK",
    mermaid: "mermaid",
    jsdiff: "Diff",
  } as const;

  /** 描画のライブラリの名前 */
  export type LibraryName = keyof typeof LIBRARIES;

  /** 図の入れ物が原文を持つ属性の名前 */
  export const DIAGRAM_SOURCE_ATTR = "data-source";

  /** 渡したライブラリのうち、グローバルが無いものの名前を返す（渡した順） */
  export function missingLibraries(names: LibraryName[]): LibraryName[] {
    return names.filter((name) => Reflect.get(window, LIBRARIES[name]) === undefined);
  }

  /** 読めなかったライブラリの名前を出す知らせの要素を返す */
  export function libraryNotice({ names, what }: { names: string[]; what: string }): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "lib-error", role: "alert" },
      children: [
        h({ tag: "span", children: [`${what}を表示できません。読み込めなかったライブラリ: ${names.join("・")}`] }),
        h({ tag: "span", attrs: { class: "muted" }, children: ["通信を確認して、ページを再読み込みしてください。"] }),
      ],
    });
  }

  // ─── 本文の行の印 ───

  /** 本文のブロックの要素が持つ、元の Markdown の先頭の行（1 始まり）の属性 */
  export const LINE_ATTR = "data-line-start";

  /** 項目の値を描いた要素が持つ、項目のキーのパスの属性 */
  export const VALUE_KEY_ATTR = "data-key";

  /** marked の token に、元の Markdown の先頭の行（0 始まり）を持たせた形 */
  type LinedToken = { raw: string; type: string; tokens?: LinedToken[]; items?: LinedToken[]; line?: number };

  /** 改行の数を返す */
  function countNewlines(text: string): number {
    return text.split("\n").length - 1;
  }

  /** token の並びに、先頭の行から raw の改行を足し進めた行を持たせる（リストの項目・引用の中も同じ） */
  function assignLines({ tokens, start }: { tokens: LinedToken[]; start: number }): void {
    let line = start;
    for (const token of tokens) {
      token.line = line;
      if (token.type === "list" && token.items) {
        assignLines({ tokens: token.items, start: line });
      } else if ((token.type === "list_item" || token.type === "blockquote") && token.tokens) {
        // 項目の中の token は字下げを外した raw を持つが、改行の数は元と同じ
        assignLines({ tokens: token.tokens, start: line });
      }
      line += countNewlines(token.raw);
    }
  }

  /** token が持つ行を返す */
  function lineOf(token: object): number | undefined {
    return (token as LinedToken).line;
  }

  /** 描いた HTML の最初の開きタグに、行の印を足す */
  function withLine(html: string, line: number | undefined): string {
    if (line === undefined) return html;
    return html.replace(/^<(\w+)/, `<$1 ${LINE_ATTR}="${line + 1}"`);
  }

  /** 本文の Markdown を、空行を持たないブロックごとに行の印を付けて HTML に描く */
  export function renderWithLines(source: string): string {
    const tokens = marked.lexer(source);
    assignLines({ tokens: tokens as unknown as LinedToken[], start: 0 });
    const renderer = new marked.Renderer();
    const base = {
      heading: renderer.heading.bind(renderer),
      paragraph: renderer.paragraph.bind(renderer),
      code: renderer.code.bind(renderer),
      listitem: renderer.listitem.bind(renderer),
      table: renderer.table.bind(renderer),
    };
    renderer.heading = (token) => withLine(base.heading(token), lineOf(token));
    renderer.paragraph = (token) => withLine(base.paragraph(token), lineOf(token));
    // mermaid の図は印を付けない（図の中の選択を本文の外として扱う）
    // フェンスで囲んだコードは、中身がフェンスの次の行から始まる
    renderer.code = (token) => {
      if (token.lang === "mermaid") return base.code(token);
      const line = lineOf(token);
      const fence = token.codeBlockStyle === "indented" ? 0 : 1;
      return withLine(base.code(token), line === undefined ? undefined : line + fence);
    };
    // 段落を持つ項目は中の段落が印を持つので、段落を持たない項目だけ li に付ける
    renderer.listitem = (item) => (item.loose ? base.listitem(item) : withLine(base.listitem(item), lineOf(item)));
    // 表は行ごとに 1 行。見出しの行の次に区切りの行がある
    renderer.table = (token) => {
      const start = lineOf(token);
      if (start === undefined) return base.table(token);
      let row = 0;
      return base.table(token).replace(/<tr>/g, () => {
        const line = row === 0 ? start : start + 1 + row;
        row += 1;
        return `<tr ${LINE_ATTR}="${line + 1}">`;
      });
    };
    return marked.parser(tokens, { renderer });
  }

  /** 印を持つブロックの先頭から、選択の端までにある改行（文の \n と br）の数を返す */
  function linesBefore({ block, node, offset }: { block: Element; node: Node; offset: number }): number {
    // 表の行は 1 行で、セルの間の空白の改行は数えない
    if (block.tagName === "TR") return 0;
    const range = document.createRange();
    range.setStart(block, 0);
    range.setEnd(node, offset);
    const fragment = range.cloneContents();
    return countNewlines(fragment.textContent ?? "") + fragment.querySelectorAll("br").length;
  }

  /** 選択の端から、本文の中で印を持つ最も近いブロックを返す（本文の外なら null） */
  function lineBlock(node: Node): Element | null {
    const element = node instanceof Element ? node : node.parentElement;
    const block = element?.closest(`[${LINE_ATTR}]`) ?? null;
    return block?.closest(".md") ? block : null;
  }

  /** 選んだ範囲を、本文なら元の Markdown の行の範囲、値ならキーのパスの箇所にする。本文と値の外・空の選択は null */
  export function selectionLocation(range: Range): Location | null {
    if (range.collapsed) return null;
    const text = range.toString().trim();
    // 文が空白だけ
    if (text === "") return null;
    // 始点と終点が同じ値の中: 値の箇所
    const startKey = keyElement(range.startContainer);
    if (startKey !== null && startKey === keyElement(range.endContainer)) {
      return { kind: "value", key: startKey.getAttribute(VALUE_KEY_ATTR) ?? "", text };
    }
    const startBlock = lineBlock(range.startContainer);
    const endBlock = lineBlock(range.endContainer);
    // 本文の外
    if (!startBlock || !endBlock) return null;
    const first = Number(startBlock.getAttribute(LINE_ATTR));
    const last = Number(endBlock.getAttribute(LINE_ATTR));
    return {
      kind: "body",
      start: first + linesBefore({ block: startBlock, node: range.startContainer, offset: range.startOffset }),
      end: last + linesBefore({ block: endBlock, node: range.endContainer, offset: range.endOffset }),
      text,
    };
  }

  /** 選択の端から、値のキーのパスを持つ最も近い要素を返す（無ければ null） */
  function keyElement(node: Node): Element | null {
    const element = node instanceof Element ? node : node.parentElement;
    return element?.closest(`[${VALUE_KEY_ATTR}]`) ?? null;
  }

  /** 項目の文字列の値の Markdown を無害化した要素にする。marked か DOMPurify が読めないときは文字のまま返す（知らせは本文の描画が出す） */
  export function renderValue(source: string): HTMLElement | string {
    if (missingLibraries(["marked", "DOMPurify"]).length > 0) return source;
    const root = h({ tag: "div", attrs: { class: "md md-value" } });
    // 描いた HTML は無害化してから差し込む（記録は利用者のもの）。行の印は付けず、mermaid のコードブロックも図にしない
    root.innerHTML = DOMPurify.sanitize(marked.parse(source, { async: false }));
    return root;
  }

  /** 本文の Markdown を無害化した要素にする。mermaid のコードブロックは図の入れ物に置き換える */
  export function renderMarkdown(source: string): HTMLElement {
    const root = h({ tag: "div", attrs: { class: "md" } });
    const missing = missingLibraries(["marked", "DOMPurify"]);
    const hasDiagram = source.includes("```mermaid");
    // marked か DOMPurify が読めていない: 知らせと原文を出す
    if (missing.length > 0) {
      const names: string[] = [...missing];
      if (hasDiagram && missingLibraries(["mermaid"]).length > 0) names.push("mermaid");
      root.append(
        libraryNotice({ names, what: "本文" }),
        h({ tag: "pre", attrs: { class: "md-raw" }, children: [source] }),
      );
      return root;
    }
    // 描いた HTML は無害化してから差し込む（記録は利用者のもの）
    root.innerHTML = DOMPurify.sanitize(renderWithLines(source));
    // mermaid のコードブロックを、原文を持つ図の入れ物（拡大・Raw・コピーの道具つき）に置き換える
    for (const code of root.querySelectorAll("code.language-mermaid")) {
      const original = code.textContent ?? "";
      const figure = h({
        tag: "figure",
        attrs: { class: "diagram" },
        children: [
          h({
            tag: "div",
            attrs: { class: "dg-tools" },
            children: [
              h({
                tag: "button",
                attrs: { class: "icon-btn", type: "button", "data-act": "diagram-zoom", "aria-label": "図を拡大表示", title: "拡大表示" },
                children: [icon("expand")],
              }),
              h({
                tag: "button",
                attrs: { class: "btn ghost", type: "button", "data-act": "diagram-raw", "aria-pressed": "false" },
                children: ["Raw"],
              }),
              h({
                tag: "button",
                attrs: { class: "icon-btn", type: "button", "data-act": "diagram-copy", "aria-label": "原文をコピー", title: "コピー" },
                children: [icon("copy")],
              }),
            ],
          }),
          h({ tag: "div", attrs: { class: "mermaid", [DIAGRAM_SOURCE_ATTR]: original } }),
          h({ tag: "pre", attrs: { class: "dg-raw", hidden: true }, children: [original] }),
        ],
      });
      (code.closest("pre") ?? code).replaceWith(figure);
    }
    return root;
  }

  /** 見出しの文言から、見出しを指す名前を作る（前後の空白を除き、間の空白の並びを `-` 1 つにする。同じ名前の 2 つ目から `-1`・`-2` を続ける）。`seen` は同じ本文でこれまでに作った名前 → 出た回数で、呼ぶたびに書き換える */
  export function headingSlug({ text, seen }: { text: string; seen: Map<string, number> }): string {
    const base = text.trim().replace(/\s+/g, "-");
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    return count === 0 ? base : `${base}-${count}`;
  }

  /** 今のハッシュの `id`・`h` を替えた URL のハッシュ（キーボードとリンクのコピーで使うリンク先。押したときは使う側の移動に替える） */
  function hashWith({ id, heading }: { id?: string; heading: string | null }): string {
    const params = new URLSearchParams(location.hash.replace(/^#/, ""));
    if (id !== undefined) params.set("id", id);
    if (heading === null) params.delete("h");
    else params.set("h", heading);
    return `#${params.toString()}`;
  }

  /** 描いた本文の見出しに、見出しを指す名前（`data-heading`）と右の # のリンクを付け、本文の中の `#見出し` のリンクをその見出しへの移動にする。押したときは既定の動作を止め、見出しの名前を `onHeading` に知らせる */
  export function linkHeadings({ root, onHeading }: { root: HTMLElement; onHeading: (slug: string) => void }): void {
    // 本文の中の `[文言](#見出し)` のリンク（# のリンクを足す前の分）。同じ名前の見出しがあるときだけ知らせ、無ければ何もしない
    const bodyLinks = [...root.querySelectorAll<HTMLAnchorElement>("a[href^='#']")];
    const seen = new Map<string, number>();
    for (const heading of root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")) {
      const text = heading.textContent ?? "";
      const slug = headingSlug({ text, seen });
      heading.dataset["heading"] = slug;
      heading.append(
        h({
          tag: "a",
          attrs: {
            class: "h-link",
            href: hashWith({ heading: slug }),
            "aria-label": `見出し「${text.trim()}」へのリンク`,
            onclick: (event: Event) => {
              event.preventDefault();
              onHeading(slug);
            },
          },
          children: [icon("hash")],
        }),
      );
    }
    for (const link of bodyLinks) {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const raw = (link.getAttribute("href") ?? "").slice(1);
        let decoded = raw;
        try {
          decoded = decodeURIComponent(raw);
        } catch {
          // 戻せない文字列は、そのまま見出しの名前として探す
        }
        const slug = headingSlug({ text: decoded, seen: new Map() });
        if (root.querySelector(`[data-heading="${CSS.escape(slug)}"]`) !== null) onHeading(slug);
      });
    }
  }

  /** 英数字と記号だけの用語か（ファイル名・識別子の一部に当てないよう、語の切れ目でだけ当てる） */
  const ASCII_TERM = /^[!-~ ]+$/;

  /** 描いた本文の文中の、用語集の用語を印に、記録にある項目の ID をリンクにする。`pre`・図・リンク・見出しの中は飛ばし、インラインコードは中身がちょうど用語か ID のときだけ当てる。押したときは既定の動作を止め、その項目の ID を `onOpen` に知らせる */
  export function linkBody({
    root,
    index,
    selfId,
    onOpen,
  }: {
    root: HTMLElement;
    index: RecordIndex;
    selfId: string;
    onOpen: (id: string) => void;
  }): void {
    // 項目自身の用語と、タイトルが空の用語には付けない。長い用語から順に当てる
    const terms = index.data.terms
      .filter((term) => term.id !== selfId && term.title.trim() !== "")
      .sort((a, b) => b.title.length - a.title.length);
    const byTitle = new Map(terms.map((term) => [term.title, term]));
    const escape = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const termPattern = (title: string): string =>
      ASCII_TERM.test(title) ? `(?<![A-Za-z0-9_.-])${escape(title)}(?![A-Za-z0-9_-])` : escape(title);
    // 項目の ID（英大文字 - 数字。前後が英数字のものは当てない）と、長い用語の順
    const pattern = new RegExp(["(?<![A-Za-z0-9-])[A-Z]+-[0-9]+(?![0-9])", ...terms.map((term) => termPattern(term.title))].join("|"), "g");
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) =>
        node.parentElement?.closest("pre, figure, a, button, svg, .mermaid, h1, h2, h3, h4, h5, h6") !== null
          ? NodeFilter.FILTER_REJECT
          : NodeFilter.FILTER_ACCEPT,
    });
    const nodes: Text[] = [];
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) nodes.push(node as Text);
    for (const node of nodes) {
      const text = node.textContent ?? "";
      // インラインコードは、中身がちょうど用語か ID のときだけ（パスや識別子の一部には付けない）
      const inCode = node.parentElement?.closest("code") !== null;
      const parts: (Node | string)[] = [];
      let last = 0;
      for (const match of text.matchAll(pattern)) {
        const word = match[0];
        const term = byTitle.get(word);
        const isId = term === undefined;
        // 記録に無い ID・項目自身の ID・コードの一部は、そのままにする
        if ((isId && (!index.byId.has(word) || word === selfId)) || (inCode && text.trim() !== word)) continue;
        const target = isId ? word : term.id;
        parts.push(
          text.slice(last, match.index),
          h({
            tag: "a",
            attrs: {
              class: isId ? "idref" : "term",
              href: hashWith({ id: target, heading: null }),
              "data-id": target,
              "aria-describedby": isId ? null : TERM_TIP_ID,
              onclick: (event: Event) => {
                event.preventDefault();
                onOpen(target);
              },
            },
            children: [word],
          }),
        );
        last = (match.index ?? 0) + word.length;
      }
      if (parts.length === 0) continue;
      parts.push(text.slice(last));
      node.replaceWith(...parts.filter((part) => part !== ""));
    }
  }

  /** 用語のツールチップの要素の id（用語の印の `aria-describedby` が指す） */
  export const TERM_TIP_ID = "term-tip";

  /** mermaid を初期化したときの、地の色（変わったら初期化し直す） */
  let initializedFor: string | null = null;

  /** 図の ID を作る連番 */
  let diagramCounter = 0;

  /** 直前の `renderDiagrams` で描いた・写した図（記法 → mermaid の出力と、その SVG の ID） */
  let lastDrawn = new Map<string, { svg: string; id: string }>();

  /** 図の ID を新しく振る */
  function nextDiagramId(): string {
    return `mindmap-diagram-${(diagramCounter += 1)}`;
  }

  /** 色の値をトークンから引く */
  function token(name: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /** 初めて描くとき（と、テーマが変わったとき）に、トークンの色で mermaid を初期化する */
  function initializeMermaid(): void {
    // 初めて描くとき（と、テーマが変わったとき）に、トークンの色で初期化する
    const surface = token("--surface");
    if (initializedFor !== surface) {
      // 図の変数 → 色のトークン（トークンが無い文書では、mermaid の既定の色に任せる）
      const colorTokens: Record<string, string> = {
        background: "--surface",
        primaryColor: "--surface-2",
        primaryTextColor: "--text",
        primaryBorderColor: "--border",
        secondaryColor: "--surface-2",
        tertiaryColor: "--surface",
        lineColor: "--text-2",
        textColor: "--text",
        edgeLabelBackground: "--surface",
        clusterBkg: "--surface-2",
        clusterBorder: "--border",
      };
      const themeVariables = Object.fromEntries(
        Object.entries(colorTokens)
          .map(([variable, name]) => [variable, token(name)] as const)
          .filter(([, color]) => color !== ""),
      );
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "base",
        fontFamily: "Noto Sans JP, sans-serif",
        themeVariables,
      });
      initializedFor = surface;
      // 古いテーマの色で描いた SVG は使い回さない
      lastDrawn = new Map();
    }
  }

  /** 記法を mermaid で SVG に描いて返す（画面には出さない）。mermaid が読めていないか、描けないときは null */
  export async function renderDiagramSvg(source: string): Promise<SVGElement | null> {
    if (missingLibraries(["mermaid"]).length > 0) return null;
    initializeMermaid();
    const id = nextDiagramId();
    try {
      const { svg } = await mermaid.render(id, source);
      const holder = document.createElement("template");
      holder.innerHTML = svg;
      return holder.content.firstElementChild as SVGElement;
    } catch {
      // 描けなかった図: mermaid が body に残した作業用の要素を消す
      document.getElementById(`d${id}`)?.remove();
      document.getElementById(id)?.remove();
      return null;
    }
  }

  /** 要素の中の図の入れ物を mermaid で SVG に描く。描けない図は原文を残し、ほかの図は続ける */
  export async function renderDiagrams(root: HTMLElement): Promise<void> {
    const containers = [...root.querySelectorAll<HTMLElement>(`[${DIAGRAM_SOURCE_ATTR}]`)];
    // mermaid が読めていない: 各入れ物に知らせと原文を入れる
    if (missingLibraries(["mermaid"]).length > 0) {
      for (const container of containers) {
        container.replaceChildren(
          libraryNotice({ names: ["mermaid"], what: "図" }),
          h({
            tag: "pre",
            attrs: { class: "dg-raw" },
            children: [container.getAttribute(DIAGRAM_SOURCE_ATTR) ?? ""],
          }),
        );
      }
      return;
    }
    initializeMermaid();
    // この呼び出しで描いた・写した図だけを、次の呼び出しのために覚える
    const drawn = new Map<string, { svg: string; id: string }>();
    for (const container of containers) {
      const source = container.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
      const id = nextDiagramId();
      try {
        // 直前に描いた同じ記法の図: 描き直さず、新しい ID に置き換えて写す（同じ図が文書に 2 つあっても ID と参照が重ならない）
        const reused = lastDrawn.get(source);
        const svg =
          reused === undefined
            ? (await mermaid.render(id, source)).svg
            : reused.svg.replace(new RegExp(`${reused.id}(?![0-9])`, "g"), id);
        container.innerHTML = svg;
        drawn.set(source, { svg, id });
      } catch {
        // 描けなかった図: mermaid が body に残した作業用の要素を消し、描けなかったことと原文を入れる
        document.getElementById(`d${id}`)?.remove();
        document.getElementById(id)?.remove();
        container.replaceChildren(
          h({ tag: "p", attrs: { class: "md-error" }, children: ["この図は表示できませんでした。原文を表示します。"] }),
          h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }),
        );
      }
    }
    lastDrawn = drawn;
  }
}
