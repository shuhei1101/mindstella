// 詳細パネルと詳細の全画面。項目 1 件の中身（案・本文・図・関係する項目）を出す。差分の表示の間は、選んだ時点の前後の差分も出す。

namespace MindmapPreview {
  /** 詳細パネルの引数 */
  export type DetailProps = {
    /** 項目の ID */
    id: string;
    index: RecordIndex;
    /** 全画面か */
    full: boolean;
    on: {
      /** 項目へ移る（関係する項目・本文の用語の印・項目の ID のリンク。パネルと全画面の中の移動は履歴に積む） */
      open: (id: string) => void;
      /** パネルを閉じる */
      close: () => void;
      /** 全画面表示の入り切り */
      full: (full: boolean) => void;
      /** 見てきた項目を 1 つ戻る */
      back: () => void;
      /** 見てきた項目を 1 つ進む */
      forward: () => void;
      /** 図を拡大して見る。差分の表示の間で、その図が変わっていれば前の版の記法を渡す（図の拡大が Raw の差分に使う） */
      diagram: (svg: SVGElement, diff: DiagramViewerDiff | null) => void;
      /** 本文の見出しへ移った（見出しの名前。本文に無い見出しで開いたときは null）。使う側がハッシュの `h` を、履歴に積まずに置き換える */
      heading: (heading: string | null) => void;
      /** 本文のまとまりのリンクを押した（`diff` の値）。使う側が記録にあるまとまりか確かめて、時点を選ぶ */
      changeSet: (id: string) => void;
      /** 本文の差分の並べ方の切り替えを押した（押した並べ方）。使う側が個人の上書きに残して描き直す */
      layout: (layout: BodyLayout) => void;
      /** HTML の本文の枠で文を選び終えた・選びを外した。使う側が選んだ箇所のコメントの入口を出す・閉じる */
      frame?: { select: (selection: HtmlFrameSelection) => void; clear: () => void };
    };
    /** 下端に置くコメントの入力の引数と、その項目へのレビュー中のコメント（溜めた順）と、行の修正・削除・元に戻すの引数。配る書き出しでは null（どれも置かない） */
    comment: { form: SendFormProps; reviews: ReviewState["items"]; edit: ReviewEditProps } | null;
    /** コメントの一覧から開いたとき示す箇所。本文は `start` の行を含むブロック、値は `data-key` が `key` の要素 */
    highlight?: Location | null;
    /** 変更履歴で選んだ時点。あり、項目がその時点で足されたか変わったとき、前後の差分を出す */
    diff?: DiffPoint | null;
    /** 開いたときに本文の中で画面に入れる見出しの名前（`Route.heading`）。本文に無ければ本文の頭で開き、`on.heading` を null で呼ぶ */
    heading?: string | null;
    /** 差分のミニマップを置くか（`resolveDisplay` の `minimap`）。差分の表示の間だけ置く */
    minimap?: boolean;
    /** 本文の差分の並べ方（`resolveDisplay` の `bodyLayout`）。本文の差分を描けたときだけ切り替えを置く */
    bodyLayout?: BodyLayout;
    /** 本文の表とセクションの見せ方（`resolveDisplay` の `bodyView`）。`decorateMarkdown` の `display` に渡す */
    bodyView?: BodyView;
    /** 編集の入口。配る書き出し・差分の表示中は渡さない（`null` と同じ） */
    edit?: DetailEdit | null;
    /** パネルの内側の左端に置く `panelResizer` の要素。幅 900px 以下と全画面では渡さない（`null` と同じ） */
    resizer?: HTMLElement | null;
  };

  /** 詳細パネルの編集の入口 */
  export type DetailEdit = {
    /** 編集の表示にしているか。真の間は本文のスクロール領域に `detailEditForm` を描き、下端のコメントの入力を隠す */
    editing: boolean;
    /** キーか案の記号 → 印の種類。項目の ID → 項目の印の種類（種類と ID の右に置く） */
    marks: Record<string, PendingMarkKind>;
    /** 編集の表示の引数 */
    form: DetailEditFormProps;
    /** 「編集する」「編集を終える」を押したとき */
    onToggle: () => void;
  };

  /** 図の拡大へ渡す、差分の表示の間のその図の前の版の記法 */
  export type DiagramViewerDiff = { beforeSource: string };

  /** 前の値が無いときに出す文字（差分のミニマップが、前に無かったキーを見分けるのにも使う） */
  export const NO_VALUE = "（なし）";

  /** 詳細パネルのレビュー中のコメントの行の `data-focus` の接頭辞（コメントの一覧と同時に開いても、描き直した後のフォーカスの戻し先を分ける） */
  export const REVIEW_FOCUS = "detail-";

  /** 差分に並べるキーから外す、ツールが付けるキーと本文の名前 */
  const UNDIFFED_KEYS = new Set(["id", "created", "updated", "updated_by", "history", "history_dropped_seq", "body"]);

  /** 前後を組み立てられない旨・本文の差分を出せない旨の文言 */
  const NOTE_TRIMMED = "このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。";
  const NOTE_BODY_UNAVAILABLE = "本文の差分を出せません。書き換えの後に、本文のファイルが直接書き換えられています。今の本文を出しています。";
  const NOTE_BODY_TOO_LARGE = "本文の差分を出せません。書き換えが大きく、差分を計算しきれませんでした。今の本文を出しています。";

  /** 図の前の版の記法を、図の要素に持たせる属性の名前（図の拡大が Raw の差分に読む） */
  const BEFORE_SOURCE_ATTR = "data-before-source";

  /** 前の版の図を描いて突き合わせる間、描いた SVG を置く画面の外の位置（px）と幅（px） */
  const OFFSCREEN_LEFT_PX = -10000;
  const OFFSCREEN_WIDTH_PX = 800;

  /** 差分の記号と、読み上げに残す名前 */
  const SIGNS = {
    add: { glyph: "+", name: "追加: " },
    del: { glyph: "−", name: "削除: " },
    same: { glyph: " ", name: "" },
  } as const;

  /** 項目の ID を、押すと開くボタンにする */
  function idButton(id: string, open: (id: string) => void): HTMLElement {
    return h({
      tag: "button",
      attrs: { class: "idlink", type: "button", onclick: () => open(id) },
      children: [id],
    });
  }

  /** 項目の ID の並びを、ID・題・状態の一覧にする */
  function itemList(index: RecordIndex, ids: string[], open: (id: string) => void): HTMLElement {
    return h({
      tag: "ul",
      attrs: { class: "d-list" },
      children: [
        ...ids.map((id) =>
          h({
            tag: "li",
            children: [
              idButton(id, open),
              h({ tag: "span", attrs: { class: "t" }, children: [titleOf(index, id)] }),
              statusBadge(index.byId.get(id)?.item.status),
            ],
          }),
        ),
      ],
    });
  }

  /** 見出しの付いた節 */
  function section(label: string, content: Node): HTMLElement {
    return h({
      tag: "section",
      attrs: { class: "d-sec" },
      children: [h({ tag: "h3", children: [label] }), content],
    });
  }

  /** 値を描いた要素。選んだ箇所のコメントが、描いた要素のキーのパスで値を指せるようにする */
  function valueSpan(key: string, children: Child[]): HTMLElement {
    return h({ tag: "span", attrs: { [VALUE_KEY_ATTR]: key }, children });
  }

  /** 文字列の値を Markdown で描き、見出しは最も上の段を top にして並べる（値が無ければ何も描かない。ライブラリを読めないときは改行を残した文字のまま） */
  function markdownValue({ value, top }: { value: string | undefined; top: number }): Child {
    if (value === undefined) return undefined;
    const rendered = renderValue(value);
    // 文字のままの要素には、下げる見出しが無い
    if (rendered.classList.contains("md-value-raw")) return rendered;
    lowerHeadings({ root: rendered, shift: headingShift({ roots: [rendered], top }) });
    return rendered;
  }

  /** Markdown で描く値の入れ物。選んだ箇所のコメント・示す箇所・キーの差分が、キーのパスで値を指せるようにする */
  function valueBlock(key: string, children: Child[]): HTMLElement {
    return h({ tag: "div", attrs: { class: "d-value", [VALUE_KEY_ATTR]: key }, children });
  }

  /** 読み上げにだけ残す文字 */
  function srOnly(text: string): HTMLElement {
    return h({ tag: "span", attrs: { class: "sr-only" }, children: [text] });
  }

  /** 差分の記号（見えるのは記号だけで、名前は読み上げに残す） */
  export function signMarks(op: keyof typeof SIGNS): Node[] {
    const { glyph, name } = SIGNS[op];
    return [h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: [glyph] }), ...(name === "" ? [] : [srOnly(name)])];
  }

  /** 語の面を付ける、並べた前の値（`del.df-was`）と今の値（`ins.df-now`）の対 */
  type KeyWordPair = { was: HTMLElement; now: HTMLElement };

  /** 変わったキーの前の値と今の値を並べる。前の値は取り消し線、今の値は下線。plain は面を塗らず、線と矢印だけで示す。pairs を渡すと、前後がどちらも空でない文字のとき、並べた対を語の面を付ける対として pairs に足す */
  function keyDiff({
    was,
    now,
    plain = false,
    pairs,
  }: {
    was: Child;
    now: Child;
    plain?: boolean;
    pairs?: KeyWordPair[];
  }): HTMLElement {
    const empty = (value: Child): boolean => value === null || value === undefined || value === false || value === "";
    const wasElement = h({ tag: "del", attrs: { class: "df-was" }, children: [srOnly("前の値: "), empty(was) ? NO_VALUE : was] });
    const nowElement = h({ tag: "ins", attrs: { class: "df-now" }, children: [srOnly("今の値: "), empty(now) ? NO_VALUE : now] });
    if (typeof was === "string" && typeof now === "string" && !empty(was) && !empty(now)) pairs?.push({ was: wasElement, now: nowElement });
    return h({
      tag: "span",
      attrs: { class: plain ? "df-kv df-plain" : "df-kv" },
      children: [wasElement, h({ tag: "span", attrs: { class: "df-arrow", "aria-hidden": "true" }, children: ["→"] }), nowElement],
    });
  }

  /** 控えたキーの値の対の文字（読み上げの文字を除く） */
  function keyWordNodes(root: HTMLElement): Text[] {
    return wordTextNodes(root).filter((node) => node.parentElement?.closest(".sr-only") == null);
  }

  /** 控えたキーの値の対の前後の文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
  function markKeyWords({ pairs, deadline }: { pairs: KeyWordPair[]; deadline: number }): void {
    for (const pair of pairs) {
      const wasNodes = keyWordNodes(pair.was);
      const nowNodes = keyWordNodes(pair.now);
      const inline = diffInline(wasNodes.map((node) => node.data).join(""), nowNodes.map((node) => node.data).join(""), deadline);
      if (inline === null) continue;
      wrapWords({ nodes: wasNodes, parts: inline.before, mark: "del" });
      wrapWords({ nodes: nowNodes, parts: inline.after, mark: "add" });
    }
  }

  /** キーの値を、差分に並べる文字にする。値が無ければ null */
  function valueText(value: unknown): string | null {
    if (value === undefined || value === null || value === "") return null;
    if (Array.isArray(value)) return value.length === 0 ? null : value.join("、");
    return String(value);
  }

  /** 案の値（文字列か文字列の配列）を、Markdown で描く 1 つの文字列にする。配列は「、」でつなぐ。空なら undefined */
  function optionText(value: string | string[] | undefined): string | undefined {
    if (Array.isArray(value)) return value.length === 0 ? undefined : value.join("、");
    return value;
  }

  /** 選んだ時点の前の版と後の版で値が変わったキーと、その見せ方 */
  type KeyDiffs = {
    /** そのキーの値が変わったか */
    has: (key: string) => boolean;
    /** 変わったキーは前の値と今の値を並べ、変わっていないキーは今の値のままにする。`render` で値の見せ方を変える */
    show: (key: string, render?: (value: unknown) => Child, plain?: boolean) => Child;
    /** `show` と同じ。変わったキーの前後がどちらも空でない文字なら、語の面を付ける対として `pairs` に控える（題と文字列の値の描画が描く値に使う） */
    showWords: (key: string) => Child;
    /** 語の面を付ける対（`showWords` と案の値が足す）。本文を描いた後に `markKeyWords` で囲む */
    pairs: KeyWordPair[];
    /** 前の版の項目 */
    before: Item;
  };

  /** 前の版と後の版を比べ、値が変わったキー（ツールが付けるキーと本文の名前を除く）の見せ方を返す */
  function keyDiffs(before: Item, after: Item): KeyDiffs {
    const left: Record<string, unknown> = { ...before };
    const right: Record<string, unknown> = { ...after };
    const changed = new Set(
      [...new Set([...Object.keys(left), ...Object.keys(right)])].filter(
        (key) => !UNDIFFED_KEYS.has(key) && JSON.stringify(left[key]) !== JSON.stringify(right[key]),
      ),
    );
    const pairs: KeyWordPair[] = [];
    return {
      has: (key) => changed.has(key),
      show: (key, render = valueText, plain = false) =>
        changed.has(key) ? keyDiff({ was: render(left[key]), now: render(right[key]), plain }) : render(right[key]),
      showWords: (key) =>
        changed.has(key) ? keyDiff({ was: valueText(left[key]), now: valueText(right[key]), pairs }) : valueText(right[key]),
      pairs,
      before,
    };
  }

  /** 状態の値（文字）を、印と名前の表示にする。状態を持たなければ null */
  function statusOf(value: unknown): Child {
    return typeof value === "string" ? statusBadge(value) : null;
  }

  /** 差分の表示で、開いた項目に当てる前後の版と、画面に出す項目・本文 */
  type DiffView = {
    point: DiffPoint;
    /** 新規（その時点で足した）か変更か */
    kind: DiffKind;
    /** 前後の版。新規の項目は持たない */
    versions: VersionPair | null;
    /** 前後を組み立てられたとき、変わったキーの見せ方 */
    keys: KeyDiffs | null;
    /** 画面に出す項目（前後を組み立てられたときは後の版、それ以外は今の項目） */
    shown: Item;
    /** 画面に出す本文 */
    body: string | undefined;
  };

  /** 選んだ時点で、開いた項目が足されたか変わったときの、前後の版と画面に出す内容。そうでなければ null */
  function resolveDiffView({ id, index, diff }: { id: string; index: RecordIndex; diff: DiffPoint | null }): DiffView | null {
    const entry = index.byId.get(id);
    if (diff === null || entry === undefined) return null;
    const { item } = entry;
    const body = index.data.bodies[item.body ?? ""];
    if (diff.added.has(id)) return { point: diff, kind: "new", versions: null, keys: null, shown: item, body };
    if (!diff.changed.has(id)) return null;
    const versions = buildVersions(item, body ?? "", diff);
    // 前後を組み立てられない: 今の内容を差分なしで出す
    if (versions.trimmed || versions.before === null) {
      return { point: diff, kind: "changed", versions, keys: null, shown: item, body };
    }
    return {
      point: diff,
      kind: "changed",
      versions,
      keys: keyDiffs(versions.before, versions.after),
      shown: versions.after,
      body: body === undefined ? undefined : versions.afterBody,
    };
  }

  /** 差分の表示の冒頭の帯。選んだ時点の名前と日時 */
  function diffHead(point: DiffPoint): HTMLElement {
    return h({
      tag: "div",
      attrs: { class: "df-head" },
      children: [
        h({ tag: "span", attrs: { class: "df-head-t" }, children: [icon("history"), point.name] }),
        h({ tag: "span", attrs: { class: "df-when" }, children: [point.sub] }),
      ],
    });
  }

  /** 前後を組み立てられない旨・本文の差分を出せない旨の知らせ */
  function noteBox(text: string): HTMLElement {
    return h({
      tag: "p",
      attrs: { class: "df-note", role: "note" },
      children: [icon("alert"), h({ tag: "span", children: [text] })],
    });
  }

  /** 案の採用の状態の名前（採用でも不採用でもない案は null） */
  function optionResult(option: Option | undefined): string | null {
    if (option === undefined) return null;
    return option.adopted === true ? "採用" : option.adopted === false ? "不採用" : null;
  }

  /** 検討事項の案をカードの縦並びにする（採用 / 不採用と理由、採用した案が無いときは推奨の印を出す）。previous があれば、変わった値に前の値を並べる */
  function optionCards({ options, previous, pairs }: { options: Option[]; previous: Option[] | null; pairs?: KeyWordPair[] }): HTMLElement {
    const compare = previous !== null;
    const removed = (previous ?? []).filter((entry) => !options.some((option) => option.key === entry.key));
    // 採用した案があれば採用の表示を優先し、推奨の印は出さない
    const decided = options.some((option) => option.adopted === true);
    return h({
      tag: "div",
      children: [
        ...options.map((option) => {
          const before = previous?.find((entry) => entry.key === option.key);
          const result = optionResult(option);
          const recommended = option.recommended === true && !decided;
          const rows: [string, "pros" | "cons" | "note" | "reason", string | undefined][] = [
            ["メリット", "pros", optionText(option.pros)],
            ["デメリット", "cons", optionText(option.cons)],
            ["備考", "note", option.note],
            ["理由", "reason", option.reason],
          ];
          // 前の値と違う値は前の値と今の値を並べる。前に無かった案は全ての値を足した印にする
          const beforeOf = (field: "pros" | "cons" | "note" | "reason"): string | undefined => optionText(before?.[field]);
          const shown = rows.filter(([, field, value]) => (value !== undefined && value !== "") || (compare && beforeOf(field) !== undefined));
          const valueOf = (field: "pros" | "cons" | "note" | "reason", value: string | undefined): Child =>
            compare && beforeOf(field) !== value
              ? keyDiff({ was: beforeOf(field) ?? null, now: value ?? null, pairs })
              : markdownValue({ value, top: SECTION_TOP_HEADING_LEVEL });
          const resultChild: Child =
            compare && optionResult(before) !== result ? keyDiff({ was: optionResult(before), now: result, plain: true }) : result;
          return h({
            tag: "div",
            attrs: {
              class: `opt${option.adopted === true ? " adopted" : option.adopted === false ? " rejected" : ""}${recommended ? " recommended" : ""}`,
            },
            children: [
              h({
                tag: "div",
                attrs: { class: "o-head" },
                children: [
                  h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                  valueBlock(`options[${option.key}].content`, [
                    compare && before?.content !== option.content
                      ? keyDiff({ was: before?.content ?? null, now: option.content, pairs })
                      : markdownValue({ value: option.content, top: SECTION_TOP_HEADING_LEVEL }),
                  ]),
                  recommended ? h({ tag: "span", attrs: { class: "rec-badge" }, children: [icon("star"), "推奨"] }) : null,
                  resultChild === null ? null : h({ tag: "span", attrs: { class: "res" }, children: [resultChild] }),
                ],
              }),
              shown.length > 0
                ? h({
                  tag: "dl",
                  children: [
                    ...shown.flatMap(([label, field, value]) => [
                      h({ tag: "dt", children: [label] }),
                      h({ tag: "dd", attrs: { [VALUE_KEY_ATTR]: `options[${option.key}].${field}` }, children: [valueOf(field, value)] }),
                    ]),
                  ],
                })
                : null,
            ],
          });
        }),
        // 後の版で消えた案: 全ての値を消した印で並べる
        ...removed.map((option) =>
          h({
            tag: "div",
            attrs: { class: "opt" },
            children: [
              h({
                tag: "div",
                attrs: { class: "o-head" },
                children: [
                  h({ tag: "span", attrs: { class: "key" }, children: [option.key] }),
                  h({ tag: "del", attrs: { class: "df-was" }, children: [srOnly("消した案: "), option.content] }),
                ],
              }),
            ],
          }),
        ),
      ],
    });
  }

  /** 見出しの下の、項目のキー（対象・カテゴリー・フェーズ・影響度・種類・確度・日付・更新日・タグ）の一覧。変わったキーは前の値と今の値を並べる */
  function metaList({ item, settings, diff }: { item: Item; settings: Settings; diff: KeyDiffs | null }): HTMLElement {
    const pairs: [string, keyof Item, string | undefined][] = [
      [settings.target_label, "target", item.target],
      ["カテゴリー", "category", item.category],
      ["フェーズ", "phase", item.phase],
      ["影響度", "weight", item.weight],
      ["種類", "kind", item.kind],
      ["確度", "confidence", item.confidence],
      ["日付", "date", item.date],
      ["更新日", "updated", item.updated],
      // 取り下げは値をここに出さず（題の右の札が示す）、差分の表示で変わったときだけ前後を並べる
      ["取り下げ", "withdrawn", undefined],
    ];
    const rows = pairs.flatMap(([label, key, value]) => {
      const changed = diff?.has(key) === true;
      // 値が無く、変わってもいないキーは出さない
      if ((value === undefined || value === "") && !changed) return [];
      const shown =
        diff === null
          ? value
          : key === "withdrawn"
            ? diff.show(key, (flag) => (flag === true ? withdrawnBadge() : null))
            : diff.show(key);
      return [
        h({ tag: "dt", attrs: { class: changed ? "df-key" : null }, children: [label] }),
        h({ tag: "dd", attrs: { class: changed ? "df-key" : null }, children: [shown] }),
      ];
    });
    const tagsChanged = diff?.has("tags") === true;
    if ((item.tags ?? []).length > 0 || tagsChanged) {
      rows.push(
        h({ tag: "dt", attrs: { class: tagsChanged ? "df-key" : null }, children: ["タグ"] }),
        h({ tag: "dd", attrs: { class: tagsChanged ? "df-key" : null }, children: [tagsChanged ? diff?.show("tags") : tagList(item.tags)] }),
      );
    }
    return h({ tag: "dl", attrs: { class: "d-meta" }, children: [...rows] });
  }

  /** この項目へのレビュー中のコメントの節（各行の右上の「修正」「削除」で、その場で直す・消す・戻す。チェックとまとめて送るはコメントの一覧で行う） */
  function reviewSection({ items, edit }: { items: ReviewState["items"]; edit: ReviewEditProps }): HTMLElement {
    // 消した行は元の場所（溜めた順）に「元に戻す」と共に残す
    const rows = [...items.map((item) => ({ item, gone: false })), ...edit.removed.map((item) => ({ item, gone: true }))].sort(
      (a, b) => commentNumber(a.item.id) - commentNumber(b.item.id),
    );
    return h({
      tag: "section",
      attrs: { class: "d-sec d-review" },
      children: [
        h({
          tag: "h3",
          children: ["レビュー中のコメント", h({ tag: "span", attrs: { class: "count" }, children: [items.length] })],
        }),
        rows.length === 0
          ? emptyNote("レビュー中のコメントはありません。")
          : h({
            tag: "ul",
            attrs: { class: "d-list review-list" },
            children: rows.map(({ item, gone }) => {
              if (gone) return removedReviewRow({ item, focus: REVIEW_FOCUS, on: { restore: edit.on.restore } });
              const editing = edit.editing === item.id;
              // 入力欄は修正を始めた場所だけに描く。コメントの一覧で始めた行は、ここでは本文だけにして「修正」「削除」も出さない
              const editingHere = editing && edit.editingIn === "detail";
              return h({
                tag: "li",
                attrs: { class: `review-row${editing ? " editing" : ""}`, "data-comment": item.id },
                children: [
                  h({
                    tag: "div",
                    attrs: { class: "review-main" },
                    children: [
                      item.loc === null
                        ? null
                        : h({
                          tag: "div",
                          attrs: { class: "review-loc" },
                          children: [
                            h({ tag: "span", attrs: { class: "review-loc-name" }, children: [locationLabel(item.loc)] }),
                            h({ tag: "blockquote", attrs: { class: "send-quote" }, children: [item.loc.text] }),
                          ],
                        }),
                      editingHere
                        ? reviewEditForm({
                          item,
                          body: edit.editBody,
                          error: edit.editError,
                          focus: REVIEW_FOCUS,
                          on: { saveEdit: edit.on.saveEdit, cancelEdit: edit.on.cancelEdit },
                        })
                        : h({ tag: "p", attrs: { class: "review-body" }, children: [item.body] }),
                    ],
                  }),
                  // 書き換えている行には「修正」「削除」を出さない（入力欄の「キャンセル」「修正」と並べない）
                  editing ? null : reviewRowActions({ item, focus: REVIEW_FOCUS, on: { edit: edit.on.edit, remove: edit.on.remove } }),
                ],
              });
            }),
          }),
      ],
    });
  }

  // ─── 本文の差分 ───

  /** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
  function linesOf(text: string): string[] {
    const lines = text.split("\n");
    if (lines.at(-1) === "") lines.pop();
    return lines;
  }

  /** 今の本文の行（1 始まり）のうち、差分で足した行 */
  function addedLines({ parts, now }: { parts: LinePart[]; now: string[] }): Set<number> {
    const added = new Set<number>();
    let line = 0;
    for (const part of parts) {
      if (part.kind === "removed") continue;
      for (const _ of part.lines) {
        line += 1;
        // 空行だけの足しは段落の間の空きで、どの塊も足したことにしない
        if (part.kind === "added" && (now[line - 1] ?? "").trim() !== "") added.add(line);
      }
    }
    return added;
  }

  /** 今の本文の各行が属するブロックの先頭の行を求める。図のコードブロックの中は null（図の差分が示す）。それ以外のコードブロックの中は、中身の最初の行を持つブロックに属する */
  export function blockOwners({ now, starts }: { now: string[]; starts: number[] }): (number | null)[] {
    const owners: (number | null)[] = [];
    let fence: { owner: number | null } | null = null;
    now.forEach((text, offset) => {
      const line = offset + 1;
      const opening = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
      if (fence !== null) {
        owners.push(fence.owner);
        // 閉じるフェンス（言語を持たない行）で、コードブロックを出る
        if (opening !== null && opening[2] === "") fence = null;
        return;
      }
      if (opening !== null) {
        fence = { owner: opening[2] === "mermaid" ? null : line + 1 };
        owners.push(fence.owner);
        return;
      }
      // 印を持つブロックのうち、この行以前で最も後ろのもの
      owners.push(starts.filter((start) => start <= line).at(-1) ?? null);
    });
    return owners;
  }

  /** 差分の記号を頭に置いた、足した塊・消した塊の囲み */
  export function diffBlock({ op, children }: { op: "add" | "del"; children: Node[] }): HTMLElement {
    return h({
      tag: op === "add" ? "ins" : "del",
      attrs: { class: "df-blk" },
      children: [...signMarks(op), ...children],
    });
  }

  /** 本文の足した部分の印を、今の本文の要素に付ける（段落・見出し・コードは囲み、表の行と箇条書きの項目は行の印にする） */
  function markAddedBlocks({ root, parts, source }: { root: HTMLElement; parts: LinePart[]; source: string }): void {
    const now = linesOf(source);
    const added = addedLines({ parts, now });
    if (added.size === 0) return;
    const blocks = [...root.querySelectorAll<HTMLElement>(`[${LINE_ATTR}]`)];
    const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(LINE_ATTR))) });
    const marked = new Set<number>();
    for (const line of added) {
      const owner = owners[line - 1];
      if (owner !== null && owner !== undefined) marked.add(owner);
    }
    for (const block of blocks) {
      if (!marked.has(Number(block.getAttribute(LINE_ATTR)))) continue;
      if (block.tagName === "TR") {
        block.classList.add("df-row", "df-add");
        block.firstElementChild?.prepend(...signMarks("add"));
      } else if (block.tagName === "LI") {
        block.classList.add("df-li-add");
        block.prepend(...signMarks("add"));
      } else {
        // 囲みを元の位置に置いてから、ブロックを囲みの中へ移す
        const wrapper = diffBlock({ op: "add", children: [] });
        block.replaceWith(wrapper);
        wrapper.append(block);
      }
    }
  }

  /** 消した行を別に描いた要素から、行の印を外す（今の本文の行に対応づけない） */
  export function withoutLineMarks(root: HTMLElement): HTMLElement {
    for (const element of root.querySelectorAll(`[${LINE_ATTR}]`)) element.removeAttribute(LINE_ATTR);
    return root;
  }

  /** 消した行の図のコードブロックを、記法の原文だけにする（描かない） */
  function plainDiagrams(root: HTMLElement): void {
    for (const figure of root.querySelectorAll("figure.diagram")) {
      const source = figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
      figure.replaceWith(h({ tag: "pre", attrs: { class: "dg-raw" }, children: [source] }));
    }
  }

  /** 消した行のかたまりを、別に Markdown として描いた要素にする */
  function renderRemoved(block: RemovedBlock): HTMLElement {
    const lines = block.tableHeader === null ? block.lines : [...block.tableHeader, ...block.lines];
    const rendered = withoutLineMarks(renderMarkdown(lines.join("\n")));
    plainDiagrams(rendered);
    return rendered;
  }

  /** 描いた消した行のかたまりと、それが元になる `RemovedBlock` の組 */
  type RenderedRemoved = { block: RemovedBlock; rendered: HTMLElement };

  /** 描いた消した行のかたまりを、今の本文の差し込む場所の前（無ければ本文の最後）へ差し込む。かたまりごとに、差し込んだ語の面を付ける対象のブロックを返す */
  function insertRemovedBlocks({ root, blocks }: { root: HTMLElement; blocks: RenderedRemoved[] }): HTMLElement[][] {
    // 差し込む前の、行の印を持つ今のブロック（差し込む要素は印を持たない）
    const stamped = [...root.querySelectorAll<HTMLElement>(`[${LINE_ATTR}]`)];
    const lineOf = (element: Element): number => Number(element.getAttribute(LINE_ATTR));
    const placed: HTMLElement[][] = [];
    for (const { block, rendered } of blocks) {
      const target = block.beforeLine === null ? undefined : stamped.find((element) => lineOf(element) >= (block.beforeLine ?? 0));
      const previous = target === undefined ? stamped.at(-1) : stamped[stamped.indexOf(target) - 1];
      // 表の本体の行だけ: 今の表の行の間（表の最後の後も）へ、消した行の印を付けた行として差し込む
      if (block.tableHeader !== null) {
        const rows = [...rendered.querySelectorAll<HTMLElement>("tbody tr")].map((row) => {
          row.classList.add("df-row", "df-del");
          row.firstElementChild?.prepend(...signMarks("del"));
          return row;
        });
        if (target?.tagName === "TR") {
          target.before(...rows);
          placed.push(rows);
          continue;
        }
        if (previous?.tagName === "TR") {
          previous.after(...rows);
          placed.push(rows);
          continue;
        }
      }
      // 囲みの中へ移す前に、語の面を付ける対象のブロックを引く
      placed.push(wordBlocksIn(rendered));
      const piece = diffBlock({ op: "del", children: [...rendered.childNodes] });
      if (target === undefined) {
        root.append(piece);
        continue;
      }
      // 足した塊の囲みの中・箇条書きや表の中ではなく、その外側の前へ差し込む（表は包む入れ物ごと外側にする）
      const outer = target.parentElement?.matches("ins.df-blk") === true ? target.parentElement : target;
      const container = outer.closest("ul, ol, table") ?? outer;
      (container.parentElement?.matches(`.${TABLE_WRAP_CLASS}`) === true ? container.parentElement : container).before(piece);
    }
    return placed;
  }

  /** 前の本文の図のコードブロック（開く行から閉じる行まで。1 始まり）。閉じていないコードブロックは本文の最後まで */
  function diagramFenceRanges(lines: string[]): { open: number; close: number }[] {
    const ranges: { open: number; close: number }[] = [];
    let open: number | null = null;
    lines.forEach((text, offset) => {
      const fence = /^\s*(`{3,}|~{3,})\s*(\S*)/.exec(text);
      if (fence === null) return;
      if (open === null) {
        if (fence[2] === "mermaid") open = offset + 1;
      } else if (fence[2] === "") {
        ranges.push({ open, close: offset + 1 });
        open = null;
      }
    });
    if (open !== null) ranges.push({ open, close: lines.length });
    return ranges;
  }

  /** 消した行のうち、図のコードブロックの一部だけを消した分を外す（図の差分が示すので、本文には消した行として差し込まない）。図を丸ごと消した分は残す */
  function withoutDiagramEdits({ parts, before }: { parts: LinePart[]; before: string }): LinePart[] {
    const ranges = diagramFenceRanges(linesOf(before));
    if (ranges.length === 0) return parts;
    let line = 0;
    return parts.flatMap((part) => {
      if (part.kind === "added") return [part];
      const first = line + 1;
      line += part.lines.length;
      if (part.kind === "same") return [part];
      const last = line;
      // この消した部分に丸ごと入っていない図のコードブロックの行
      const partial = ranges.filter((range) => range.open < first || range.close > last);
      const kept = part.lines.filter((_, offset) => !partial.some((range) => first + offset >= range.open && first + offset <= range.close));
      return kept.length === 0 ? [] : [{ kind: part.kind, lines: kept }];
    });
  }

  /** 語の面を付ける対象になる、描いたブロック（段落・見出し・箇条書きの項目・表の本体の行）の選び方 */
  const WORD_BLOCK_SELECTOR = "p, h1, h2, h3, h4, h5, h6, li, tbody tr";

  /** 語の面を付ける対象のブロックか（ほかの対象のブロックを中に持たないもの） */
  function isWordBlock(element: Element): boolean {
    return element.matches(WORD_BLOCK_SELECTOR) && element.querySelector(WORD_BLOCK_SELECTOR) === null;
  }

  /** 要素の中の、語の面を付ける対象のブロック（文書の順） */
  export function wordBlocksIn(root: HTMLElement): HTMLElement[] {
    return [...root.querySelectorAll<HTMLElement>(WORD_BLOCK_SELECTOR)].filter(isWordBlock);
  }

  /** 足した部分ごとの、足した行（空行を除く）を持つ今のブロックのうち、語の面を付ける対象のもの（足した行の順） */
  function addedBlocksByPart({ root, parts, now }: { root: HTMLElement; parts: LinePart[]; now: string[] }): Map<number, HTMLElement[]> {
    const blocks = [...root.querySelectorAll<HTMLElement>(`[${LINE_ATTR}]`)];
    const owners = blockOwners({ now, starts: blocks.map((block) => Number(block.getAttribute(LINE_ATTR))) });
    const byStart = new Map(blocks.map((block) => [Number(block.getAttribute(LINE_ATTR)), block]));
    const found = new Map<number, HTMLElement[]>();
    let line = 0;
    parts.forEach((part, position) => {
      if (part.kind === "removed") return;
      const here: HTMLElement[] = [];
      for (const _ of part.lines) {
        line += 1;
        // 空行だけの足しは段落の間の空きで、どのブロックも足したことにしない
        if (part.kind !== "added" || (now[line - 1] ?? "").trim() === "") continue;
        const owner = owners[line - 1];
        const block = owner === null || owner === undefined ? undefined : byStart.get(owner);
        if (block !== undefined && isWordBlock(block) && !here.includes(block)) here.push(block);
      }
      if (part.kind === "added") found.set(position, here);
    });
    return found;
  }

  /** 語の面を付ける、消したブロックと足したブロックの対 */
  export type WordPair = { removed: HTMLElement; added: HTMLElement };

  /** 変えた行の対（`pairedParts`）ごとに、消した部分から描いたブロックと、足した部分の行を持つ今のブロックを前から順に並べ、両方の数が同じときだけ 1 つずつ対にする */
  function wordPairs({
    root,
    parts,
    now,
    placed,
  }: {
    root: HTMLElement;
    parts: LinePart[];
    now: string[];
    placed: HTMLElement[][];
  }): WordPair[] {
    // 消した部分の並びの何番目か（`placed` は消した部分の順）
    const removedOrder = parts.flatMap((part, position) => (part.kind === "removed" ? [position] : []));
    const addedBlocks = addedBlocksByPart({ root, parts, now });
    return pairedParts(parts).flatMap(({ removed, added }) => {
      const removedList = placed[removedOrder.indexOf(removed)] ?? [];
      const addedList = addedBlocks.get(added) ?? [];
      if (removedList.length === 0 || removedList.length !== addedList.length) return [];
      return removedList.map((block, offset) => ({ removed: block, added: addedList[offset]! }));
    });
  }

  /** 要素の中の、行の印（`signMarks` が入れる記号と読み上げの文字）と、表・リストの構造の間の整形の空白を除いた文字のノード（文書の順） */
  function wordTextNodes(root: HTMLElement): Text[] {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => {
        const parent = node.parentElement;
        const isSign = parent?.closest(".df-sign") != null || parent?.matches(".df-sign + .sr-only") === true;
        const isLayoutSpace = (node.textContent ?? "").trim() === "" && parent?.matches("table, thead, tbody, tr, ul, ol") === true;
        return isSign || isLayoutSpace ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      },
    });
    const nodes: Text[] = [];
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) nodes.push(node as Text);
    return nodes;
  }

  /** 変わった語の面の要素 */
  function wordMark({ mark, text }: { mark: "add" | "del"; text: string }): HTMLElement {
    return h({ tag: "span", attrs: { class: `df-word df-${mark}` }, children: [text] });
  }

  /** 文字のノードの並びのうち、語の差分の足した・消した部分を面の要素で囲む（ノードをまたぐ部分はノードごとに囲み、ノードの外の要素は分けない） */
  function wrapWords({ nodes, parts, mark }: { nodes: Text[]; parts: InlinePart[]; mark: "add" | "del" }): void {
    // 同じでない部分の、文字の頭からの範囲
    const ranges: { start: number; end: number }[] = [];
    let offset = 0;
    for (const part of parts) {
      if (part.kind !== "same") ranges.push({ start: offset, end: offset + part.text.length });
      offset += part.text.length;
    }
    let nodeStart = 0;
    for (const node of nodes) {
      const text = node.data;
      const nodeEnd = nodeStart + text.length;
      const pieces: (string | HTMLElement)[] = [];
      // ノードの中で、ここまでを pieces に入れた位置
      let cursor = 0;
      for (const range of ranges) {
        const from = Math.max(range.start, nodeStart) - nodeStart;
        const to = Math.min(range.end, nodeEnd) - nodeStart;
        if (from >= to) continue;
        if (from > cursor) pieces.push(text.slice(cursor, from));
        pieces.push(wordMark({ mark, text: text.slice(from, to) }));
        cursor = to;
      }
      nodeStart = nodeEnd;
      if (pieces.length === 0) continue;
      if (cursor < text.length) pieces.push(text.slice(cursor));
      node.replaceWith(...pieces);
    }
  }

  /** 対の 2 つのブロックの、行の印を除いた文字を語の単位で比べ、変わった語を濃い面で囲む。比べられなかった対には付けない */
  export function markWords({ pair, deadline }: { pair: WordPair; deadline: number }): void {
    const removedNodes = wordTextNodes(pair.removed);
    const addedNodes = wordTextNodes(pair.added);
    const inline = diffInline(removedNodes.map((node) => node.data).join(""), addedNodes.map((node) => node.data).join(""), deadline);
    if (inline === null) return;
    wrapWords({ nodes: removedNodes, parts: inline.before, mark: "del" });
    wrapWords({ nodes: addedNodes, parts: inline.after, mark: "add" });
  }

  /** 描いた本文の差分。`markWords` は、見出し・本文のリンクを付けた後に呼んで、変えた行の対に語の面を付ける */
  type BodyDiff = { root: HTMLElement; markWords: () => void };

  /** 埋め込んだ HTML の範囲の中の行の差分を、本文の行の差分から外す（範囲の差分は範囲ごとの部品が出す）。前の版の範囲の中の消した行は落とし、今の範囲の中の足した行は変えていない行にして、今の本文の行の数は変えない */
  function withoutEmbeddedHtmlEdits({ parts, before, after }: { parts: LinePart[]; before: string; after: string }): LinePart[] {
    /** 範囲の印の行を含む、範囲の中の行（1 始まり） */
    const linesInRanges = (source: string): Set<number> => {
      const lines = new Set<number>();
      for (const { open, close } of embeddedHtmlRanges(source)) for (let line = open; line <= close; line += 1) lines.add(line);
      return lines;
    };
    const inBefore = linesInRanges(before);
    const inAfter = linesInRanges(after);
    const result: LinePart[] = [];
    /** 同じ種類が続くときは 1 つの並びにまとめて足す */
    const push = (kind: LinePart["kind"], line: string): void => {
      const last = result[result.length - 1];
      if (last?.kind === kind) last.lines.push(line);
      else result.push({ kind, lines: [line] });
    };
    let beforeLine = 1;
    let afterLine = 1;
    for (const part of parts) {
      for (const line of part.lines) {
        if (part.kind === "removed") {
          if (!inBefore.has(beforeLine)) push("removed", line);
          beforeLine += 1;
        } else if (part.kind === "added") {
          push(inAfter.has(afterLine) ? "same" : "added", line);
          afterLine += 1;
        } else {
          push("same", line);
          beforeLine += 1;
          afterLine += 1;
        }
      }
    }
    return result;
  }

  /** 範囲の直下の要素を並びで比べるための文字列にする（描くたびに変わる部品の連番は揃える） */
  function childSignature(element: Element): string {
    return element.outerHTML.replace(/mdmark-(diagram|param)-\d+-\d+/g, "mdmark-$1");
  }

  /** 差分の表示の間、変わった埋め込んだ HTML の範囲を、範囲の差分（変更前・変更後の描いた結果と原文の差分）に置き換える。範囲の直下の要素のうち、足した要素と変えた要素にマーカーを付けた今の範囲を、変更後の描いた結果にする */
  function replaceChangedRanges({ root, before, after }: { root: HTMLElement; before: string; after: string }): void {
    const ranges = [...root.querySelectorAll<HTMLElement>(`.${EMBEDDED_HTML_CLASS}`)];
    for (const pair of pairEmbeddedHtml({ before, after })) {
      const element = ranges[pair.order];
      if (element === undefined) continue;
      // 選んだ時点の範囲を、範囲の印で包んで描く
      const beforeView = renderMarkdown(`<!-- html -->\n${pair.before}\n<!-- /html -->\n`);
      const beforeRange = beforeView.querySelector(`.${EMBEDDED_HTML_CLASS}`);
      if (beforeRange === null) continue;
      const marks = childMarks({ before: [...beforeRange.children].map(childSignature), after: [...element.children].map(childSignature) });
      marks?.forEach((mark, position) => {
        if (mark !== null) element.children[position]?.setAttribute("data-df", mark === "added" ? "add" : "chg");
      });
      // 今の範囲を差分の部品へ移す間、置き場所を残す。差分を計算しきれなかったら今の範囲のまま戻す
      const placeholder = document.createComment("");
      element.replaceWith(placeholder);
      const diff = htmlBodyDiff({ before: pair.before, after: pair.after, marked: "", initial: "raw", heading: "埋め込んだ HTML", beforeView, afterView: element });
      placeholder.replaceWith(diff ?? element);
    }
  }

  /** 前後の本文を行ごとに比べ、今の本文を描いて足した部分と消した部分に印を付ける。差分を計算しきれなかったら null */
  function renderBodyDiff({ before, after, deadline }: { before: string; after: string; deadline: number }): BodyDiff | null {
    const compared = diffLineParts(before, after);
    if (compared === null) return null;
    const parts = withoutDiagramEdits({ parts: withoutEmbeddedHtmlEdits({ parts: compared, before, after }), before });
    const rendered = renderMarkdown(after);
    const removed = placeRemovedBlocks(parts).map((block) => ({ block, rendered: renderRemoved(block) }));
    // 今の本文と消した部分の見出しを合わせた最も上の段から、段の差を 1 つ求める
    const shift = headingShift({ roots: [rendered, ...removed.map((piece) => piece.rendered)] });
    lowerHeadings({ root: rendered, shift });
    for (const piece of removed) lowerHeadings({ root: piece.rendered, shift });
    markAddedBlocks({ root: rendered, parts, source: after });
    const placed = insertRemovedBlocks({ root: rendered, blocks: removed });
    const pairs = wordPairs({ root: rendered, parts, now: linesOf(after), placed });
    return { root: rendered, markWords: () => pairs.forEach((pair) => markWords({ pair, deadline })) };
  }

  // ─── 図の差分 ───

  /** 記法の 1 行目の語（図の種類）。先頭の設定の行（`%%`）と空行は読み飛ばす */
  function diagramType(source: string): string {
    const first = source
      .split("\n")
      .map((line) => line.trim())
      .find((line) => line !== "" && !line.startsWith("%%"));
    return first?.split(/\s+/)[0] ?? "";
  }

  /** 行の差分を比べやすいよう、記法の末尾を改行 1 つにそろえる */
  function withTrailingNewline(source: string): string {
    return source.endsWith("\n") ? source : `${source}\n`;
  }

  /** 記法の行ごとの差分を、足した行（+）・消した行（−）の印つきの行にする。変えた行の対は、変わった語を濃い面で囲む（`deadline` は、行の差分を呼ぶ直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
  export function rawDiffLines({ parts, deadline }: { parts: LinePart[]; deadline: number }): HTMLElement[] {
    const op = { added: "add", removed: "del", same: "same" } as const;
    // 対の行ごとの語の差分（`parts` の添え字 → 行ごと）。対の行ごとに 1 回だけ比べ、消した側と足した側に同じ結果を使う
    const inlines = new Map<number, (InlineDiff | null)[]>();
    for (const { removed, added } of pairedParts(parts)) {
      const removedLines = parts[removed]?.lines ?? [];
      const addedLines = parts[added]?.lines ?? [];
      const compared = removedLines.map((text, offset) => diffInline(text, addedLines[offset] ?? "", deadline));
      inlines.set(removed, compared);
      inlines.set(added, compared);
    }
    return parts.flatMap((part, position) =>
      part.lines.map((text, offset) => {
        const inline = inlines.get(position)?.[offset] ?? null;
        const pieces = inline === null ? null : part.kind === "removed" ? inline.before : inline.after;
        return h({
          tag: "span",
          attrs: { class: `df-line${part.kind === "same" ? "" : ` df-${op[part.kind]}`}` },
          children: [
            ...signMarks(op[part.kind]),
            ...(pieces === null ? [text] : pieces.map((piece) => (piece.kind === "same" ? piece.text : wordMark({ mark: part.kind === "removed" ? "del" : "add", text: piece.text })))),
          ],
        });
      }),
    );
  }

  /** 前後の版の図の記法の並びから、今の図ごとの前の版の記法を決める。前の版と同じ図は null、前に無い図は空文字列。同じ記法の図を先に組にし、残りを並びの順で組にする */
  function pairDiagrams({ before, after }: { before: string[]; after: string[] }): (string | null)[] {
    const free = new Set(before.keys());
    const unchanged = after.map((source) => {
      const match = [...free].find((candidate) => (before[candidate] ?? "").trim() === source.trim());
      if (match === undefined) return false;
      free.delete(match);
      return true;
    });
    const rest = [...free];
    return after.map((_, position) => {
      if (unchanged[position] === true) return null;
      const next = rest.shift();
      return next === undefined ? "" : (before[next] ?? "");
    });
  }

  /** 図の下に出す、凡例と「消したもの」 */
  function diagramNotes({ colored, removed }: { colored: boolean; removed: string[] }): HTMLElement {
    const legend = colored
      ? h({
        tag: "div",
        attrs: { class: "df-legend" },
        children: [
          h({ tag: "span", attrs: { class: "df-lg df-lg-add" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "足した"] }),
          h({ tag: "span", attrs: { class: "df-lg df-lg-chg" }, children: [h({ tag: "i", attrs: { "aria-hidden": "true" } }), "変わった"] }),
        ],
      })
      : h({
        tag: "div",
        attrs: { class: "df-legend" },
        children: [
          h({ tag: "span", attrs: { class: "df-badge df-chg" }, children: [icon("changed"), "変わった図"] }),
          h({ tag: "span", attrs: { class: "muted" }, children: ["図の中の変更は Raw で見られます"] }),
        ],
      });
    return h({
      tag: "figcaption",
      attrs: { class: "df-notes" },
      children: [
        legend,
        removed.length === 0
          ? null
          : h({
            tag: "div",
            attrs: { class: "df-removed" },
            children: [
              h({ tag: "span", attrs: { class: "df-removed-t" }, children: ["消したもの"] }),
              h({
                tag: "ul",
                children: removed.map((name) =>
                  h({ tag: "li", children: [h({ tag: "span", attrs: { class: "df-sign", "aria-hidden": "true" }, children: ["−"] }), srOnly("消した: "), name] }),
                ),
              }),
            ],
          }),
      ],
    });
  }

  /** 図の差分で見つけた要素に色の印を付ける（ノードは枠と面、辺は線、メッセージは文字と線） */
  function paintDiagramElement({ element, mode }: { element: Element; mode: "add" | "chg" }): void {
    if (element.matches("text")) {
      element.classList.add(`df-t-${mode}`);
      element.nextElementSibling?.classList.add(`df-e-${mode}`);
      return;
    }
    element.classList.add(element.matches("path") ? `df-e-${mode}` : `df-n-${mode}`);
  }

  /** 前の版の図を `renderDiagramSvg` で描き、今の版の図と `diffDiagram` で突き合わせる。前の版の図を描けないときと、色を付けない種類・突き合わせを打ち切ったときは null */
  async function diffByRenderedBefore({ type, beforeSource, afterSvg }: { type: string; beforeSource: string; afterSvg: SVGElement }): Promise<DiagramDiff | null> {
    const beforeSvg = await renderDiagramSvg(beforeSource);
    if (beforeSvg === null) return null;
    // 前の版の図は、座標を取れるよう画面の外に置いて突き合わせる
    const offscreen = h({
      tag: "div",
      attrs: {
        "aria-hidden": "true",
        style: `position:absolute;top:0;left:${OFFSCREEN_LEFT_PX}px;width:${OFFSCREEN_WIDTH_PX}px`,
      },
      children: [beforeSvg],
    });
    document.body.append(offscreen);
    const diagram = diffDiagram(type, beforeSvg, afterSvg);
    offscreen.remove();
    return diagram;
  }

  /** 変わった図に、色・凡例と消したもの・Raw の行ごとの差分を付ける。前の版の図を描けない・色を付けない種類・突き合わせを打ち切ったときは、図の枠に色を付ける */
  export async function decorateDiagram({ figure, beforeSource }: { figure: HTMLElement; beforeSource: string }): Promise<void> {
    const holder = figure.querySelector<HTMLElement>(".mermaid");
    const afterSource = holder?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
    figure.classList.add("df-changed", "df-frame");
    // Raw: 記法の行ごとの差分（打ち切ったときは今の記法のまま）
    const raw = figure.querySelector<HTMLElement>(":scope > .dg-raw");
    const deadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
    const parts = diffLineParts(withTrailingNewline(beforeSource), withTrailingNewline(afterSource));
    if (raw !== null && parts !== null) {
      raw.classList.add("df-raw");
      raw.replaceChildren(...rawDiffLines({ parts, deadline }));
    }
    const type = diagramType(afterSource);
    const afterSvg = holder?.querySelector<SVGElement>("svg") ?? null;
    let colored = false;
    let removed: string[] = [];
    if (afterSvg !== null && COLORED_DIAGRAM_TYPES.includes(type) && beforeSource.trim() !== "") {
      // flowchart は前後の記法の解析で突き合わせ、前の版を描かない。null（flowchart でない・解析できない）の図だけ前の版を描く
      const diagram =
        (await diffDiagramFromSource(type, beforeSource, afterSource, afterSvg)) ?? (await diffByRenderedBefore({ type, beforeSource, afterSvg }));
      if (diagram !== null) {
        for (const element of diagram.added) paintDiagramElement({ element, mode: "add" });
        for (const element of diagram.changed) paintDiagramElement({ element, mode: "chg" });
        removed = diagram.removed;
        colored = true;
      }
    }
    figure.classList.toggle("df-frame", !colored);
    figure.classList.toggle("df-colored", colored);
    figure.append(diagramNotes({ colored, removed }));
    // 図の拡大が、同じ凡例と Raw の差分を出せるようになる
    figure.setAttribute(BEFORE_SOURCE_ATTR, beforeSource);
  }

  /** 差分の表示の間、今の本文の図のうち前の版から変わったものを、色・凡例・Raw の差分で示す */
  function decorateDiagrams({ root, before }: { root: HTMLElement; before: string }): void {
    const afterFigures = [...root.querySelectorAll<HTMLElement>("figure.diagram")];
    if (afterFigures.length === 0) return;
    const sourceOf = (figure: ParentNode): string => figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
    const beforeSources = [...renderMarkdown(before).querySelectorAll("figure.diagram")].map(sourceOf);
    const pairs = pairDiagrams({ before: beforeSources, after: afterFigures.map(sourceOf) });
    afterFigures.forEach((figure, position) => {
      const beforeSource = pairs[position];
      // 前の版と同じ図は印を付けない
      if (beforeSource === null || beforeSource === undefined) return;
      void decorateDiagram({ figure, beforeSource });
    });
  }

  // ─── 詳細の中身 ───

  /** 詳細の中身の引数 */
  type BodyProps = {
    id: string;
    index: RecordIndex;
    on: DetailProps["on"];
    /** その項目へのレビュー中のコメントと、行の修正・削除・元に戻すの引数。配る書き出しでは null（節を置かない） */
    review: { items: ReviewState["items"]; edit: ReviewEditProps } | null;
    view: DiffView | null;
    bodyLayout: BodyLayout;
    bodyView: BodyView;
  };

  /** 資料の HTML の本文の枠が持つ属性（コメントの一覧から開いたとき、示す箇所を求める枠を引く） */
  const HTML_BODY_ATTR = "data-html-body";

  /** Markdown の本文の中の `html` のコードブロックの入れ物を、枠に置き換える。差分の表示の間の足した・消した部分は、枠に描かず原文に印を付けたまま出す */
  function drawHtmlBlocks(root: HTMLElement): void {
    for (const block of root.querySelectorAll<HTMLElement>(`.${HTML_BLOCK_CLASS}`)) {
      const source = block.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
      if (block.closest(".df-blk") !== null) {
        block.replaceWith(h({ tag: "pre", attrs: { class: "html-block-src" }, children: [source] }));
      } else {
        const frame = htmlBodyFrame({ source, selectable: false, label: "html のコードブロック" });
        frame.classList.add(HTML_BLOCK_CLASS);
        const line = block.getAttribute(LINE_ATTR);
        if (line !== null) frame.setAttribute(LINE_ATTR, line);
        block.replaceWith(frame);
      }
    }
  }

  /** 項目の中身（種類ごと）。本文は Markdown と図を描く */
  function detailBody({ id, index, on, review, view, bodyLayout, bodyView }: BodyProps): HTMLElement {
    const entry = index.byId.get(id);
    const body = h({ tag: "div", attrs: { class: "detail" } });
    if (entry === undefined) return body;
    const { kind } = entry;
    const item = view?.shown ?? entry.item;
    const keys = view?.keys ?? null;
    const related = relatedItems({ id, index });
    /** キーの値。変わっていれば前の値と今の値を並べる */
    const textOf = (key: string, value: string | undefined): Child => (keys?.has(key) === true ? keys.showWords(key) : value);
    const labelled = ({ label, key, value, top }: { label: string; key: string; value: string | undefined; top: number }): HTMLElement | null => {
      const changed = keys?.has(key) === true;
      if ((value === undefined || value === "") && !changed) return null;
      return h({
        tag: "div",
        attrs: { class: changed ? "d-answer df-key" : "d-answer" },
        children: [h({ tag: "b", children: [label] }), valueBlock(key, [changed ? textOf(key, value) : markdownValue({ value, top })])],
      });
    };
    /** 資料・調査の説明の節（値があるとき、または値が変わったときだけ）。値が変わっていれば、前の値と今の値を並べる */
    const descriptionSection = (): HTMLElement | null => {
      const changed = keys?.has("description") === true;
      if ((item.description === undefined || item.description === "") && !changed) return null;
      const described = section("説明", valueBlock("description", [changed ? textOf("description", item.description) : markdownValue({ value: item.description, top: SECTION_TOP_HEADING_LEVEL })]));
      // 見た目は結論と同じ、灰色の面に小さな名前を添えた形
      described.classList.add("d-answer");
      return described;
    };
    /** 取り下げた理由の節（検討事項・タスクの `reason` は別の節が持つ）。値が変わっていれば、前の値と今の値を並べる */
    const withdrawnReason = (): HTMLElement | null => {
      if (kind === "decisions" || kind === "tasks") return null;
      const changed = keys?.has("reason") === true;
      if ((item.reason === undefined || item.reason === "") && !changed) return null;
      return section(
        "取り下げた理由",
        valueBlock("reason", [changed ? textOf("reason", item.reason) : markdownValue({ value: item.reason, top: SECTION_TOP_HEADING_LEVEL })]),
      );
    };
    /** 見出しの下の 1 段落 */
    const lead = (key: string, value: string | undefined, className: string | null): HTMLElement | null => {
      if ((value === undefined || value === "") && keys?.has(key) !== true) return null;
      return h({
        tag: "div",
        attrs: { class: className, [VALUE_KEY_ATTR]: key },
        children: [keys?.has(key) === true ? textOf(key, value) : markdownValue({ value, top: TITLE_TOP_HEADING_LEVEL })],
      });
    };
    let keysMarked = false;
    /** キーの値の語の面を、1 回だけ付ける。deadline は本文の語の差分と共有する（本文の差分を描かないときは、比べる直前の時刻に `LINE_DIFF_TIMEOUT_MS` を足した時刻） */
    const markKeys = (deadline: number): void => {
      if (keys === null || keysMarked) return;
      keysMarked = true;
      markKeyWords({ pairs: keys.pairs, deadline });
    };
    /** 本文の節。本文の図を描き、図の道具（拡大・Raw・コピー）を動かす。差分の表示の間は、本文と図の差分を重ねる */
    const bodySection = (label: string): HTMLElement | null => {
      const source = view?.body ?? index.data.bodies[item.body ?? ""];
      if (source === undefined) return null;
      if (bodyFormatOf(item.body) === "html") return htmlBodySection({ label, source });
      let rendered: HTMLElement | null = null;
      let markBodyWords: (() => void) | null = null;
      let bodyDeadline: number | null = null;
      let notice: HTMLElement | null = null;
      let diagramBefore: string | null = null;
      // 左右に並べた本文（並べ方が「左右に並べる」のとき）と、並べ方の切り替え
      let side: SideBySideBodyDiff | null = null;
      let layoutBar: HTMLElement | null = null;
      const versions = view?.versions ?? null;
      if (versions !== null && versions.before !== null && !versions.trimmed) {
        if (missingLibraries(["jsdiff"]).length > 0) {
          // jsdiff を読めない: 本文・図・Raw は今の版を差分なしで描く
          notice = libraryNotice({ names: ["jsdiff"], what: "本文と図の差分" });
        } else if (versions.beforeBody === null) {
          notice = noteBox(NOTE_BODY_UNAVAILABLE);
        } else {
          diagramBefore = versions.beforeBody;
          // 語の差分は、行の差分を呼ぶ前に決めたこの時刻の内に収める（行の差分を打ち切ったときも、キーの値の語の差分と共有する）
          bodyDeadline = performance.now() + LINE_DIFF_TIMEOUT_MS;
          const bodyDiff = renderBodyDiff({ before: versions.beforeBody, after: source, deadline: bodyDeadline });
          rendered = bodyDiff?.root ?? null;
          markBodyWords = bodyDiff?.markWords ?? null;
          if (rendered === null) {
            notice = noteBox(NOTE_BODY_TOO_LARGE);
          } else if (versions.beforeBody !== source) {
            // 本文が選んだ時点から変わっていて差分を描けたときだけ、並べ方の切り替えを置く
            side =
              bodyLayout === "side"
                ? sideBySideBodyDiff({ before: versions.beforeBody, after: source, lined: source === index.data.bodies[item.body ?? ""], deadline: bodyDeadline })
                : null;
            if (bodyLayout === "side" && side === null) {
              notice = noteBox(NOTE_BODY_TOO_LARGE);
            } else {
              layoutBar = h({ tag: "div", attrs: { class: "body-diff-bar" }, children: [bodyDiffLayoutSwitch({ layout: bodyLayout, on: { change: on.layout } })] });
            }
          }
        }
      }
      const root = rendered ?? renderMarkdown(source);
      if (rendered === null) lowerHeadings({ root, shift: headingShift({ roots: [root] }) });
      // 本文の差分（インライン）の間は、変わった埋め込んだ HTML の範囲を範囲の差分に置き換える
      if (rendered !== null && diagramBefore !== null) replaceChangedRanges({ root, before: diagramBefore, after: source });
      // 古いまとまりを選び、その後に本文を直した: 描いた本文は今の本文の行と合わないので、行の印を外す（選んだ箇所のコメントも示す箇所も今の行に向けない）
      if (source !== index.data.bodies[item.body ?? ""]) withoutLineMarks(root);
      // 見出しのリンクと、本文の用語・項目の ID の印を付ける
      linkHeadings({
        root,
        onHeading: (slug) => {
          scrollToHeading({ root, slug });
          on.heading(slug);
        },
        onChangeSet: on.changeSet,
      });
      linkBody({ root, index, selfId: id, onOpen: on.open, source });
      drawHtmlBlocks(root);
      // 表の列の固定・見出しの固定・しま模様と、見出しの開閉を当てる（本文の差分には開閉を置かない）
      decorateMarkdown({ root, display: bodyView, fold: rendered === null });
      // 左右に並べた本文にも、見出しのリンクと本文の印を付ける（右の列だけが今の本文の行を持つ）
      for (const [position, column] of (side?.columns ?? []).entries()) {
        linkHeadings({
          root: column,
          onHeading: (slug) => {
            scrollToHeading({ root: column, slug });
            on.heading(slug);
          },
          onChangeSet: on.changeSet,
        });
        // 左の列は選んだ時点の本文、右の列は今の本文を描いたもの
        linkBody({ root: column, index, selfId: id, onOpen: on.open, source: position === 0 ? (diagramBefore ?? source) : source });
        drawHtmlBlocks(column);
        decorateMarkdown({ root: column, display: bodyView, fold: false });
      }
      // 語の面は、リンクと用語の印を付けた後に付ける（印の要素は分けず、中の文字だけを囲む）。キーの値の語の面を先に付ける
      if (bodyDeadline !== null) markKeys(bodyDeadline);
      markBodyWords?.();
      side?.markWords();
      const drawn = renderDiagrams(root);
      if (diagramBefore !== null) {
        const before = diagramBefore;
        void drawn.then(() => decorateDiagrams({ root, before }));
      }
      // 左右に並べた本文の図を描き、右の変えた図に色・凡例・Raw の差分を付ける
      if (side !== null) {
        const sideView = side;
        void renderDiagrams(sideView.root).then(() => sideView.decorate());
      }
      const onDiagramTool = (event: Event): void => {
        const button = (event.target as Element).closest<HTMLElement>("[data-act]");
        const figure = button?.closest<HTMLElement>(".diagram");
        if (button === null || button === undefined || figure === null || figure === undefined) return;
        const act = button.dataset["act"];
        const original = figure.querySelector(`[${DIAGRAM_SOURCE_ATTR}]`)?.getAttribute(DIAGRAM_SOURCE_ATTR) ?? "";
        if (act === "diagram-zoom") {
          const svgElement = figure.querySelector<SVGElement>(".mermaid svg");
          const beforeSource = figure.getAttribute(BEFORE_SOURCE_ATTR);
          if (svgElement !== null) on.diagram(svgElement, beforeSource === null ? null : { beforeSource });
        } else if (act === "diagram-raw") {
          // 図と mermaid の原文を切り替える
          const pressed = button.getAttribute("aria-pressed") !== "true";
          button.setAttribute("aria-pressed", String(pressed));
          figure.querySelector<HTMLElement>(".mermaid")!.hidden = pressed;
          figure.querySelector<HTMLElement>(".dg-raw")!.hidden = !pressed;
        } else if (act === "diagram-copy") {
          void navigator.clipboard?.writeText(original).then(() => {
            button.replaceChildren(icon("check"));
            window.setTimeout(() => button.replaceChildren(icon("copy")), 1400);
          });
        }
      };
      root.addEventListener("click", onDiagramTool);
      const content = document.createDocumentFragment();
      // 左右に並べるときは、本文の幅が足りないときに出すインラインの本文も持つ
      if (side !== null) {
        side.root.addEventListener("click", onDiagramTool);
        root.classList.add("sbs-fallback");
      }
      content.append(...(notice === null ? [] : [notice]), ...(layoutBar === null ? [] : [layoutBar]), ...(side === null ? [] : [side.root]), root);
      return section(label, content);
    };
    /** HTML の本文の節。本文を枠に描く。差分の表示の間は、描いた結果の上の印と原文の差分で前後を見せる */
    const htmlBodySection = ({ label, source }: { label: string; source: string }): HTMLElement => {
      const current = index.data.bodies[entry.item.body ?? ""];
      const marked = index.data.marked_bodies?.[entry.item.body ?? ""];
      // 選んだ時点が今の本文のとき、行の印つきの HTML を使う（古いまとまりを選び、その後に本文を直したときは、今の行と合わない）
      const lined = source === current && marked !== undefined;
      const drawn = lined ? marked : source;
      let notice: HTMLElement | null = null;
      let content: HTMLElement | null = null;
      const versions = view?.versions ?? null;
      if (versions !== null && versions.before !== null && !versions.trimmed) {
        if (missingLibraries(["jsdiff"]).length > 0) {
          notice = libraryNotice({ names: ["jsdiff"], what: "本文の差分" });
        } else if (versions.beforeBody === null) {
          notice = noteBox(NOTE_BODY_UNAVAILABLE);
        } else if (versions.beforeBody !== source) {
          content = htmlBodyDiff({
            before: versions.beforeBody,
            after: source,
            marked: drawn,
            beforeFormat: bodyFormatOf(versions.before.body) === "md" ? "md" : "html",
            layout: bodyLayout,
            layoutSwitch: bodyDiffLayoutSwitch({ layout: bodyLayout, on: { change: on.layout } }),
          });
          if (content === null) notice = noteBox(NOTE_BODY_TOO_LARGE);
        }
      }
      const frame =
        content ??
        htmlBodyFrame({
          source: drawn,
          // 配る書き出しと、今の本文の行と合わない本文では、選んだ箇所のコメントの入口を出さない
          selectable: review !== null && lined,
          ...(on.frame === undefined ? {} : { on: { select: on.frame.select, clear: on.frame.clear } }),
        });
      if (frame instanceof HTMLIFrameElement) frame.setAttribute(HTML_BODY_ATTR, "");
      const wrapped = document.createDocumentFragment();
      wrapped.append(...(notice === null ? [] : [notice]), frame);
      return section(label, wrapped);
    };
    /** 採用した案と理由の節（決定内容・理由のどちらかがあるときだけ） */
    const adoptedSection = (): HTMLElement | null => {
      const rows = [
        labelled({ label: "決定内容", key: "answer", value: item.answer, top: SECTION_TOP_HEADING_LEVEL }),
        labelled({ label: "理由", key: "reason", value: item.reason, top: SECTION_TOP_HEADING_LEVEL }),
      ].filter(
        (row) => row !== null,
      );
      if (rows.length === 0) return null;
      const content = document.createDocumentFragment();
      content.append(...rows);
      return section("採用した案と理由", content);
    };
    /** 関係する項目の節（1 件以上あるときだけ） */
    const relation = (label: string, ids: string[]): HTMLElement | null =>
      ids.length === 0 ? null : section(label, itemList(index, ids, on.open));
    /** タグなどの一覧の節。値が変わっていれば、前の値と今の値を並べる */
    const listSection = (label: string, key: string, values: readonly string[] | undefined): HTMLElement | null => {
      if (keys?.has(key) === true) return section(label, valueSpan(key, [keys.show(key)]));
      return (values ?? []).length > 0 ? section(label, tagList(values)) : null;
    };

    append({
      parent: body,
      children: [
        view === null ? null : diffHead(view.point),
        view?.versions?.trimmed === true ? noteBox(NOTE_TRIMMED) : null,
        valueSpan("status", [keys?.has("status") === true ? keys.show("status", statusOf, true) : statusBadge(item.status)]),
        h({
          tag: "h2",
          attrs: { class: "d-title", [VALUE_KEY_ATTR]: "title" },
          children: [
            keys?.has("title") === true ? keys.showWords("title") : item.title,
            item.deliverable === true ? deliverableBadge() : null,
            view?.kind === "new" ? diffMark({ kind: "new", labeled: true }) : null,
            // 取り下げた項目は、差分の表示によらず題の右に札を置く
            item.withdrawn === true ? withdrawnBadge({ large: true }) : null,
          ],
        }),
        metaList({ item, settings: index.data.settings, diff: keys }),
        withdrawnReason(),
      ],
    });
    if (kind === "decisions") {
      const previous = keys?.has("options") === true ? (keys.before.options ?? []) : null;
      append({
        parent: body,
        children: [
          lead("lead", item.lead, "d-lead"),
          (item.options ?? []).length > 0 || previous !== null ? section("案", optionCards({ options: item.options ?? [], previous, ...(keys === null ? {} : { pairs: keys.pairs }) })) : null,
          adoptedSection(),
          bodySection("本文"),
          relation("前提", related.prerequisites),
          relation("後続の項目", related.successors),
          relation("関連タスク", related.tasks),
          relation("経緯（会話ログ）", related.logs),
        ],
      });
    } else if (kind === "tasks") {
      append({
        parent: body,
        children: [
          labelled({ label: "理由", key: "reason", value: item.reason, top: TITLE_TOP_HEADING_LEVEL }),
          relation("進める検討事項", item.for ?? []),
          relation("前提", related.prerequisites),
          relation("結果", item.result === undefined ? [] : [item.result]),
          bodySection("本文"),
        ],
      });
    } else if (kind === "research") {
      append({
        parent: body,
        children: [
          lead("question", item.question, "d-lead"),
          descriptionSection(),
          labelled({ label: "結論", key: "conclusion", value: item.conclusion, top: TITLE_TOP_HEADING_LEVEL }),
          listSection("エイリアス", "aliases", item.aliases),
          listSection("調査の観点", "angles", item.angles),
          bodySection("本文"),
        ],
      });
    } else if (kind === "docs") {
      append({ parent: body, children: [descriptionSection(), listSection("エイリアス", "aliases", item.aliases), bodySection("本文")] });
    } else if (kind === "terms") {
      append({
        parent: body,
        children: [
          labelled({ label: "意味", key: "meaning", value: item.meaning, top: TITLE_TOP_HEADING_LEVEL }),
          listSection("別名", "aliases", item.aliases),
          listSection("使わない表記", "avoid", item.avoid),
          bodySection("本文"),
        ],
      });
    } else if (kind === "notes") {
      append({ parent: body, children: [lead("content", item.content, null), bodySection("本文")] });
    } else {
      append({ parent: body, children: [bodySection("要約")] });
    }
    if ((item.links ?? []).length > 0) {
      append({
        parent: body,
        children: [
          section(
            "リンク",
            h({
              tag: "ul",
              attrs: { class: "d-list" },
              children: [
                ...(item.links ?? []).map((link) =>
                  h({
                    tag: "li",
                    children: [
                      icon("link"),
                      h({
                        tag: "a",
                        attrs: { href: link.url, target: "_blank", rel: "noopener" },
                        children: [link.title],
                      }),
                    ],
                  }),
                ),
              ],
            }),
          ),
        ],
      });
    }
    append({
      parent: body,
      children: [
        relation(kind === "logs" ? "更新した項目" : "関連", related.related),
        relation("参照元", related.referencedBy),
        review === null ? null : reviewSection(review),
      ],
    });
    // 本文の差分を描かなかったとき、キーの値の語の面をここで付ける
    markKeys(performance.now() + LINE_DIFF_TIMEOUT_MS);
    return body;
  }

  /** 読む表示のキーの名前（メタの行の見出し）。キー → 見出しの文字 */
  function metaLabelOf({ key, settings }: { key: string; settings: Settings }): string | undefined {
    const labels: Record<string, string> = {
      target: settings.target_label,
      category: "カテゴリー",
      phase: "フェーズ",
      kind: "種類",
      confidence: "確度",
      date: "日付",
      withdrawn: "取り下げ",
      tags: "タグ",
    };
    return labels[key];
  }

  /** 読む表示のキー・案の名前の後ろに、保存待ちの印（印だけ）を置く。置き場所は、メタの行の見出し・値の名前（太字）・節の見出し・題・案の見出しの順で探す */
  function markEditedKeys({ root, marks, settings }: { root: HTMLElement; marks: Record<string, PendingMarkKind>; settings: Settings }): void {
    for (const [key, kind] of Object.entries(marks)) {
      // 項目の印は見出しに置く
      if (/^[A-Z]-\d+$/.test(key)) continue;
      const badge = pendingEditMark({ kind, compact: true });
      // 案の記号
      if (/^[A-Z]$/.test(key)) {
        const head = root.querySelector(`[${VALUE_KEY_ATTR}="options[${key}].content"]`)?.closest(".opt")?.querySelector(".o-head");
        if (head !== null && head !== undefined && head.querySelector(".pm") === null) head.append(badge);
        continue;
      }
      const label = metaLabelOf({ key, settings });
      const dt = label === undefined ? undefined : [...root.querySelectorAll("dt")].find((node) => node.textContent === label);
      const value = root.querySelector(`[${VALUE_KEY_ATTR}="${key}"]`);
      const named = value?.closest(".d-answer")?.querySelector(":scope > b") ?? null;
      const heading = [...root.querySelectorAll(".d-sec > h3")].find((node) => node.textContent?.startsWith(KEY_LABELS[key] ?? "\u0000") === true || (key === "body" && /^(本文|要約)/.test(node.textContent ?? "")));
      const target = dt ?? named ?? heading ?? (value?.matches(".d-title") === true ? value : null);
      if (target !== null && target !== undefined) target.append(badge);
      else if (value !== null && value !== undefined) value.after(badge);
    }
  }

  /** 見出し（前へ・次へ・全画面・閉じる）を作る */
  function detailHead({ id, index, full, on, edit = null }: DetailProps): HTMLElement {
    const entry = index.byId.get(id);
    const trail = history.state as Trail | null;
    const position = trail?.position ?? 0;
    const length = trail?.items.length ?? 1;
    // 本文が Markdown の資料は、編集の表示の間を除いて、エクスポートの入口を置く
    const exportSource =
      entry?.kind === "docs" && bodyFormatOf(entry.item.body) === "md" && edit?.editing !== true ? index.data.bodies[entry.item.body ?? ""] : undefined;
    const arrow = (label: string, glyph: string, disabled: boolean, handler: () => void): HTMLElement =>
      h({
        tag: "button",
        attrs: {
          class: "icon-btn",
          type: "button",
          "data-act": glyph === "←" ? "back" : "forward",
          "aria-label": label,
          title: label,
          disabled,
          onclick: handler,
        },
        children: [glyph],
      });
    return h({
      tag: "div",
      attrs: { class: "panel-head" },
      children: [
        full
          ? null
          : h({
            tag: "button",
            attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: on.close },
            children: [icon("back")],
          }),
        h({
          tag: "span",
          attrs: { class: "panel-kind" },
          children: [
            // 狭い幅でタイトルに幅を譲るとき、種類の名前だけを見た目から外せるよう包む
            entry === undefined ? "" : h({ tag: "span", attrs: { class: "panel-kind-label" }, children: [`${KIND_LABEL[entry.kind]} `] }),
            h({ tag: "span", attrs: { class: "mono" }, children: [id] }),
          ],
        }),
        entry?.kind === "docs" ? bodyFormatBadgeOf(entry.item.body) : null,
        // 保存待ちの編集がある項目は、種類と ID の右に印だけを置く（幅 480px 以下は出さず、キー・案の印に任せる）
        editMarkOf({ edit, id, compact: true }),
        // 本文の先頭のタイトルと二重に読ませないよう読み上げから外す。収まらない分は省略し、乗せると全文が読める
        entry === undefined
          ? null
          : h({
            tag: "span",
            attrs: { class: "panel-title", "aria-hidden": "true", title: entry.item.title },
            children: [entry.item.title],
          }),
        h({ tag: "span", attrs: { class: "spacer" } }),
        edit === null
          ? null
          : h({
              tag: "button",
              attrs: {
                class: "btn pe-edit-toggle",
                type: "button",
                "data-act": "edit",
                "aria-pressed": String(edit.editing),
                title: edit.editing ? "編集を終える" : "編集する",
                onclick: () => edit.onToggle(),
              },
              children: [icon("edit"), h({ tag: "span", attrs: { class: "lbl" }, children: [edit.editing ? "編集を終える" : "編集する"] })],
            }),
        exportSource === undefined || entry === undefined ? null : docExportControl({ item: entry.item, source: exportSource, index }),
        arrow("前の項目へ戻る", "←", position <= 0, on.back),
        arrow("次の項目へ進む", "→", position >= length - 1, on.forward),
        h({
          tag: "button",
          attrs: {
            class: "icon-btn panel-full",
            type: "button",
            "data-act": "full",
            // 全画面の間は、縮小のアイコンと元に戻す名前にする（色は変えず、押された状態は持たない）
            "aria-label": full ? "元の大きさに戻す" : "全画面表示",
            title: full ? "元の大きさに戻す" : "全画面表示",
            onclick: () => on.full(!full),
          },
          children: [icon(full ? "shrink" : "expand")],
        }),
        full
          ? null
          : h({
            tag: "button",
            attrs: {
              class: "icon-btn panel-close-x",
              type: "button",
              "data-act": "close",
              "aria-label": "詳細を閉じる",
              onclick: on.close,
            },
            children: [icon("x")],
          }),
      ],
    });
  }

  /** 資料のエクスポートの入口と、形式を選ぶメニュー。入口を押すとメニューを入口の下に右端を揃えて開き、「HTML でエクスポート」は mdmark を取って 1 枚の HTML を組み立てて保存させ、「Markdown でエクスポート」は警告の後に埋め込んだ HTML を除いた本文を保存させる。閉じたら入口へフォーカスを戻す */
  function docExportControl({ item, source, index }: { item: Item; source: string; index: RecordIndex }): HTMLElement {
    // 組み立てている間にメニューを閉じたとき、組み立て終えたファイルを保存させないための世代
    let generation = 0;
    let view: DocExportView = "choose";
    const entry = h({
      tag: "button",
      attrs: {
        class: "icon-btn panel-export",
        type: "button",
        "data-act": "export",
        "aria-label": "エクスポート",
        title: "エクスポート",
        "aria-haspopup": "dialog",
        "aria-expanded": "false",
      },
      children: [icon("download")],
    });
    /** メニューの中身を替える（開いたまま、中身とフォーカスだけを替える） */
    const setView = ({ next, focus }: { next: DocExportView; focus?: DocExportFormat }): void => {
      view = next;
      const fresh = docExportMenu({ view: next, ...(focus === undefined ? {} : { focus }), on });
      menu.replaceChildren(...fresh.childNodes);
      menu.setAttribute("aria-labelledby", fresh.getAttribute("aria-labelledby") ?? "");
      if (next === "busy") menu.setAttribute("aria-busy", "true");
      else menu.removeAttribute("aria-busy");
      menu.querySelector<HTMLElement>(`[${DOC_EXPORT_FOCUS_ATTR}]`)?.focus();
    };
    /** HTML のエクスポート。mdmark を取って組み立て、保存させて閉じる。取れないか組み立てられなければエラーの中身にする */
    const exportHtml = async (): Promise<void> => {
      setView({ next: "busy" });
      generation += 1;
      const mine = generation;
      const assets = await mdmarkAssets();
      // 組み立てている間に閉じた
      if (mine !== generation) return;
      if (!assets.ok) {
        setView({ next: "error" });
        return;
      }
      let html: string;
      try {
        html = buildDocHtml({ item, source, index, assets });
      } catch {
        // 1 枚に入れられない中身（script 要素を閉じるタグを含む JavaScript など）
        setView({ next: "error" });
        return;
      }
      downloadText({ name: `${item.id}.html`, text: html, type: "text/html" });
      menu.hidePopover();
    };
    const on: DocExportMenuProps["on"] = {
      format: (format) => {
        if (format === "html") void exportHtml();
        else setView({ next: "warn" });
      },
      confirm: () => {
        downloadText({ name: `${item.id}.md`, text: stripEmbeddedHtml(source), type: "text/markdown" });
        menu.hidePopover();
      },
      back: () => setView({ next: "choose", focus: view === "warn" ? "md" : "html" }),
      retry: () => void exportHtml(),
      close: () => {
        generation += 1;
        entry.setAttribute("aria-expanded", "false");
        entry.focus();
      },
    };
    const menu = docExportMenu({ on });
    // 入口の押下が開閉を決める。開くたびに形式を選ぶ中身へ戻し、入口の下に右端を揃えて置く
    entry.popoverTargetElement = menu;
    entry.popoverTargetAction = "toggle";
    menu.addEventListener("beforetoggle", (event) => {
      if ((event as ToggleEvent).newState !== "open") return;
      setView({ next: "choose" });
      entry.setAttribute("aria-expanded", "true");
      const rect = entry.getBoundingClientRect();
      menu.style.top = `${rect.bottom + 4}px`;
      menu.style.right = `${window.innerWidth - rect.right}px`;
      menu.style.left = "auto";
    });
    // 開いたら、最初の行にフォーカスを置く
    menu.addEventListener("toggle", (event) => {
      if ((event as ToggleEvent).newState === "open") menu.querySelector<HTMLElement>(`[${DOC_EXPORT_FOCUS_ATTR}]`)?.focus();
    });
    return h({ tag: "span", attrs: { class: "panel-export-host" }, children: [entry, menu] });
  }

  /** 本文の先頭のタイトルが本文のスクロール領域の上へ出ている間だけ、見出しのタイトルに `is-shown` を付ける */
  function bindHeadTitle({ head, body }: { head: HTMLElement; body: HTMLElement }): void {
    const headTitle = head.querySelector<HTMLElement>(".panel-title");
    const bodyTitle = body.querySelector<HTMLElement>(".d-title");
    if (headTitle === null || bodyTitle === null) return;
    const observer = new IntersectionObserver(
      (entries) => {
        // 描き直されて文書から外れた見出しの見張りは外す
        if (!head.isConnected) {
          observer.disconnect();
          return;
        }
        const last = entries[entries.length - 1];
        // 領域の上へ出たときだけ出す（下にあるときは出さない）
        headTitle.classList.toggle("is-shown", !last.isIntersecting && last.boundingClientRect.top < (last.rootBounds?.top ?? 0));
      },
      { root: body, threshold: 0 },
    );
    observer.observe(bodyTitle);
  }

  /** 節の見出し（h3）の次に置く、本文・値の見出しのうち最も上の段 */
  const SECTION_TOP_HEADING_LEVEL = 4;

  /** 題（h2）の次に置く、値の見出しのうち最も上の段 */
  const TITLE_TOP_HEADING_LEVEL = 3;

  /** 見出しの要素の最も下の段（h6） */
  const LOWEST_HEADING_LEVEL = 6;

  /** 見出しの要素の段（h1〜h6 の数字） */
  function headingLevel(heading: HTMLElement): number {
    return Number(heading.tagName.slice(1));
  }

  /** 見出しのうち最も上の段を top（省略すると節の見出しの次の段）にするための、全ての見出しに足す段の差。見出しが無ければ 0 */
  export function headingShift({ roots, top = SECTION_TOP_HEADING_LEVEL }: { roots: HTMLElement[]; top?: number }): number {
    const levels = roots.flatMap((root) => [...root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")].map(headingLevel));
    return levels.length === 0 ? 0 : top - Math.min(...levels);
  }

  /** 本文・値の見出しに渡された段の差を足して並べる（`headingShift` が求めた差なら h3〜h6 になる）。見た目は元の段のまま（`data-md-level`） */
  export function lowerHeadings({ root, shift }: { root: HTMLElement; shift: number }): void {
    for (const heading of root.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")) {
      const level = headingLevel(heading);
      const lowered = Math.min(level + shift, LOWEST_HEADING_LEVEL);
      const replacement = h({
        tag: `h${lowered}` as "h3" | "h4" | "h5" | "h6",
        attrs: {
          "data-md-level": level,
          // 元の Markdown の行の印を引き継ぐ
          [LINE_ATTR]: heading.getAttribute(LINE_ATTR),
          // h6 を超える段は、読み上げの段で伝える
          "aria-level": level + shift > LOWEST_HEADING_LEVEL ? level + shift : null,
        },
        children: [...heading.childNodes],
      });
      heading.replaceWith(replacement);
    }
  }

  /** 本文の見出しを、本文のスクロール領域の中で画面に入れる（見えている見出しが本文に無ければ false。左右に並べるときは同じ見出しが 3 か所にあるので、矩形を持つ最初のものへ送る） */
  function scrollToHeading({ root, slug }: { root: ParentNode; slug: string }): boolean {
    // 畳んだ節の中の見出しは、包む入れ物を開いてから送る
    revealHeading({ root, slug });
    const target = [...root.querySelectorAll(`[data-heading="${CSS.escape(slug)}"]`)].find(isRendered);
    if (target === undefined) return false;
    target.scrollIntoView({ block: "start" });
    return true;
  }

  /** 本文の印のツールチップを隠すまで待つミリ秒（印からツールチップへポインターを動かす間に消さない） */
  const TIP_HIDE_DELAY_MS = 150;

  /** ツールチップを隠す待ちのタイマー */
  let tipTimer = 0;

  /** 今出している（出していた）ツールチップの印と、押して残しているか */
  let tipState: { mark: HTMLElement; pinned: boolean } | null = null;

  /** Esc で閉じて印へフォーカスを戻すとき、その印のフォーカスでツールチップを出し直さない */
  let refocused: Element | null = null;

  /** 今のツールチップの要素（使い回す 1 つ。隠していても文書に残る） */
  function currentTip(): HTMLElement | null {
    return document.getElementById(TERM_TIP_ID);
  }

  /** 押して残しているか。ツールチップがまだ文書にあって開いているときに限る（詳細パネルの描き直しで外れたものは残していないとみなす） */
  function isPinned(): boolean {
    return tipState?.pinned === true && currentTip()?.matches(":popover-open") === true;
  }

  /** ツールチップを隠す（`now` が偽のときは、少し待ってから） */
  function hideTermTip(now: boolean): void {
    window.clearTimeout(tipTimer);
    const hide = (): void => {
      const tip = currentTip();
      if (tip?.matches(":popover-open") === true) tip.hidePopover();
      tipState = null;
    };
    if (now) hide();
    else tipTimer = window.setTimeout(hide, TIP_HIDE_DELAY_MS);
  }

  /** 印の上に、一致した項目のツールチップを出す。重ねる面の上にも出せるよう、印のある詳細パネル・全画面のモーダルの中に置く（モーダルの外は操作できない） */
  function showTermTip({
    mark,
    entries,
    pinned,
    onOpen,
  }: {
    mark: HTMLElement;
    entries: TermTipEntry[];
    pinned: boolean;
    onOpen: (id: string) => void;
  }): void {
    window.clearTimeout(tipTimer);
    const previous = currentTip();
    // 同じ印を同じ出し方で出しているときは出し直さない（中のスクロールを保つ）
    if (tipState?.mark === mark && tipState.pinned === pinned && previous?.matches(":popover-open") === true) return;
    if (previous !== null) {
      if (previous.matches(":popover-open")) previous.hidePopover();
      previous.remove();
    }
    const tip = termTip({
      entries,
      anchor: mark,
      pinned,
      on: {
        open: (id) => {
          hideTermTip(true);
          onOpen(id);
        },
        close: () => hideTermTip(true),
      },
    });
    // ツールチップに乗せている間は消さない。押して残した間は、外れても消さない
    tip.addEventListener("mouseenter", () => window.clearTimeout(tipTimer));
    tip.addEventListener("mouseleave", () => {
      if (!pinned) hideTermTip(false);
    });
    (mark.closest("dialog, aside") ?? document.body).append(tip);
    tip.showPopover();
    tipState = { mark, pinned };
  }

  /** Esc でツールチップを隠す。中にフォーカスがあれば印へ戻し、全画面の Esc（元の大きさに戻す）を起こさない */
  document.addEventListener(
    "keydown",
    (event) => {
      const tip = currentTip();
      // 詳細パネルが出したツールチップだけを対象にする
      if (event.key !== "Escape" || tipState === null || tip?.matches(":popover-open") !== true) return;
      const back = tip.contains(document.activeElement) ? tipState.mark : null;
      event.preventDefault();
      event.stopPropagation();
      hideTermTip(true);
      refocused = back;
      back?.focus();
      refocused = null;
    },
    true,
  );

  /** 本文の印に乗せる・フォーカスするとツールチップを出し、外れると隠す（本文の要素に委ねて付ける）。用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残し、Tab で中へ移れる */
  function attachTermTips({ root, index, onOpen }: { root: HTMLElement; index: RecordIndex; onOpen: (id: string) => void }): void {
    /** イベントの先の印と、一致した項目（用語 → 資料 → 調査の順）。用語 2 件以上か、資料・調査を含むか */
    const markOf = (event: Event): { mark: HTMLElement; entries: TermTipEntry[]; multi: boolean } | null => {
      const mark = (event.target as Element).closest?.<HTMLElement>("a.term") ?? null;
      if (mark === null) return null;
      const ids = (mark.getAttribute("data-ids") ?? mark.getAttribute("data-id") ?? "").split(" ");
      const entries = ids.flatMap((id) => {
        const found = index.byId.get(id);
        return found === undefined ? [] : [{ kind: found.kind as TermTipEntry["kind"], item: found.item }];
      });
      return entries.length === 0 ? null : { mark, entries, multi: entries.length > 1 || entries.some((entry) => entry.kind !== "terms") };
    };
    root.addEventListener("mouseover", (event) => {
      const found = markOf(event);
      // 押して残している間は、ほかの印に乗せても替えない
      if (found !== null && !isPinned()) showTermTip({ ...found, pinned: false, onOpen });
    });
    root.addEventListener("focusin", (event) => {
      const found = markOf(event);
      if (found !== null && found.mark !== refocused) showTermTip({ ...found, pinned: false, onOpen });
    });
    root.addEventListener("mouseout", (event) => {
      if (markOf(event) !== null && !isPinned()) hideTermTip(false);
    });
    root.addEventListener("focusout", (event) => {
      const to = (event as FocusEvent).relatedTarget;
      // ツールチップの中へ移るときは残す。押して残している間は、フォーカスの行き先が無い（余白を押した）ときも残す
      if (markOf(event) === null || (to instanceof Node && currentTip()?.contains(to) === true)) return;
      if (to === null && isPinned()) return;
      hideTermTip(true);
    });
    // 用語 2 件以上か、資料・調査にも一致した印から Tab で、ツールチップの中の最初のリンクへ移る
    root.addEventListener("keydown", (event) => {
      const found = markOf(event);
      const tip = currentTip();
      if (event.key !== "Tab" || event.shiftKey || found === null || !found.multi || tip?.matches(":popover-open") !== true) return;
      const first = tip.querySelector<HTMLElement>("a[href]");
      if (first === null) return;
      event.preventDefault();
      first.focus();
    });
    root.addEventListener("click", (event) => {
      const found = markOf(event);
      if (found === null) return;
      // 用語 2 件以上か、資料・調査にも一致した印は、押すとツールチップを残す（移る先は中のリンクで選ぶ）
      if (found.multi) {
        showTermTip({ ...found, pinned: true, onOpen });
        return;
      }
      // 用語 1 件だけに一致した印を押して項目へ移るときは、ツールチップを残さない
      hideTermTip(true);
    });
  }

  /** コメントの一覧から開いたとき、そのコメントの箇所に印の色の地を付け、描いた後にその箇所までスクロールする。合わなければ示さず、項目の先頭を出す */
  function applyHighlight({ root, loc }: { root: ParentNode; loc: Location }): void {
    let hits: Element[] = [];
    if (loc.kind === "value") {
      hits = [...root.querySelectorAll(`[${VALUE_KEY_ATTR}]`)].filter((element) => element.getAttribute(VALUE_KEY_ATTR) === loc.key);
    } else {
      const start = loc.start ?? 0;
      const end = loc.end ?? start;
      // HTML の本文: 枠の中で、始まりの行を含む最も内側の要素を示す
      const frame = root.querySelector<HTMLIFrameElement>(`iframe[${HTML_BODY_ATTR}]`);
      if (frame !== null) {
        highlightFrameLine({ frame, line: start, scroller: root.querySelector<HTMLElement>(".panel-body") });
        return;
      }
      const blocks = [...root.querySelectorAll(`.md [${LINE_ATTR}]`)];
      const lineOf = (element: Element): number => Number(element.getAttribute(LINE_ATTR));
      // 始まりの行を含む（始まりの行以前で最も後ろの）ブロックから、終わりの行までのブロック
      const first = blocks.filter((element) => lineOf(element) <= start).at(-1);
      if (first !== undefined) hits = blocks.filter((element) => lineOf(element) >= lineOf(first) && lineOf(element) <= end);
    }
    for (const element of hits) element.classList.add("loc-hit");
    // 文書に入れた後でないとスクロールできない
    const target = hits[0];
    if (target !== undefined) requestAnimationFrame(() => target.scrollIntoView({ block: "center" }));
  }

  /** 詳細パネルの幅の決まり（px）。既定の幅・ドラッグで変えられる下限・上限を決める残す幅（本文を寄せる幅は本文に、重ねる幅は左に）・矢印キー 1 回の刻み・幅を変えられる表示の幅の下限・本文を寄せる表示の幅の下限（`style.css` の境目と同じ値） */
  export const PANEL_WIDTH = { default: 640, min: 480, keepBody: 400, keepLeft: 160, step: 16, resizableFrom: 901, sideFrom: 1100 } as const;

  /** 表示の幅と、本文を寄せるかから、詳細パネルの幅の上限を返す */
  export function panelWidthMax({ viewport, mapView }: { viewport: number; mapView: boolean }): number {
    // 本文を寄せる幅（マップは幅を変えられる幅ならいつも寄せる）は本文に残す幅、重ねる幅は左に残す幅を、表示の幅から引く
    const aligned = viewport >= PANEL_WIDTH.sideFrom || (mapView && viewport >= PANEL_WIDTH.resizableFrom);
    return viewport - (aligned ? PANEL_WIDTH.keepBody : PANEL_WIDTH.keepLeft);
  }

  /** 詳細パネルの幅を下限以上・上限以下に収め、整数に丸めて返す */
  export function clampPanelWidth({ width, max }: { width: number; max: number }): number {
    return Math.round(Math.max(PANEL_WIDTH.min, Math.min(width, max)));
  }

  /** 詳細パネルの左端に置く幅の区切り。ドラッグと矢印キーで幅を変え、変えるたびに `onChange` で知らせる */
  export function panelResizer({ stored, mapView, onChange }: { stored: number | null; mapView: () => boolean; onChange: (width: number) => void }): HTMLElement {
    const separator = h({
      tag: "div",
      attrs: { class: "panel-resizer", role: "separator", tabindex: "0", "aria-orientation": "vertical", "aria-label": "詳細パネルの幅", "aria-valuemin": PANEL_WIDTH.min },
    });
    // 持っている幅。上限を超える残した幅は、窓を広げ直したときに戻せるよう収めずに持つ（幅を変えたら、収めた幅にそろえる）
    let wanted = stored ?? PANEL_WIDTH.default;
    // 画面へ当てている幅
    let shown = wanted;
    const maxWidth = (): number => panelWidthMax({ viewport: innerWidth, mapView: mapView() });
    /** 持っている幅を今の上限に収めて画面へ当てる（詳細パネルの幅と本文の寄せは `--panel-w` を読む）。当てた幅を返す */
    const apply = (): number => {
      const max = maxWidth();
      shown = clampPanelWidth({ width: wanted, max });
      document.documentElement.style.setProperty("--panel-w", `${shown}px`);
      separator.setAttribute("aria-valuemax", String(max));
      separator.setAttribute("aria-valuenow", String(shown));
      // 下限・上限で止まっている間は、広げる・狭める片方だけのカーソルにする
      separator.dataset.edge = shown <= PANEL_WIDTH.min ? "min" : shown >= max ? "max" : "";
      return shown;
    };
    /** 幅を変えて画面へ当て、当てた幅を知らせる */
    const change = (width: number): void => {
      wanted = width;
      wanted = apply();
      onChange(wanted);
    };
    apply();
    // 窓の幅が変わったら、持っている幅を新しい上限で当て直す。文書から外れた区切りの分は受け取らない
    const onResize = (): void => {
      if (!separator.isConnected) {
        removeEventListener("resize", onResize);
        return;
      }
      apply();
    };
    addEventListener("resize", onResize);
    separator.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      // 本文の文字を選ばず、区切りの外へポインターが出ても動きを受け取り続ける
      event.preventDefault();
      separator.focus({ preventScroll: true });
      separator.setPointerCapture(event.pointerId);
      const startX = event.clientX;
      const startWidth = apply();
      document.body.classList.add("is-panel-resizing");
      // 左端をつかんでいるので、左へ動かすほど広がる
      const move = (moved: PointerEvent): void => change(startWidth + startX - moved.clientX);
      // 離した・中断した・区切りが外れたときは、ポインターの捕捉が外れる
      const end = (): void => {
        separator.removeEventListener("pointermove", move);
        separator.removeEventListener("lostpointercapture", end);
        document.body.classList.remove("is-panel-resizing");
      };
      separator.addEventListener("pointermove", move);
      separator.addEventListener("lostpointercapture", end);
    });
    separator.addEventListener("keydown", (event) => {
      // ←: 広げる / →: 狭める / Home: 下限 / End: 上限
      const targets: Record<string, number> = { ArrowLeft: shown + PANEL_WIDTH.step, ArrowRight: shown - PANEL_WIDTH.step, Home: PANEL_WIDTH.min, End: maxWidth() };
      if (!Object.hasOwn(targets, event.key)) return;
      event.preventDefault();
      change(targets[event.key] ?? shown);
    });
    return separator;
  }

  /** 詳細パネル（全画面のときは中央のモーダル）を返す。文書に入れた後、全画面は `showModal()` で開く */
  export function detailPanel(props: DetailProps): HTMLElement {
    const { id, index, full, on, comment, highlight = null, diff = null, heading = null, minimap = true, bodyLayout = "inline", bodyView = BODY_VIEW_DEFAULT, edit = null, resizer = null } = props;
    const editing = edit?.editing === true;
    // 編集の表示の間は、読む表示の代わりに編集の入力を並べる
    const content = editing && edit !== null ? detailEditForm(edit.form) : detailBody({ id, index, on, review: comment === null ? null : { items: comment.reviews, edit: comment.edit }, view: resolveDiffView({ id, index, diff }), bodyLayout, bodyView });
    if (!editing && edit !== null) markEditedKeys({ root: content, marks: edit.marks, settings: index.data.settings });
    // 中にフォーカスできる要素が無い項目でも、キーボードで送れるように領域ごとフォーカスできるようにする
    const body = h({
      tag: "div",
      attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "詳細の本文" },
      children: [content],
    });
    // 本文を縦に送っても、見出しを固定した表の見出しの行を領域の上端に残す
    bindTableHeads(body);
    const head = detailHead(props);
    bindHeadTitle({ head, body });
    // 見出しと下端の入力の間の本文だけをスクロールする。差分の表示の間で、表示の設定で外していなければ、本文の右にミニマップを並べる。編集の表示の間は下端のコメントの入力を隠す
    const footer = comment === null || editing ? null : sendForm(comment.form);
    const scroller = diffMinimapFrame({ body, shown: diff !== null && minimap });
    let root: HTMLElement;
    if (!full) {
      root = h({
        tag: "aside",
        attrs: { class: `panel${editing ? " pe-editing" : ""}`, "aria-label": "詳細" },
        children: [resizer, head, scroller, footer],
      });
    } else {
      const dialog = h({ tag: "dialog", attrs: { class: `full${editing ? " pe-editing" : ""}`, "aria-label": "詳細の全画面" }, children: [head, scroller, footer] });
      // Esc は閉じずに元の大きさ（詳細パネル）に戻す。外側（後ろの幕）を押したときも同じ
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        on.full(false);
      });
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) on.full(false);
      });
      root = dialog;
    }
    if (highlight !== null) applyHighlight({ root, loc: highlight });
    attachTermTips({ root: body, index, onOpen: on.open });
    // 見出しを指して開いた: 描いた後にその見出しを本文の領域の中で画面に入れる（本文に無ければ、本文の頭で開き、ハッシュから外させる）
    if (heading !== null) {
      requestAnimationFrame(() => {
        if (!scrollToHeading({ root: body, slug: heading })) on.heading(null);
      });
    }
    return root;
  }
}
