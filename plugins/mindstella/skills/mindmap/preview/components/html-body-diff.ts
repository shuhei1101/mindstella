// HTML の本文の差分。差分の表示の間、HTML の本文を描いた結果の上で変わった行を含む要素に印を付け、「原文の差分」に切り替えると原文の行の差分を出す。

namespace MindmapPreview {
  /** HTML の本文の差分の引数 */
  export type HtmlBodyDiffProps = {
    /** 選んだ時点の本文の原文（`body_diff` で組み立てたもの） */
    before: string;
    /** 今の本文の原文（記録の `bodies`） */
    after: string;
    /** 今の本文の行の印つきの HTML（記録の `marked_bodies`） */
    marked: string;
    /** 選んだ時点の本文の形式。`md`（形式を替えた）のときは描いた結果の印と切り替えを出さず、原文の差分だけを出す */
    beforeFormat?: "md" | "html";
    /** 本文の差分の並べ方。`side` のとき、描いた結果と原文の差分をどちらも左に選んだ時点、右に今を並べる */
    layout?: BodyLayout;
    /** 並べ方の切り替え。「描いた結果」「原文の差分」の組の前に別の組として置く。無ければ置かない */
    layoutSwitch?: HTMLElement | null;
  };

  /** 原文の差分で、同じ行がこの数を超えて続くときは前後だけを残して畳む（前後に残す行数） */
  const RAW_DIFF_CONTEXT = 3;

  /** 原文の行の差分。足した行・消した行に印を付け、変わっていない長い並びは前後 3 行を残して件数の行にする */
  function rawDiff({ parts }: { parts: LinePart[] }): HTMLElement {
    const lines: HTMLElement[] = [];
    // 1 つの並びずつ渡すため、消した行と足した行は対にならず、語の面は付かない
    const deadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
    parts.forEach((part, position) => {
      if (part.kind !== "same" || part.lines.length <= RAW_DIFF_CONTEXT * 2) {
        lines.push(...rawDiffLines({ parts: [part], deadline }));
        return;
      }
      // 先頭・末尾の並びは、変わった行の側だけを残す
      const head = position === 0 ? [] : part.lines.slice(0, RAW_DIFF_CONTEXT);
      const tail = position === parts.length - 1 ? [] : part.lines.slice(-RAW_DIFF_CONTEXT);
      const skipped = part.lines.length - head.length - tail.length;
      lines.push(...rawDiffLines({ parts: [{ kind: "same", lines: head }], deadline }));
      lines.push(h({ tag: "span", attrs: { class: "df-line df-skip" }, children: [`変わっていない ${skipped} 行`] }));
      lines.push(...rawDiffLines({ parts: [{ kind: "same", lines: tail }], deadline }));
    });
    return h({
      tag: "div",
      attrs: { class: "html-diff" },
      children: [
        h({ tag: "p", attrs: { class: "html-diff-head" }, children: ["原文の差分"] }),
        h({ tag: "pre", attrs: { class: "dg-raw df-raw", tabindex: "0", "aria-label": "原文の差分" }, children: lines }),
      ],
    });
  }

  /** 左右に並べた表示の列の名前の行 */
  function sideHead(): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "sbs-head", "aria-hidden": "true" },
      children: [h({ tag: "span", children: ["選んだ時点"] }), h({ tag: "span", children: ["今"] })],
    });
  }

  /** 原文の行の差分を左右に並べる。左に選んだ時点の行（消した行に印）、右に今の行（足した行に印）を置き、片側にしか無い行の向かいは空けて高さを揃える */
  function rawSideDiff({ parts }: { parts: LinePart[] }): HTMLElement {
    const cells: HTMLElement[] = [];
    const deadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
    const gap = (): HTMLElement => h({ tag: "span", attrs: { class: "df-line df-gap", "aria-hidden": "true" } });
    /** 左右の行の並びを、1 行ずつ向かい合わせて置く（短い側は空ける） */
    const place = (left: HTMLElement[], right: HTMLElement[]): void => {
      for (let offset = 0; offset < Math.max(left.length, right.length); offset += 1) {
        cells.push(left[offset] ?? gap(), right[offset] ?? gap());
      }
    };
    const sameLines = (lines: string[]): HTMLElement[] => rawDiffLines({ parts: [{ kind: "same", lines }], deadline });
    parts.forEach((part, position) => {
      if (part.kind === "same") {
        // 変わっていない長い並びは、前後の 3 行を残して件数の行にする
        const long = part.lines.length > RAW_DIFF_CONTEXT * 2;
        const head = !long ? part.lines : position === 0 ? [] : part.lines.slice(0, RAW_DIFF_CONTEXT);
        const tail = !long ? [] : position === parts.length - 1 ? [] : part.lines.slice(-RAW_DIFF_CONTEXT);
        place(sameLines(head), sameLines(head));
        if (long) {
          cells.push(
            h({ tag: "span", attrs: { class: "df-line df-skip df-span" }, children: [`変わっていない ${part.lines.length - head.length - tail.length} 行`] }),
          );
          place(sameLines(tail), sameLines(tail));
        }
        return;
      }
      // 消した行のすぐ後の足した行は、消した行と同じ行の高さに向かい合わせて置いた
      if (part.kind === "added" && parts[position - 1]?.kind === "removed") return;
      const next = parts[position + 1];
      if (part.kind === "removed" && next?.kind === "added") {
        // 行の数が同じなら変わった語に面を付ける
        const spans = rawDiffLines({ parts: [part, next], deadline });
        place(spans.slice(0, part.lines.length), spans.slice(part.lines.length));
        return;
      }
      const spans = rawDiffLines({ parts: [part], deadline });
      if (part.kind === "removed") place(spans, []);
      else place([], spans);
    });
    return h({
      tag: "div",
      attrs: { class: "html-diff sbs-only" },
      children: [
        h({ tag: "p", attrs: { class: "html-diff-head" }, children: ["原文の差分"] }),
        sideHead(),
        h({ tag: "pre", attrs: { class: "dg-raw df-raw df-split", tabindex: "0", "aria-label": "原文の差分（左に選んだ時点、右に今）" }, children: cells }),
      ],
    });
  }

  /** 描いた結果を左右に並べる。左は選んだ時点の本文（Markdown のときは Markdown として描く）、右は今の本文 */
  function renderedSide({ before, beforeFormat, right }: { before: string; beforeFormat: "md" | "html"; right: HTMLElement }): HTMLElement {
    const left = beforeFormat === "md" ? renderMarkdown(before) : htmlBodyFrame({ source: before, selectable: false, label: "選んだ時点の本文" });
    return h({
      tag: "div",
      attrs: { class: "sbs sbs-html" },
      children: [
        sideHead(),
        h({
          tag: "div",
          attrs: { class: "sbs-cols" },
          children: [
            h({ tag: "section", attrs: { class: "sbs-col sbs-before", "aria-label": "選んだ時点の本文" }, children: [left] }),
            h({ tag: "section", attrs: { class: "sbs-col sbs-after", "aria-label": "今の本文" }, children: [right] }),
          ],
        }),
      ],
    });
  }

  /** 凡例（足した・変わった）。消しただけの箇所があるときは、原文の差分で見られる旨を添える */
  function legend({ removedOnly }: { removedOnly: boolean }): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "df-legend" },
      children: [
        h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "足した"] }),
        h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
        removedOnly ? h({ tag: "span", attrs: { class: "muted" }, children: ["消した箇所は原文の差分で見られます"] }) : null,
      ],
    });
  }

  /** HTML の本文の差分。差分を計算しきれなかったときは null */
  export function htmlBodyDiff({ before, after, marked, beforeFormat = "html", layout = "inline", layoutSwitch = null }: HtmlBodyDiffProps): HTMLElement | null {
    const parts = diffLineParts(before, after);
    if (parts === null) return null;
    const raw = rawDiff({ parts });
    const side = layout === "side";
    // 選んだ時点の本文が Markdown で、インライン: 描いた結果の印と切り替えを出さず、原文の差分だけを出す
    if (beforeFormat === "md" && !side) {
      return layoutSwitch === null
        ? raw
        : h({ tag: "div", attrs: { class: "html-diff-c" }, children: [h({ tag: "div", attrs: { class: "html-diff-bar" }, children: [layoutSwitch] }), raw] });
    }
    const changed = htmlChangedLines(before, after);
    if (changed === null) return null;
    // 選んだ時点が Markdown のときは、右の今の本文に印を付けない
    const marks = beforeFormat === "md" ? undefined : { added: changed.added, changed: changed.changed };
    // 選んだ箇所のコメントの入口は出さない（差分の表示の間は今の本文の行と合わない場合がある）
    const rendered = h({
      tag: "div",
      attrs: { class: "html-marked" },
      children: [htmlBodyFrame({ source: marked, selectable: false, ...(marks === undefined ? {} : { marks }) })],
    });
    raw.hidden = true;
    // 左右に並べるときは、並べた描いた結果と原文の差分を持ち、本文の幅が足りないときはインラインの方を出す
    let rawSide: HTMLElement | null = null;
    if (side) {
      rendered.firstElementChild?.classList.add("sbs-fallback");
      raw.classList.add("sbs-fallback");
      rendered.prepend(
        renderedSide({
          before,
          beforeFormat,
          right: htmlBodyFrame({ source: marked, selectable: false, label: "今の本文", ...(marks === undefined ? {} : { marks }) }),
        }),
      );
      rawSide = rawSideDiff({ parts });
      rawSide.hidden = true;
    }
    const legendElement = legend({ removedOnly: changed.removedOnly });
    /** 描いた結果と原文の差分を切り替えるボタン */
    const toggle = (label: string, showRaw: boolean): HTMLElement =>
      h({
        tag: "button",
        attrs: {
          type: "button",
          "aria-pressed": String(!showRaw),
          onclick: (event) => {
            const pressed = event.currentTarget as HTMLElement;
            for (const button of pressed.parentElement?.children ?? []) button.setAttribute("aria-pressed", String(button === pressed));
            raw.hidden = !showRaw;
            rendered.hidden = showRaw;
            legendElement.hidden = showRaw;
            // 左右に並べた原文の差分も、原文の差分と一緒に出し分ける
            if (rawSide !== null) rawSide.hidden = !showRaw;
          },
        },
        children: [label],
      });
    return h({
      tag: "div",
      attrs: { class: "html-diff-c" },
      children: [
        h({
          tag: "div",
          attrs: { class: "html-diff-bar" },
          children: [
            // 並べ方の切り替えを、描いた結果と原文の差分の切り替えの前に別の組で置く
            layoutSwitch,
            h({
              tag: "div",
              attrs: { class: "segment", role: "group", "aria-label": "本文の差分の見せ方" },
              children: [toggle("描いた結果", false), toggle("原文の差分", true)],
            }),
            legendElement,
          ],
        }),
        rendered,
        rawSide,
        raw,
      ],
    });
  }
}
