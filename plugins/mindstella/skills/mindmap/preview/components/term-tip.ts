// 本文の印のツールチップ。本文の印（用語のタイトルと別名・資料と調査のエイリアスに一致した語）に乗せる・フォーカスすると、一致した項目を用語 → 資料 → 調査の順に並べて印の上に出す。

namespace MindmapPreview {
  /** ツールチップに並べる項目（種類と項目） */
  export type TermTipEntry = { kind: (typeof MARK_KINDS)[number]; item: Item };

  /** 本文の印のツールチップの引数 */
  export type TermTipProps = {
    /** 印の語に一致した項目。用語 → 資料 → 調査の順。開いている項目自身と取り下げた資料・調査は含めない（取り下げた用語は含める） */
    entries: TermTipEntry[];
    /** 本文の印の要素。置き場所とフォーカスの戻し先 */
    anchor: HTMLElement;
    /** 押して残した状態か。真のときは外を押すと閉じる */
    pinned?: boolean;
    on: {
      /** 中の項目のリンクを押した（項目の ID）。使う側がツールチップを閉じ、その項目へ移る */
      open: (id: string) => void;
      /** 閉じる操作があった（Esc・押して残した状態での外の押下・中からフォーカスが外へ出た） */
      close: () => void;
    };
  };

  /** 種類ごとの見出しの名前 */
  const KIND_LABELS: Record<TermTipEntry["kind"], string> = { terms: "用語", docs: "資料", research: "調査" };

  /** 印との間の空きと、画面の端から内側に収める幅（px） */
  const TIP_GAP = 6;
  const SCREEN_EDGE = 8;

  /** 要素の中のフォーカスできる要素 */
  function focusablesIn(parent: ParentNode): HTMLElement[] {
    return [...parent.querySelectorAll<HTMLElement>("a[href], button, [tabindex]:not([tabindex='-1'])")].filter(
      (node) => node.closest("[hidden]") === null,
    );
  }

  /** 項目 1 件。用語は用語・ID・意味、資料・調査はタイトル・ID・説明（無ければ出さない） */
  function tipItem({ entry }: { entry: TermTipEntry }): HTMLElement {
    const { item } = entry;
    const text = entry.kind === "terms" ? item.meaning : item.description;
    return h({
      tag: "li",
      attrs: { class: "tt-item" },
      children: [
        h({
          tag: "span",
          attrs: { class: "tt-head" },
          children: [
            h({ tag: "a", attrs: { class: "tt-link", href: hashWith({ id: item.id, heading: null }), "data-id": item.id }, children: [item.title] }),
            h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
          ],
        }),
        text === undefined || text === "" ? null : h({ tag: "span", attrs: { class: "tt-body" }, children: [text] }),
      ],
    });
  }

  /** 用語と資料・調査を含むツールチップの中身。種類ごとの見出し（種類名と件数）とリストに分ける */
  function groupedContent(entries: TermTipEntry[]): HTMLElement[] {
    return MARK_KINDS.map((kind) => ({ kind, entries: entries.filter((entry) => entry.kind === kind) }))
      .filter((group) => group.entries.length > 0)
      .map((group) =>
        h({
          tag: "div",
          attrs: { class: "tt-group" },
          children: [
            h({
              tag: "p",
              attrs: { class: "tt-kind", id: `tt-kind-${group.kind}` },
              children: [KIND_LABELS[group.kind], " ", h({ tag: "span", attrs: { class: "tt-n" }, children: [String(group.entries.length)] })],
            }),
            h({
              tag: "ul",
              attrs: { class: "tt-items", "aria-labelledby": `tt-kind-${group.kind}` },
              children: group.entries.map((entry) => tipItem({ entry })),
            }),
          ],
        }),
      );
  }

  /** ツールチップを返す。使う側が文書に入れて `showPopover()` で開く。開くと印の上に置き、上に収まらなければ下に、どちらにも収まらなければ広い側の高さに縮める */
  export function termTip({ entries, anchor, pinned = false, on }: TermTipProps): HTMLElement {
    // 用語 2 件以上か、資料・調査を含むときは、種類ごとの見出しとリンクで並べる
    const multi = entries.length > 1 || entries.some((entry) => entry.kind !== "terms");
    const tip = h({
      tag: "div",
      attrs: {
        id: TERM_TIP_ID,
        class: multi ? "term-tip is-multi" : "term-tip",
        // リンクを持たない用語 1 件だけのツールチップは tooltip の役割にし、リンクを持つ方は印の aria-details で指す
        role: multi ? null : "tooltip",
        popover: "manual",
      },
    });
    if (multi) {
      tip.append(...groupedContent(entries));
    } else {
      // 用語 1 件だけに一致した印は、用語・ID・意味だけを出す
      const term = entries[0]!.item;
      tip.append(
        h({ tag: "span", attrs: { class: "tt-head" }, children: [term.title, h({ tag: "span", attrs: { class: "mono" }, children: [term.id] })] }),
        h({ tag: "span", attrs: { class: "tt-body" }, children: [term.meaning ?? ""] }),
      );
    }

    /** 印の上に 6px 空けて下端を留める。上に収まらなければ下に出し、どちらにも収まらなければ広い側の余白（印との 6px と画面の端の 8px を除く）の高さに縮めて固定する */
    const place = (): void => {
      const rect = anchor.getBoundingClientRect();
      tip.style.height = "";
      tip.style.top = "auto";
      tip.style.bottom = "auto";
      const needed = tip.offsetHeight;
      const spaceAbove = rect.top - TIP_GAP - SCREEN_EDGE;
      const spaceBelow = innerHeight - rect.bottom - TIP_GAP - SCREEN_EDGE;
      const above = spaceAbove >= needed || (spaceBelow < needed && spaceAbove >= spaceBelow);
      const room = above ? spaceAbove : spaceBelow;
      // 収まらない: 縮めた高さで固定し、中身が変わっても大きさを変えない
      if (needed > room) tip.style.height = `${Math.max(room, 0)}px`;
      tip.style.left = `${Math.max(SCREEN_EDGE, Math.min(rect.left, innerWidth - tip.offsetWidth - SCREEN_EDGE))}px`;
      if (above) tip.style.bottom = `${innerHeight - rect.top + TIP_GAP}px`;
      else tip.style.top = `${rect.bottom + TIP_GAP}px`;
    };

    /** 押して残した状態で、ツールチップと印の外を押したら閉じる */
    const closeOnOutsidePress = (event: Event): void => {
      const target = event.target;
      if (target instanceof Node && (tip.contains(target) || anchor.contains(target))) return;
      on.close();
    };

    // 開いたとき（と、開いた直後の描画の前）に置き場所を決める。押して残した状態なら外の押下も見る
    tip.addEventListener("toggle", (event) => {
      if ((event as ToggleEvent).newState === "open") {
        place();
        if (pinned) document.addEventListener("pointerdown", closeOnOutsidePress, true);
      } else {
        document.removeEventListener("pointerdown", closeOnOutsidePress, true);
      }
    });
    requestAnimationFrame(() => {
      if (tip.matches(":popover-open")) place();
    });

    // 中の項目のリンクは、その項目へ移る
    tip.addEventListener("click", (event) => {
      const link = (event.target as Element).closest<HTMLElement>("a.tt-link");
      if (link === null) return;
      event.preventDefault();
      on.open(link.getAttribute("data-id") ?? "");
    });

    tip.addEventListener("keydown", (event) => {
      // Esc: ツールチップだけを閉じて印へフォーカスを戻す（全画面を閉じる Esc として受けさせない）
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        anchor.focus();
        on.close();
        return;
      }
      if (event.key !== "Tab") return;
      // 最初のリンクの Shift+Tab は印へ、最後のリンクの次は本文の印の次の要素へ移す
      const inside = focusablesIn(tip);
      const edge = event.shiftKey ? inside[0] : inside.at(-1);
      if (document.activeElement !== edge) return;
      event.preventDefault();
      if (event.shiftKey) {
        anchor.focus();
        return;
      }
      const after = focusablesIn(anchor.closest(".md") ?? document.body);
      const next = after[after.indexOf(anchor) + 1] ?? anchor;
      next.focus();
      // 印へ戻るときは focusout で閉じないため、ここで閉じる
      if (next === anchor) on.close();
    });

    // 中から印でもツールチップでもない所へフォーカスが出たら閉じる
    tip.addEventListener("focusout", (event) => {
      const to = event.relatedTarget;
      if (to instanceof Node && !tip.contains(to) && to !== anchor) on.close();
    });

    return tip;
  }
}
