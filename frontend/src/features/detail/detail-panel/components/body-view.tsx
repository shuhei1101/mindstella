// 本文の節。mdmark が描いた本文に見出しのリンク・本文の印・図を当て、差分の表示の間は本文と図の差分を重ねる（React の外の DOM を `useEffect` の中で組む）
import { useCallback } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { BodyDiffLayoutSwitch } from "@/shared/components/body-diff-layout-switch";
import { DomHost } from "@/shared/components/dom-host";
import { DIAGRAM_SOURCE_ATTR, libraryNotice, linkBody, linkHeadings, renderDiagrams, renderMarkdown } from "@/shared/core/body-links";
import { BEFORE_SOURCE_ATTR, decorateDiagrams, drawHtmlBlocks, headingShift, HTML_BODY_ATTR, lowerHeadings, noteBox, renderBodyDiff, replaceChangedRanges, withoutLineMarks } from "@/shared/core/body-render";
import { LINE_DIFF_TIMEOUT_MS, type VersionPair } from "@/shared/core/diff";
import { h } from "@/shared/core/dom-parts";
import { htmlBodyDiff } from "@/shared/core/html-body-diff";
import { htmlFrameElement } from "@/shared/core/html-frame";
import { bindTableHeads, decorateMarkdown, type BodyView as BodyDisplay } from "@/shared/core/markdown-decorate";
import { bodyFormatOf, type Item, type RecordIndex } from "@/shared/core/records";
import { sideBySideBodyDiff } from "@/shared/core/side-by-side";
import { attachTermTips, scrollToHeading } from "@/shared/core/term-tips";

const NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。";
const NOTE_BODY_TOO_LARGE = "本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。";

/** 本文の差分の並べ方 */
export type BodyLayout = "inline" | "side";

export type BodyViewProps = {
  label: string;
  item: Item;
  /** 開いている項目（本文の印から自分を除く） */
  id: string;
  index: RecordIndex;
  source: string;
  versions: VersionPair | null;
  layout: BodyLayout;
  display: BodyDisplay;
  heading: string | undefined;
  onOpen: (id: string) => void;
  onHeading: (slug: string | undefined) => void;
  onChangeSet: (id: string) => void;
  onLayout: (layout: BodyLayout) => void;
  onDiagram: (svg: SVGElement, beforeSource: string | null) => void;
};

export const BodyView = ({ label, item, id, index, source, versions, layout, display, heading, onOpen, onHeading, onChangeSet, onLayout, onDiagram }: BodyViewProps) => {
  const mdmark = useLibrary("mdmark").status;
  const jsdiff = useLibrary("jsdiff").status;
  const marked = useLibrary("marked").status;
  const mermaid = useLibrary("mermaid").status;
  const html = bodyFormatOf(item.body) === "html";
  const current = index.data.bodies[item.body ?? ""];
  const comparing = versions !== null && versions.before !== null && !versions.trimmed;
  const before = comparing ? versions.beforeBody : null;
  const canLayout = comparing && before !== null && before !== source && jsdiff === "ready";
  const create = useCallback(() => {
    const wrapper = h({ tag: "div" });
    const notes: HTMLElement[] = [];
    if (comparing && jsdiff !== "ready") notes.push(libraryNotice({ names: ["jsdiff"], what: "本文と図の差分" }));
    else if (comparing && before === null) notes.push(noteBox(NOTE_BODY_UNAVAILABLE));
    if (html) {
      const marks = index.data.marked_bodies?.[item.body ?? ""];
      const lined = source === current && marks !== undefined;
      const drawn = lined ? marks : source;
      let content: HTMLElement | null = null;
      if (comparing && jsdiff === "ready" && before !== null && before !== source) {
        content = htmlBodyDiff({ before, after: source, marked: drawn, beforeFormat: bodyFormatOf(versions.before?.body) === "md" ? "md" : "html", layout });
        if (content === null) notes.push(noteBox(NOTE_BODY_TOO_LARGE));
      }
      const frame = content ?? htmlFrameElement({ source: drawn, selectable: false });
      if (frame instanceof HTMLIFrameElement) frame.setAttribute(HTML_BODY_ATTR, "");
      wrapper.append(...notes, frame);
      return { node: wrapper };
    }
    let rendered: HTMLElement | null = null;
    let markWords: (() => void) | null = null;
    let side: ReturnType<typeof sideBySideBodyDiff> = null;
    if (comparing && jsdiff === "ready" && before !== null) {
      const deadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
      const diff = renderBodyDiff({ before, after: source, deadline });
      rendered = diff?.root ?? null;
      markWords = diff?.markWords ?? null;
      if (rendered === null) notes.push(noteBox(NOTE_BODY_TOO_LARGE));
      else if (before !== source && layout === "side" && marked === "ready") {
        side = sideBySideBodyDiff({ before, after: source, lined: source === current, deadline });
        if (side === null) notes.push(noteBox(NOTE_BODY_TOO_LARGE));
      }
    }
    const root = rendered ?? renderMarkdown(source);
    if (rendered === null) lowerHeadings({ root, shift: headingShift({ roots: [root] }) });
    if (rendered !== null && before !== null) replaceChangedRanges({ root, before, after: source });
    if (source !== current) withoutLineMarks(root);
    const link = (target: HTMLElement, text: string): void => {
      linkHeadings({
        root: target,
        onHeading: (slug) => {
          scrollToHeading({ root: target, slug });
          onHeading(slug);
        },
        onChangeSet,
      });
      linkBody({ root: target, index, selfId: id, onOpen, source: text });
      drawHtmlBlocks(target);
    };
    link(root, source);
    decorateMarkdown({ root, display, fold: rendered === null });
    for (const [position, column] of (side?.columns ?? []).entries()) {
      link(column, position === 0 ? (before ?? source) : source);
      decorateMarkdown({ root: column, display, fold: false });
    }
    markWords?.();
    side?.markWords();
    attachTermTips({ root, index, onOpen });
    const drawn = renderDiagrams(root);
    if (before !== null) void drawn.then(() => { decorateDiagrams({ root, before }); });
    if (side !== null) {
      const view = side;
      void renderDiagrams(view.root).then(() => { view.decorate(); });
      root.classList.add("sbs-fallback");
    }
    const onDiagramTool = (event: Event): void => {
      const button = (event.target as Element).closest<HTMLElement>("[data-act]");
      const figure = button?.closest<HTMLElement>(".diagram");
      if (button === null || button === undefined || figure === null || figure === undefined) return;
      const act = button.dataset["act"];
      if (act === "diagram-zoom") {
        const svg = figure.querySelector<SVGElement>(".mermaid svg");
        if (svg !== null) onDiagram(svg, figure.getAttribute(BEFORE_SOURCE_ATTR));
      } else if (act === "diagram-raw") {
        const pressed = button.getAttribute("aria-pressed") !== "true";
        button.setAttribute("aria-pressed", String(pressed));
        figure.querySelector<HTMLElement>(".mermaid")?.toggleAttribute("hidden", pressed);
        figure.querySelector<HTMLElement>(".dg-raw")?.toggleAttribute("hidden", !pressed);
      } else if (act === "diagram-copy") {
        void navigator.clipboard.writeText(figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "");
      }
    };
    wrapper.addEventListener("click", onDiagramTool);
    wrapper.append(...notes, ...(side === null ? [] : [side.root]), root);
    // 文書に入れた後に、見出しへ送り、表の見出しの固定をつなぐ
    let release: (() => void) | undefined;
    const frame = requestAnimationFrame(() => {
      const scroller = wrapper.closest<HTMLElement>(".panel-body");
      if (scroller !== null) release = bindTableHeads(scroller);
      if (heading !== undefined && !scrollToHeading({ root, slug: heading })) onHeading(undefined);
    });
    return {
      node: wrapper,
      destroy: () => {
        cancelAnimationFrame(frame);
        release?.();
      },
    };
    // heading の変更では描き直さない（見出しのリンクが送る）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mdmark, jsdiff, marked, mermaid, html, source, current, comparing, before, layout, display, index, id, item.body]);
  return (
    <section className="flex flex-col gap-1">
      <h3 className="text-small font-semibold">{label}</h3>
      {canLayout ? <BodyDiffLayoutSwitch layout={layout} onChange={onLayout} /> : null}
      <DomHost create={create} />
    </section>
  );
};
