// 本文の節。mdmark が描いた本文に見出しのリンク・本文のマーカー・図を当て、差分の表示の間は mdmark の差分と図の差分で描く（React の外の DOM を `useEffect` の中で組む）
import { useCallback } from "react";

import { getLibrary, useLibrary } from "@/shared/adapters/libraries";
import { BodyDiffViewSwitch, type BodyDiffView } from "@/shared/components/body-diff-view-switch";
import { DomHost } from "@/shared/components/dom-host";
import { DIAGRAM_SOURCE_ATTR, libraryNotice, linkBody, linkHeadings, renderDiagrams, renderMarkdown } from "@/shared/core/body-links";
import { BEFORE_SOURCE_ATTR, decorateDiagrams, drawHtmlBlocks, headingShift, HTML_BODY_ATTR, lowerHeadings, noteBox, replaceChangedRanges, withoutLineMarks } from "@/shared/core/body-render";
import { diffLineParts, type JsDiff, type VersionPair } from "@/shared/core/diff";
import { h } from "@/shared/core/dom-parts";
import { htmlBodyDiff } from "@/shared/core/html-body-diff";
import { htmlFrameElement } from "@/shared/core/html-frame";
import { decorateMarkdown, type BodyView as BodyDisplay } from "@/shared/core/markdown-decorate";
import { bodyFormatOf, type Item, type RecordIndex } from "@/shared/core/records";
import { attachTermTips, scrollToHeading } from "@/shared/core/term-tips";

const NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。";
const NOTE_BODY_TOO_LARGE = "本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。今の本文を出しています。";

export type BodyViewProps = {
  label: string;
  item: Item;
  /** 開いている項目（本文の印から自分を除く） */
  id: string;
  index: RecordIndex;
  source: string;
  versions: VersionPair | null;
  /** Markdown の本文の差分の見せ方 */
  view: BodyDiffView;
  /** 見せ方を選んだ回数。押している方を押し直したときも変わり、描き直す */
  viewNonce: number;
  display: BodyDisplay;
  heading: string | undefined;
  onOpen: (id: string) => void;
  onHeading: (slug: string | undefined) => void;
  onChangeSet: (id: string) => void;
  onView: (view: BodyDiffView) => void;
  onDiagram: (figure: { svg: SVGElement; source: string | null; beforeSource: string | null; notes: string | null; framed: boolean }) => void;
};

export const BodyView = ({ label, item, id, index, source, versions, view, viewNonce, display, heading, onOpen, onHeading, onChangeSet, onView, onDiagram }: BodyViewProps) => {
  const mdmark = useLibrary("mdmark").status;
  const jsdiff = useLibrary("jsdiff").status;
  const mermaid = useLibrary("mermaid").status;
  const html = bodyFormatOf(item.body) === "html";
  const current = index.data.bodies[item.body ?? ""];
  const comparing = versions !== null && versions.before !== null && !versions.trimmed;
  const before = comparing ? versions.beforeBody : null;
  /** 選んだ時点の本文（今の本文と違うときだけ。同じなら色を付けずに描く） */
  const base = comparing && before !== null && before !== source ? before : null;
  const changed = base !== null;
  // eslint-disable-next-line sonarjs/cognitive-complexity -- 分岐を 1 か所で読めるように保つ
  const create = useCallback(() => {
    // Markdown の本文は mdmark を読み終えてから描く（読めなかったときは原文と知らせを出す）
    if (!html && mdmark === "loading") return { node: null };
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
        content = htmlBodyDiff({ before, after: source, marked: drawn, beforeFormat: bodyFormatOf(versions.before?.body) === "md" ? "md" : "html" });
        if (content === null) notes.push(noteBox(NOTE_BODY_TOO_LARGE));
      }
      const frame = content ?? htmlFrameElement({ source: drawn, selectable: false });
      if (frame instanceof HTMLIFrameElement) frame.setAttribute(HTML_BODY_ATTR, "");
      wrapper.append(...notes, frame);
      return { node: wrapper };
    }
    // 選んだ時点から変わった本文は、「描いた結果」を比較元の Markdown の色分け、「原文の差分」を取り出し元の行の差分で描く
    // 行の差分を計算しきれない書き換えは、差分を出さずに今の本文を描く
    const tooLarge = base !== null && jsdiff === "ready" && diffLineParts(base, source, getLibrary("jsdiff") as JsDiff) === null;
    if (tooLarge) notes.push(noteBox(NOTE_BODY_TOO_LARGE));
    const options = base === null || tooLarge ? {} : view === "source" ? { diffSource: { docId: item.id, before: base, after: source } } : { base };
    const root = renderMarkdown(source, options);
    lowerHeadings({ root, shift: headingShift({ roots: [root] }) });
    if (base !== null && !tooLarge && view === "rendered" && jsdiff === "ready") replaceChangedRanges({ root, before: base, after: source });
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
      // 本文の印と ID のリンクは、mdmark の語の照合で付ける
      if (mdmark === "ready") linkBody({ root: target, index, selfId: id, onOpen, source: text });
      drawHtmlBlocks(target);
    };
    link(root, source);
    decorateMarkdown({ root, display, fold: !changed });
    attachTermTips({ root, index, onOpen });
    const drawn = renderDiagrams(root);
    if (base !== null && !tooLarge && view === "rendered" && jsdiff === "ready") void drawn.then(() => { decorateDiagrams({ root, before: base }); });
    const onDiagramTool = (event: Event): void => {
      const button = (event.target as Element).closest<HTMLElement>("[data-act]");
      const figure = button?.closest<HTMLElement>(".diagram");
      if (button === null || button === undefined || figure === null || figure === undefined) return;
      const act = button.dataset["act"];
      if (act === "diagram-zoom") {
        const svg = figure.querySelector<SVGElement>(".mermaid svg");
        const notes = figure.querySelector(":scope > .df-notes");
        const beforeSource = figure.getAttribute(BEFORE_SOURCE_ATTR);
        if (svg !== null) onDiagram({ svg, source: figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? null, beforeSource, notes: beforeSource === null || notes === null ? null : notes.outerHTML, framed: beforeSource !== null && figure.classList.contains("df-frame") });
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
    wrapper.append(...notes, root);
    // 文書に入れた後に、見出しへ送る
    const frame = requestAnimationFrame(() => {
      if (heading !== undefined && !scrollToHeading({ root, slug: heading })) onHeading(undefined);
    });
    return {
      node: wrapper,
      destroy: () => {
        cancelAnimationFrame(frame);
      },
    };
    // heading の変更では描き直さない（見出しのリンクが送る）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mdmark, jsdiff, mermaid, html, source, current, comparing, before, base, view, viewNonce, display, index, id, item.id, item.body]);
  return (
    <section data-body-view className="flex flex-col gap-1">
      <h3 className="m-0 text-h2 font-semibold">{label}</h3>
      {changed && !html ? <BodyDiffViewSwitch view={view} onChange={onView} /> : null}
      <DomHost create={create} />
    </section>
  );
};
