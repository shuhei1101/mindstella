// 表と、並べ替え・絞り込みの計算。列の見出しで並べ替え・ピン留めでき、表の上に絞り込みの条件のチップを並べる。絞り込みの条件はドロワーで選ぶ。

namespace MindmapPreview {
  /** 表の行（埋め込みのデータの項目そのもの） */
  export type Row = { id: string } & Record<string, unknown>;

  /** 列が行から取る値（配列の列は、要素のどれかが条件にあれば絞り込みに合う） */
  export type CellValue = string | number | readonly string[] | null | undefined;

  /** 列の定義 */
  export type Column = {
    /** 列の識別子。並べ替え・絞り込み・ピン留めの対象を指す */
    key: string;
    /** 見出しの文字 */
    label: string;
    /** 値で絞り込めるか。真の列を絞り込みのドロワーの条件にする（列の見出しには絞り込みのボタンを出さない） */
    filterable?: boolean;
    /** 表示する列から外せないか（タイトルの列。行を押して詳細を開くボタンにする） */
    fixed?: boolean;
    /** 初期設定で隠すか */
    hidden?: boolean;
    /** 値の並び（並べ替え・絞り込みの値の順） */
    order?: readonly string[];
    /** 数値の列か（右寄せ） */
    num?: boolean;
    /** セルを折り返さないか */
    nowrap?: boolean;
    /** 列の最小の幅（CSS の値） */
    minWidth?: string;
    /** 狭い幅で隠す順（大きいほど先に隠す） */
    priority?: number;
    /** 行から値を取る */
    get: (row: Row) => CellValue;
    /** セルを描く。無ければ値を文字にする */
    cell?: (row: Row) => Node | string;
  };

  /** 並べ替えている列と向き */
  export type SortState = { key: string; dir: "asc" | "desc" } | null;

  /** 列の `key` → 選んだ値の配列 */
  export type Filters = Record<string, string[]>;

  /** 絞り込みの条件の定義（行から値を取る） */
  export type FilterColumn = Pick<Column, "key" | "get">;

  /** 値の件数を数える条件の定義（値の並びを持つ） */
  export type ConditionColumn = FilterColumn & Pick<Column, "order">;

  /** ドロワーの条件の値（件数と、キーワードに一致した件数） */
  export type FilterValue = { value: string; count: number; hit?: number };

  /** ドロワーの条件 1 つ（部品設計『絞り込み』の `groups[]`） */
  export type FilterGroup = {
    key: string;
    label: string;
    values: FilterValue[];
    /** 値の左に添える印。状態の印か、項目の種類の色の点 */
    mark?: "status" | "kind";
  };

  /** 表で開いているポップオーバー */
  export type TablePopover = { type: "columns" };

  /** 表のイベントごとのコールバック（使う側が描き直す） */
  export type TableHandlers = {
    /** 見出しの文字を押したとき（昇順 → 降順 → 解除は使う側が巡る） */
    sort: (key: string) => void;
    /** チップの × か「すべて解除」を押したとき。key が null のときは全ての条件を外す */
    filter: (filters: Filters) => void;
    /** ピン留めのボタンを押したとき（固定中の列をもう一度押すと外す） */
    pin: (key: string) => void;
    /** 表示する列を付け外ししたとき（隠している列の key） */
    columns: (hiddenColumns: string[]) => void;
    /** 初期設定に戻すを押したとき */
    reset: () => void;
    /** 行のタイトルを押したとき */
    open: (id: string) => void;
    /** ポップオーバーを開いた・閉じたとき（描き直しても開いたままにするために、使う側が持つ） */
    popover?: (popover: TablePopover | null) => void;
  };

  /** 表の引数 */
  export type TableProps = {
    /** 項目の種類。該当なしの文言に使う */
    kind: Kind;
    columns: Column[];
    /** 行にする項目 */
    rows: Row[];
    sort?: SortState;
    filters?: Filters;
    /** 左端からこの列までを横スクロールでも固定する列の key */
    pinTo?: string | null;
    /** 隠している列の key。無ければ `columns[].hidden` が真の列 */
    hiddenColumns?: string[];
    /** 開いているポップオーバー */
    popover?: TablePopover | null;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡し、当たる行のタイトルの右に印を文言なしで置く */
    marks?: DiffMarks;
    /** 項目の ID → レビュー中のコメントの件数。渡したとき（サーバーにつながって開いたとき）だけ、当たる行のタイトルの右、差分の印の後ろに印を置く場所を置く */
    comments?: Record<string, number>;
    on: TableHandlers;
  };

  /** 列が行から取る値を、文字の配列にする */
  function valuesOf(column: FilterColumn, row: Row): string[] {
    const value = column.get(row);
    if (value === null || value === undefined) return [];
    return Array.isArray(value) ? value.map(String) : [String(value)];
  }

  /** 値を文字で比べる順（`order` を持つ列はその並びの順、無ければ日本語の順） */
  function compareValues(column: Pick<Column, "order">, a: string, b: string): number {
    if (column.order) {
      const rank = (value: string) => {
        const index = column.order?.indexOf(value) ?? -1;
        return index < 0 ? (column.order?.length ?? 0) : index;
      };
      return rank(a) - rank(b);
    }
    return a.localeCompare(b, "ja");
  }

  /** 文字の条件のキー（`~{列}`）の頭 */
  export const TEXT_FILTER_PREFIX = "~";

  /** 条件ごとに合う行を返す（条件の中はどれかに当たればよく、条件の間は全てに当たる）。`~{列}` は文字の条件で、その列の値のどれかが文字を含む行に当てる（大文字・小文字を区別しない） */
  export function filterRows({
    rows,
    columns,
    filters,
  }: {
    rows: Row[];
    columns: FilterColumn[];
    filters: Filters;
  }): Row[] {
    const active = Object.entries(filters).filter(([, values]) => values.length > 0);
    return rows.filter((row) =>
      active.every(([key, wanted]) => {
        const isText = key.startsWith(TEXT_FILTER_PREFIX);
        const columnKey = isText ? key.slice(TEXT_FILTER_PREFIX.length) : key;
        const column = columns.find((candidate) => candidate.key === columnKey);
        // 知らない列の条件は無視する
        if (column === undefined) return true;
        const values = valuesOf(column, row);
        if (!isText) return values.some((value) => wanted.includes(value));
        const needles = wanted.map((text) => text.toLowerCase());
        return values.some((value) => needles.some((needle) => value.toLowerCase().includes(needle)));
      }),
    );
  }

  /** 表の列のうち、絞り込みのドロワーに文字の欄を出す列（値を選ぶ列と数の列を除く。列の順のまま） */
  export function textColumns(columns: Column[]): Column[] {
    return columns.filter((column) => column.filterable !== true && column.num !== true);
  }

  /** 列の値で行を並べ替える（元の配列は変えない。同じ値は元の順） */
  export function sortRows({
    rows,
    columns,
    sort,
  }: {
    rows: Row[];
    columns: Column[];
    sort: SortState;
  }): Row[] {
    if (sort === null) return [...rows];
    const column = columns.find((candidate) => candidate.key === sort.key);
    if (column === undefined) return [...rows];
    const direction = sort.dir === "asc" ? 1 : -1;
    const compare = (a: Row, b: Row): number => {
      const x = column.get(a);
      const y = column.get(b);
      // 数値は数の順
      if (typeof x === "number" && typeof y === "number") return x - y;
      return compareValues(column, valuesOf(column, a).join(" "), valuesOf(column, b).join(" "));
    };
    return rows
      .map((row, position) => ({ row, position }))
      .sort((a, b) => direction * compare(a.row, b.row) || a.position - b.position)
      .map(({ row }) => row);
  }

  /** 条件の値ごとの件数を返す（その条件以外の条件で絞った行で数える） */
  export function filterCounts({
    rows,
    columns,
    filters,
    key,
  }: {
    rows: Row[];
    columns: ConditionColumn[];
    filters: Filters;
    key: string;
  }): { value: string; count: number }[] {
    const column = columns.find((candidate) => candidate.key === key);
    if (column === undefined) return [];
    const others = withoutKey(filters, key);
    const counts = new Map<string, number>();
    // 選べる値は全ての行の値（件数が 0 のものも出す）
    for (const row of rows) for (const value of valuesOf(column, row)) counts.set(value, 0);
    for (const row of filterRows({ rows, columns, filters: others })) {
      for (const value of valuesOf(column, row)) counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    return [...counts]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => compareValues(column, a.value, b.value));
  }

  /** ドロワーの条件を並べるとき、先に置くキー（この順） */
  const LEADING_CONDITION_KEYS = ["kind", "type", "status", "tags"];

  /** 検討事項を開いたときの絞り込みの状態 */
  const DEFAULT_DECISION_STATUSES = ["要見直し", "未決定", "未整理", "保留"];

  /** 絞り込みから、1 つの条件を除いたものを返す */
  export function withoutKey(filters: Filters, key: string): Filters {
    return Object.fromEntries(Object.entries(filters).filter(([name]) => name !== key));
  }

  /** 絞り込みのドロワーに並べる条件と、条件ごとの値・件数を組む（キーワードに一致した件数を `hit` で添えられる） */
  export function drawerGroups({
    rows,
    columns,
    filters,
    hit,
  }: {
    rows: Row[];
    columns: (ConditionColumn & Pick<Column, "label">)[];
    filters: Filters;
    hit?: (row: Row) => boolean;
  }): FilterGroup[] {
    const rank = (key: string): number => {
      const position = LEADING_CONDITION_KEYS.indexOf(key);
      return position < 0 ? LEADING_CONDITION_KEYS.length : position;
    };
    const ordered = [...columns].sort((a, b) => rank(a.key) - rank(b.key));
    const groups: FilterGroup[] = [];
    for (const column of ordered) {
      const counts = filterCounts({ rows, columns, filters, key: column.key });
      // 値を 1 つも持たない条件は並べない
      if (counts.length === 0) continue;
      // キーワードに一致した件数は、その条件以外の条件で絞った行で数える
      const others = hit === undefined ? [] : filterRows({ rows, columns, filters: withoutKey(filters, column.key) });
      groups.push({
        key: column.key,
        label: column.label,
        values: counts.map(({ value, count }) =>
          hit === undefined
            ? { value, count }
            : {
                value,
                count,
                hit: others.filter((row) => hit(row) && valuesOf(column, row).includes(value)).length,
              },
        ),
        ...(column.key === "status" ? { mark: "status" as const } : {}),
        ...(column.key === "type" ? { mark: "kind" as const } : {}),
      });
    }
    return groups;
  }

  /** 値を 1 つ以上選んでいる条件の数を返す（絞り込みのボタンのバッジ） */
  export function activeConditionCount(filters: Filters): number {
    return Object.values(filters).filter((values) => values.length > 0).length;
  }

  /** 画面を開いたときの絞り込みを返す。URL のハッシュの `f.{列}` があればそれだけ、無ければ端末に残した条件、それも無ければ画面の既定 */
  export function initialFilters(tab: Route["tab"], fromHash: Filters, saved: Filters | null): Filters {
    if (Object.keys(fromHash).length > 0) return { ...fromHash };
    // 残した条件は、全て外した状態（空）でも画面の既定に戻さない
    if (saved !== null) return { ...saved };
    return tab === "decisions" ? { status: [...DEFAULT_DECISION_STATUSES] } : {};
  }

  /** 端末に残した条件から、今の記録のどの行にも無い値を外す。文字の条件（`~{列}`）はそのまま残し、知らない列の条件は外す（渡した条件は変えない） */
  export function pruneFilters({
    rows,
    columns,
    saved,
  }: {
    rows: Row[];
    columns: FilterColumn[];
    saved: Filters;
  }): Filters {
    const pruned: Filters = {};
    for (const [key, values] of Object.entries(saved)) {
      // 文字の条件は記録の値ではないので、そのまま写す
      if (key.startsWith(TEXT_FILTER_PREFIX)) {
        pruned[key] = [...values];
        continue;
      }
      const column = columns.find((candidate) => candidate.key === key);
      // 知らない列の条件は外す
      if (column === undefined) continue;
      const present = new Set(rows.flatMap((row) => valuesOf(column, row)));
      const kept = values.filter((value) => present.has(value));
      // 値が 1 つも残らない列はキーごと外す
      if (kept.length > 0) pruned[key] = kept;
    }
    return pruned;
  }

  /** ポップオーバーを開いた元のボタンの上か下に置く（収まる側に開き、どちらも収まらないときは広い側で高さを抑える） */
  export function positionPopover(pop: HTMLElement, anchor: Element): void {
    const gap = 6;
    const margin = 8;
    const rect = anchor.getBoundingClientRect();
    pop.style.maxHeight = "";
    const { offsetWidth: width, offsetHeight: height } = pop;
    pop.style.left = `${Math.max(margin, Math.min(rect.left, innerWidth - width - margin))}px`;
    const below = innerHeight - rect.bottom - gap - margin;
    const above = rect.top - gap - margin;
    const openBelow = height <= below || (height > above && below >= above);
    const room = openBelow ? below : above;
    if (height > room) pop.style.maxHeight = `${room}px`;
    pop.style.top = `${openBelow ? rect.bottom + gap : rect.top - gap - pop.offsetHeight}px`;
  }

  /** 表の入れ物（スクロールする要素）ごとの、大きさの観察（描き直すたびに前の観察を止める） */
  const wrapObservers = new WeakMap<HTMLElement, ResizeObserver>();

  /** 表の項目の見出しのアイコン */
  function sortIcon(direction: "asc" | "desc" | null): Node {
    if (direction === "asc") return icon("up");
    if (direction === "desc") return icon("down");
    return h({ tag: "span", attrs: { class: "sort-hint" }, children: [icon("updown")] });
  }

  /** 項目の表を返す。操作は引数のコールバックで知らせ、描き直しは使う側が行う */
  export function table(props: TableProps): HTMLElement {
    return buildTable({ props, previous: null });
  }

  /** 選んでいる値を `{列}: {値}` のチップにし、× と「すべて解除」で条件の解除を知らせる行を返す（条件が無いときは中身の無い行） */
  export function filterChips({
    filters,
    labels,
    onFilter,
  }: {
    /** 絞り込みのドロワーと共有する条件 */
    filters: Filters;
    /** 条件の key → チップに出す列の名前 */
    labels: Record<string, string>;
    /** 解除した後の新しい条件を知らせる */
    onFilter: (filters: Filters) => void;
  }): HTMLElement {
    const items: HTMLElement[] = [];
    for (const [key, values] of Object.entries(filters)) {
      // 文字の条件（`~{列}`）は、列の名前に「文字を含む」の文言を続けたチップにする
      if (key.startsWith(TEXT_FILTER_PREFIX)) {
        const columnKey = key.slice(TEXT_FILTER_PREFIX.length);
        const name = labels[columnKey] ?? columnKey;
        // 英数字で終わる列名の後ろには空白を挟む（「ID に」のように読めるように）
        const joint = /[A-Za-z0-9]$/.test(name) ? " " : "";
        for (const value of values) {
          const text = `${name}${joint}に「${value}」を含む`;
          items.push(
            h({
              tag: "span",
              attrs: { class: "chip" },
              children: [
                text,
                h({
                  tag: "button",
                  attrs: {
                    type: "button",
                    "aria-label": `${text} の条件を解除`,
                    onclick: () => onFilter(withoutKey(filters, key)),
                  },
                  children: [icon("x")],
                }),
              ],
            }),
          );
        }
        continue;
      }
      const label = labels[key] ?? key;
      for (const value of values) {
        items.push(
          h({
            tag: "span",
            attrs: { class: "chip" },
            children: [
              `${label}: ${value}`,
              h({
                tag: "button",
                attrs: {
                  type: "button",
                  "aria-label": `${label}: ${value} の条件を解除`,
                  onclick: () => {
                    // 押した値を外し、値が残らない条件は key ごと消す
                    const rest = values.filter((candidate) => candidate !== value);
                    onFilter(rest.length === 0 ? withoutKey(filters, key) : { ...filters, [key]: rest });
                  },
                },
                children: [icon("x")],
              }),
            ],
          }),
        );
      }
    }
    if (items.length > 0) {
      items.push(
        h({
          tag: "button",
          attrs: { class: "btn ghost", type: "button", onclick: () => onFilter({}) },
          children: ["すべて解除"],
        }),
      );
    }
    return h({ tag: "div", attrs: { class: "chips" }, children: items });
  }

  /** 表を組み立てる。previous があれば、その表の入れ物（スクロールする要素）を作り直さず、中身だけ差し替える */
  function buildTable({
    props: { kind, columns, rows, sort = null, filters = {}, pinTo = null, hiddenColumns, popover = null, marks, comments, on },
    previous,
  }: {
    props: TableProps;
    previous: HTMLElement | null;
  }): HTMLElement {
    const hidden = new Set(
      hiddenColumns ?? columns.filter((column) => column.hidden).map((column) => column.key),
    );
    const visible = columns.filter((column) => !hidden.has(column.key));
    // 固定する列の数（左端から pinTo の列まで）
    const pinned = pinTo === null ? 0 : visible.findIndex((column) => column.key === pinTo) + 1;
    const shownRows = sortRows({ rows: filterRows({ rows, columns, filters }), columns, sort });

    // 描き直しでは前の入れ物をそのまま使い、スクロールの位置を失わない
    const root = previous ?? h({ tag: "div", attrs: { class: "table-block", "data-kind": kind } });
    const wrap =
      previous?.querySelector<HTMLElement>(".table-wrap") ??
      h({ tag: "div", attrs: { class: "table-wrap" } });

    // ===== 条件のチップと、表示する列のボタン =====
    const chipsRow = filterChips({
      filters,
      labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
      onFilter: on.filter,
    });
    // ポップオーバーの題の要素の id（`aria-labelledby` が指す。置かれる画面の見出しの深さを知らないので、見出しの要素にはしない）
    const popTitleId = `pop-title-${kind}`;
    const pop = h({
      tag: "div",
      attrs: { class: "pop", popover: "auto", "aria-labelledby": popTitleId },
    });
    /** ポップオーバーの題 */
    const popoverTitle = (text: string): HTMLElement =>
      h({ tag: "p", attrs: { class: "pop-title", id: popTitleId }, children: [text] });
    /** ポップオーバーの中身を作り、元のボタンの近くに開く */
    const showPopover = (): void => {
      pop.replaceChildren(columnsPopoverBody());
      if (!pop.matches(":popover-open")) pop.showPopover();
      const anchor = root.querySelector('[data-popover="columns"]');
      if (anchor !== null) positionPopover(pop, anchor);
    };
    /** 表示する列のポップオーバーの中身 */
    const columnsPopoverBody = (): Node => {
      const boxes = columns.map((column) =>
        h({
          tag: "label",
          children: [
            h({
              tag: "input",
              attrs: {
                type: "checkbox",
                checked: !hidden.has(column.key),
                disabled: column.fixed === true,
                onchange: (event: Event) => {
                  const checked = (event.target as HTMLInputElement).checked;
                  on.columns(
                    checked
                      ? [...hidden].filter((key) => key !== column.key)
                      : [...hidden, column.key],
                  );
                },
              },
            }),
            column.label,
          ],
        }),
      );
      return h({
        tag: "div",
        children: [
          popoverTitle("表示する列"),
          ...boxes,
          h({
            tag: "div",
            attrs: { class: "pop-foot" },
            children: [
              h({
                tag: "button",
                attrs: {
                  class: "btn ghost",
                  type: "button",
                  onclick: () => {
                    on.reset();
                  },
                },
                children: ["列・並べ替え・固定を初期設定に戻す"],
              }),
            ],
          }),
        ],
      });
    };
    // ポップオーバーを閉じたら、使う側にも知らせる（描き直しで消えたときは知らせない）
    pop.addEventListener("toggle", (event) => {
      if ((event as ToggleEvent).newState === "closed" && pop.isConnected) on.popover?.(null);
    });
    /** ポップオーバーを開き、使う側にも知らせる */
    const openPopover = (): void => {
      showPopover();
      on.popover?.({ type: "columns" });
    };

    const toolbar = h({
        tag: "div",
        attrs: { class: "table-toolbar" },
        children: [
          chipsRow,
          h({
            tag: "button",
            attrs: {
              class: "btn",
              type: "button",
              "data-popover": "columns",
              "aria-label": "表示する列",
              onclick: openPopover,
            },
            children: [
              icon("cols"),
              h({ tag: "span", attrs: { class: "lbl" }, children: ["表示する列"] }),
            ],
          }),
        ],
      });

    // ===== 見出し =====
    const headers = visible.map((column, position) => {
      const direction = sort !== null && sort.key === column.key ? sort.dir : null;
      const isPinned = position === pinned - 1;
      return h({
        tag: "th",
        attrs: {
          scope: "col",
          class: [column.num ? "num" : "", position < pinned ? "pinned" : ""].join(" ").trim(),
          "data-col": position,
          "data-pri": column.priority ?? 1,
          "aria-sort":
            direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none",
          style: column.minWidth === undefined ? null : `min-width:${column.minWidth}`,
        },
        children: [
          h({
            tag: "div",
            attrs: { class: "th-in" },
            children: [
              h({
                tag: "button",
                attrs: {
                  class: "th-sort",
                  type: "button",
                  "data-sort": column.key,
                  onclick: () => {
                    on.sort(column.key);
                  },
                },
                children: [column.label, sortIcon(direction)],
              }),
              h({
                tag: "button",
                attrs: {
                  class: "th-tool pin",
                  type: "button",
                  "data-pin": column.key,
                  "aria-pressed": String(isPinned),
                  "aria-label": `${column.label}まで固定`,
                  onclick: () => {
                    on.pin(column.key);
                  },
                },
                children: [icon("pin")],
              }),
            ],
          }),
        ],
      });
    });

    // ===== 行 =====
    /** セルの中身 */
    const cellContent = (column: Column, row: Row): Node | string => {
      const content =
        column.cell?.(row) ?? valuesOf(column, row).join(column.num === true ? "" : "、");
      if (column.fixed !== true) return content;
      // タイトルの列は、押すと詳細を開くボタンにし、取り下げの札・差分の印があれば右に置く
      const opener = h({
        tag: "button",
        attrs: { class: "row-open", type: "button", "data-id": row.id, onclick: () => on.open(row.id) },
        children: [content],
      });
      // 取り下げた行は、差分の表示によらず差分の印より前に札を置く
      const badge = row["withdrawn"] === true ? withdrawnBadge() : null;
      const mark = markFor({ marks, id: row.id });
      const commentPlaceElement = comments === undefined ? null : commentPlace({ id: row.id, count: comments[row.id] });
      if (badge === null && mark === null && commentPlaceElement === null) return opener;
      const fragment = document.createDocumentFragment();
      fragment.append(...[opener, badge, mark, commentPlaceElement].filter((node) => node !== null));
      return fragment;
    };
    const body =
      shownRows.length > 0
        ? shownRows.map((row) =>
            h({
              tag: "tr",
              attrs: {
                "data-id": row.id,
                // 取り下げた行は文字を薄くする
                class: [row.id === currentSelection() ? "selected" : "", row["withdrawn"] === true ? "is-withdrawn" : ""]
                  .join(" ")
                  .trim(),
              },
              children: [
                ...visible.map((column, position) =>
                  h({
                    tag: "td",
                    attrs: {
                      "data-col": position,
                      "data-pri": column.priority ?? 1,
                      class: [
                        column.num ? "num" : "",
                        column.nowrap ? "nowrap" : "",
                        position < pinned ? "pinned" : "",
                      ]
                        .join(" ")
                        .trim(),
                    },
                    children: [cellContent(column, row)],
                  }),
                ),
              ],
            }),
          )
        : [
            h({
              tag: "tr",
              children: [
                h({
                  tag: "td",
                  attrs: { colspan: visible.length, class: "no-match-cell" },
                  children: [
                    h({
                      tag: "div",
                      attrs: { class: "no-match" },
                      children: [`該当する${KIND_LABEL[kind]}はありません。別の条件を試してください。`],
                    }),
                  ],
                }),
              ],
            }),
          ];
    const grid = h({
      tag: "table",
      attrs: { class: "grid" },
      children: [
        h({ tag: "thead", children: [h({ tag: "tr", children: [...headers] })] }),
        h({ tag: "tbody", children: [...body] }),
      ],
    });
    if (previous === null) {
      wrap.append(grid);
      root.append(toolbar, wrap, pop);
    } else {
      // 描き直し: 入れ物（スクロールする要素）は残し、同じ回のうちに中身だけを差し替える
      root.querySelector(".table-toolbar")?.replaceWith(toolbar);
      wrap.replaceChildren(grid);
      root.querySelector(".pop")?.replaceWith(pop);
    }

    // ===== 配置: 固定した列の左端の位置・該当なしの文言の幅 =====
    wrapObservers.get(wrap)?.disconnect();
    const observer = new ResizeObserver(() => {
      wrap.style.setProperty("--wrap-w", `${wrap.clientWidth}px`);
      let left = 0;
      headers.forEach((header, position) => {
        if (position >= pinned) return;
        for (const cell of wrap.querySelectorAll<HTMLElement>(`[data-col="${position}"]`)) {
          cell.style.left = `${left}px`;
          cell.classList.toggle("pin-edge", position === pinned - 1);
        }
        left += header.getBoundingClientRect().width;
      });
    });
    wrapObservers.set(wrap, observer);
    observer.observe(wrap);

    // 開いたままにするポップオーバーを、表が文書に入った後に開く
    if (popover !== null) queueMicrotask(showPopover);
    return root;
  }

  // ───── 画面が共通で使う列 ─────

  /** 行から文字の値を取る */
  function text(row: Row, key: string): string | undefined {
    const value = row[key];
    return typeof value === "string" ? value : undefined;
  }

  /** 行から文字の配列を取る */
  function texts(row: Row, key: string): string[] {
    const value = row[key];
    return Array.isArray(value) ? value.map(String) : [];
  }

  /** 項目の ID を並べたセル（押すと詳細を開く）。無ければ「—」 */
  export function idLinksCell(ids: string[], open: (id: string) => void): Node {
    if (ids.length === 0) return h({ tag: "span", attrs: { class: "muted" }, children: ["—"] });
    const fragment = document.createDocumentFragment();
    for (const id of ids) {
      fragment.append(h({
        tag: "button",
        attrs: { class: "idlink", type: "button", onclick: () => open(id) },
        children: [id],
      }));
    }
    return fragment;
  }

  /** どの表にもある列（ID・タイトル・状態・対象・カテゴリー・フェーズ・タグ）を作る関数の集まり */
  export function commonColumns(settings: Settings): {
    id: Column;
    title: (label?: string) => Column;
    status: (order: readonly string[]) => Column;
    target: Column;
    category: Column;
    phase: Column;
    tags: Column;
    text: (key: string, label: string, options?: Partial<Column>) => Column;
  } {
    return {
      id: {
        key: "id",
        label: "ID",
        nowrap: true,
        get: (row) => row.id,
        cell: (row) => h({ tag: "span", attrs: { class: "mono" }, children: [row.id] }),
      },
      title: (label = "タイトル") => ({
        key: "title",
        label,
        fixed: true,
        minWidth: "16em",
        get: (row) => text(row, "title"),
      }),
      status: (order) => ({
        key: "status",
        label: "状態",
        nowrap: true,
        filterable: true,
        order,
        get: (row) => text(row, "status"),
        cell: (row) => statusBadge(text(row, "status")),
      }),
      target: {
        key: "target",
        label: settings.target_label,
        nowrap: true,
        filterable: true,
        priority: 4,
        get: (row) => text(row, "target"),
      },
      category: {
        key: "category",
        label: "カテゴリー",
        nowrap: true,
        filterable: true,
        priority: 2,
        get: (row) => text(row, "category"),
      },
      phase: {
        key: "phase",
        label: "フェーズ",
        nowrap: true,
        filterable: true,
        order: settings.phases,
        priority: 2,
        get: (row) => text(row, "phase"),
      },
      tags: {
        key: "tags",
        label: "タグ",
        filterable: true,
        priority: 4,
        get: (row) => texts(row, "tags"),
        cell: (row) => tagList(texts(row, "tags")),
      },
      text: (key, label, options = {}) => ({
        key,
        label,
        priority: 3,
        get: (row) => text(row, key),
        ...options,
      }),
    };
  }

  /** 行から文字の配列を取る（画面の列の定義で使う） */
  export function rowTexts(row: Row, key: string): string[] {
    return texts(row, key);
  }

  // ───── 画面が使う、状態を持った表 ─────

  /** 端末に残す、表ごとの表示する列とピン留め */
  export type TablePrefs = { hidden: string[]; pinTo: string | null };

  /** 表の状態（並べ替え・ポップオーバーは開いている間だけ、表示する列とピン留めは端末に残す。絞り込みは画面が持つ） */
  type TableState = {
    sort: SortState;
    popover: TablePopover | null;
    hidden: string[] | undefined;
    pinTo: string | null;
  };

  /** 種類ごとの表の状態 */
  const tableStates = new Map<Kind, TableState>();

  /** 表示する列とピン留めを変えたときの知らせ先（null は初期設定に戻したとき） */
  let prefsListener: ((kind: Kind, prefs: TablePrefs | null) => void) | null = null;

  /** 端末に残した表示する列とピン留めを入れ、変わったときの知らせ先を決める */
  export function restoreTablePrefs(
    saved: Record<string, TablePrefs>,
    listener: (kind: Kind, prefs: TablePrefs | null) => void,
  ): void {
    prefsListener = listener;
    for (const [kind, prefs] of Object.entries(saved)) {
      const state = tableState(kind as Kind);
      state.hidden = prefs.hidden;
      state.pinTo = prefs.pinTo;
    }
  }

  /** どの表の表示する列とピン留めも初期設定に戻す（「既定に戻す」で個人の上書きを外すとき） */
  export function clearTablePrefs(): void {
    for (const state of tableStates.values()) {
      state.hidden = undefined;
      state.pinTo = null;
    }
  }

  /** 種類の表の状態（無ければ作る） */
  export function tableState(kind: Kind): TableState {
    let state = tableStates.get(kind);
    if (state === undefined) {
      state = { sort: null, popover: null, hidden: undefined, pinTo: null };
      tableStates.set(kind, state);
    }
    return state;
  }

  /** 状態を持つ表を返す。並べ替え・列・ピン留めの操作は自分で描き直し、表示する列とピン留めは端末に残す。絞り込みの条件は画面から受け、チップで変えたときは `onFilter` に新しい条件を渡す */
  export function managedTable({
    kind,
    columns,
    rows,
    filters,
    onFilter,
    open,
    marks,
    comments,
  }: {
    kind: Kind;
    columns: Column[];
    rows: Row[];
    /** 絞り込みの条件（画面が絞り込みのドロワーと共有する） */
    filters: Filters;
    /** チップで条件を解除したとき、新しい条件を知らせる（描き直しは使う側が行う） */
    onFilter: (filters: Filters) => void;
    open: (id: string) => void;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks;
    /** 項目の ID → レビュー中のコメントの件数。描き直すたびに読むので、使う側が中身を更新すれば並べ替えなどの描き直しにも反映される */
    comments?: Record<string, number>;
  }): HTMLElement {
    const state = tableState(kind);
    // 画面を描き直したときは、前のポップオーバーを開いたままにしない
    state.popover = null;
    const slot = h({ tag: "div", attrs: { class: "table-slot" } });
    /** 端末に残す値が変わったことを知らせる */
    const persist = (): void => {
      prefsListener?.(kind, { hidden: state.hidden ?? [], pinTo: state.pinTo });
    };
    /** 今の表（描き直すとき、入れ物を残して中身だけ差し替える） */
    let current: HTMLElement | null = null;
    const render = (): void => {
      const next = buildTable({
        previous: current,
        props: {
          kind,
          columns,
          rows,
          sort: state.sort,
          filters,
          pinTo: state.pinTo,
          hiddenColumns: state.hidden,
          popover: state.popover,
          ...(marks === undefined ? {} : { marks }),
          ...(comments === undefined ? {} : { comments }),
          on: {
            sort: (key) => {
              // 昇順 → 降順 → 解除
              if (state.sort === null || state.sort.key !== key) state.sort = { key, dir: "asc" };
              else state.sort = state.sort.dir === "asc" ? { key, dir: "desc" } : null;
              render();
            },
            filter: onFilter,
            pin: (key) => {
              state.pinTo = state.pinTo === key ? null : key;
              persist();
              render();
            },
            columns: (hidden) => {
              state.hidden = hidden;
              persist();
              render();
            },
            reset: () => {
              state.sort = null;
              state.hidden = undefined;
              state.pinTo = null;
              state.popover = null;
              prefsListener?.(kind, null);
              render();
            },
            open,
            popover: (popover) => {
              state.popover = popover;
            },
          },
        },
      });
      // 初めて描くときだけ、表を差し込む（描き直しでは同じ表の中身が入れ替わる）
      if (current === null) {
        current = next;
        slot.replaceChildren(next);
      }
    };
    render();
    return slot;
  }
}
