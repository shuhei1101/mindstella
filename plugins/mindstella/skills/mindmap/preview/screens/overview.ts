// 概要。未読の AI の書き込み・未決定の検討事項・要見直しの検討事項・確認中の資料のタイルを並べる。

namespace MindmapPreview {
  /** 概要の引数 */
  export type OverviewProps = {
    index: RecordIndex;
    /** スレッド。`null`（読めなかった・配る書き出し）のときは未読のタイルを 0 件で描く */
    threads?: Thread[] | null;
    on: {
      /** 項目を詳細パネルで開く */
      open: (id: string) => void;
      /** 絞った表へ移る（`Route`） */
      navigate: (route: Route) => void;
      /** コメントの一覧を開く（スレッドの ID。「すべて表示」は `null`）。配る書き出しでは渡さない */
      openThread?: (id: string | null) => void;
    };
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks;
    /** 表示する種類。表示しない種類へ移る「すべて表示」を出さない（タイルと中の項目は残す） */
    visibleKinds?: Set<string>;
  };

  /** 小さなタイルに出す件数 */
  const MINI_LIMIT = 3;

  /** 種類を表示するか（`visibleKinds` を渡さないときは全ての種類を表示する） */
  function isShown(props: OverviewProps, kind: Kind): boolean {
    return props.visibleKinds === undefined || props.visibleKinds.has(kind);
  }

  /** 絞った表へ移る `Route`（画面の既定の表示形式で開く） */
  function tableRoute(tab: Tab, filters: Record<string, string[]>, view: View = "table"): Route {
    return { tab, view, id: null, full: false, filters, heading: null, diff: null };
  }

  /** 「すべて表示（N 件）」のボタン */
  function showAll(count: number, onClick: () => void): HTMLElement {
    return h({
      tag: "button",
      attrs: { class: "t-link", type: "button", onclick: onClick },
      children: [`すべて表示（${count} 件）`],
    });
  }

  /** 見出し（アイコンと名前）と、右端の「すべて表示」 */
  function tileHead(id: string, iconName: IconName, title: string, link: Node | null): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "t-head" },
      children: [h({ tag: "h2", attrs: { id }, children: [icon(iconName), title] }), link],
    });
  }

  /** 1 行が項目のボタンの一覧（押すと詳細を開く） */
  function miniList(
    items: Item[],
    emptyText: string,
    open: (id: string) => void,
    marks?: DiffMarks,
  ): HTMLElement {
    if (items.length === 0) return emptyNote(emptyText);
    return h({
      tag: "ul",
      attrs: { class: "mini" },
      children: [
        ...items.slice(0, MINI_LIMIT).map((item) =>
          h({
            tag: "li",
            children: [
              h({
                tag: "button",
                attrs: { type: "button", "data-id": item.id, onclick: () => open(item.id) },
                children: [
                  statusMark(item.status),
                  h({ tag: "span", attrs: { class: "mt" }, children: [item.title] }),
                  markFor({ marks, id: item.id }),
                  h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [icon("chev")] }),
                ],
              }),
            ],
          }),
        ),
      ],
    });
  }

  /** 未読の AI の書き込みを持つオープンのスレッドを、最後の未読の書き込みの新しい順に返す */
  function unreadThreads(threads: Thread[] | null | undefined): { thread: Thread; last: string }[] {
    return (threads ?? [])
      .filter((thread) => thread.status === "open")
      .flatMap((thread) => {
        const unseen = thread.posts.filter((post) => post.author === "ai" && !post.seen);
        const last = unseen.at(-1);
        return last === undefined ? [] : [{ thread, last: last.created }];
      })
      .sort((a, b) => (a.last < b.last ? 1 : a.last > b.last ? -1 : 0));
  }

  /** 未読の AI の書き込みのタイル（押すとコメントの一覧でそのスレッドを開く） */
  function unreadTile(props: OverviewProps): HTMLElement {
    const rows = unreadThreads(props.threads);
    const openThread = props.on.openThread;
    return h({
      tag: "section",
      attrs: { id: "tile-unread", class: "tile t-small", "aria-labelledby": "h-unread" },
      children: [
        tileHead(
          "h-unread",
          "comment",
          "未読の AI の書き込み",
          rows.length > 0 && openThread !== undefined ? showAll(rows.length, () => openThread(null)) : null,
        ),
        h({ tag: "p", attrs: { class: "num" }, children: [rows.length] }),
        rows.length === 0
          ? emptyNote("未読の AI の書き込みはありません。")
          : h({
              tag: "ul",
              attrs: { class: "mini" },
              children: rows.slice(0, MINI_LIMIT).map(({ thread, last }) =>
                h({
                  tag: "li",
                  children: [
                    h({
                      tag: "button",
                      attrs: {
                        type: "button",
                        "data-id": thread.id,
                        disabled: openThread === undefined,
                        onclick: () => openThread?.(thread.id),
                      },
                      children: [
                        h({ tag: "span", attrs: { class: "mt" }, children: [`${thread.id} ${thread.summary ?? ""}`.trim()] }),
                        h({ tag: "span", attrs: { class: "go", "aria-hidden": "true" }, children: [icon("chev")] }),
                      ],
                    }),
                    h({ tag: "span", attrs: { class: "wait" }, children: [formatJst(last)] }),
                  ],
                }),
              ),
            }),
      ],
    });
  }

  /** 件数と名前の小さなタイル（未決定・要見直し・確認中の資料） */
  function smallTile({
    tileId,
    id,
    iconName,
    title,
    items,
    emptyText,
    link,
    open,
    marks,
    linked,
  }: {
    /** タイルの項目 ID（画面設計） */
    tileId: string;
    /** タイルの見出しの要素の id */
    id: string;
    iconName: IconName;
    title: string;
    items: Item[];
    /** 0 件のときに出す文 */
    emptyText: string;
    link: () => void;
    open: (id: string) => void;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks | undefined;
    /** 「すべて表示」を出すか（その種類の画面を表示しないときは出さない） */
    linked: boolean;
  }): HTMLElement {
    return h({
      tag: "section",
      attrs: { id: tileId, class: "tile t-small", "aria-labelledby": id },
      children: [
        tileHead(id, iconName, title, items.length > 0 && linked ? showAll(items.length, link) : null),
        h({ tag: "p", attrs: { class: "num" }, children: [items.length] }),
        miniList(items, emptyText, open, marks),
      ],
    });
  }

  /** 概要の画面を返す */
  export function overviewScreen(props: OverviewProps): HTMLElement {
    const { index, on } = props;
    const { settings } = index.data;
    const byNumber = (items: Item[]): Item[] => [...items].sort((a, b) => compareIds(a.id, b.id));
    const decisions = index.data.decisions;
    const open = byNumber(decisions.filter((item) => item.status === "未決定"));
    const review = byNumber(decisions.filter((item) => item.status === "要見直し"));
    const docs = byNumber(index.data.docs.filter((item) => item.status === "確認中"));
    return h({
      tag: "div",
      attrs: { class: "overview" },
      children: [
        h({
          tag: "header",
          attrs: { class: "hero" },
          children: [
            // 話し合いの概要があるときだけ、題名の上に出す
            settings.description !== undefined
              ? h({
                  tag: "p",
                  attrs: { id: "overview-description", class: "hero-sub hero-desc" },
                  children: [settings.description],
                })
              : null,
            h({ tag: "h1", children: [settings.summary] }),
          ],
        }),
        h({
          tag: "div",
          attrs: { class: "bento" },
          children: [
            unreadTile(props),
            smallTile({
              tileId: "tile-open",
              id: "h-open",
              iconName: "decision",
              title: "未決定の検討事項",
              items: open,
              emptyText: "未決定の検討事項はありません。",
              link: () => on.navigate(tableRoute("decisions", { status: ["未決定"] })),
              open: on.open,
              marks: props.marks,
              linked: isShown(props, "decisions"),
            }),
            smallTile({
              tileId: "tile-review",
              id: "h-review",
              iconName: "alert",
              title: "要見直し",
              items: review,
              emptyText: "要見直しの検討事項はありません。",
              link: () => on.navigate(tableRoute("decisions", { status: ["要見直し"] })),
              open: on.open,
              marks: props.marks,
              linked: isShown(props, "decisions"),
            }),
            smallTile({
              tileId: "tile-docs",
              id: "h-docs",
              iconName: "doc",
              title: "確認中の資料",
              items: docs,
              emptyText: "確認中の資料はありません。",
              link: () => on.navigate(tableRoute("docs", { status: ["確認中"] }, "cards")),
              open: on.open,
              marks: props.marks,
              linked: isShown(props, "docs"),
            }),
          ],
        }),
      ],
    });
  }
}
