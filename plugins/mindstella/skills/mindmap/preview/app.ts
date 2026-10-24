// 起動。記録を読み（配る書き出しは埋め込みから、サーバーの配信は記録の取得から）、URL のハッシュが指す画面を描き、操作を画面の移動・書き換えの知らせ・コメントの読み書き・端末の保存領域につなぐ。

namespace MindmapPreview {
  /** 埋め込みのデータの要素の ID */
  const DATA_ELEMENT_ID = "mindmap-data";

  /** 端末の保存領域のキー */
  export const PREFS_KEY = "mindmap-preview";

  /** 入力が止まってから書きかけを保つまでの待ち（ミリ秒）。打つたびに書かず、打ち終えた直後に閉じても失うのがこの待ちの分だけで済む長さ */
  export const DRAFT_SAVE_DELAY_MS = 500;

  /** 画面の下に「ワークスペースの既定が変わりました。」を出しておくミリ秒 */
  export const NOTICE_MS = 6000;

  /** 画面の下に「{n} 件を保存しました。」を出しておくミリ秒 */
  export const SAVED_NOTICE_MS = 5000;

  /** そのタブの「前回開いてから」の始まり（`OpenedPoint` の JSON）を残す sessionStorage のキー。あれば `POST /api/opened` を呼ばない（同じタブで読み込み直しても範囲を変えない） */
  export const SINCE_KEY = "mindmap-since";

  /** そのタブで変えた詳細パネルの幅（px の整数の文字列）を残す sessionStorage のキー。種類で分けない。配る書き出しでも同じ */
  export const PANEL_WIDTH_KEY = "mindmap-panel-width";

  /** 入力欄 1 つ（向けた先ごと）の書きかけと溜める状態（開いている間だけ持つ。書きかけの本文はサーバーにも残す） */
  export type FormState = {
    target: string | null;
    loc: Location | null;
    /** 返信先のスレッドの ID（スレッドの返信の入力欄のとき。持つときは `target`・`loc` を持たない） */
    thread: string | null;
    /** 入力欄の書きかけ */
    body: string;
    status: SendStatus;
    /** 溜めた後のレビュー中の件数 */
    count: number | null;
    /** サーバーが返した溜められなかった理由 */
    detail: string | null;
  };

  /** コメントの画面の状態（開いている間だけ持つ。描き直し・項目の移動・詳細パネルと全画面の行き来でも保つ） */
  export type CommentState = {
    /** 最後に読んだレビュー中のコメントと書きかけ */
    review: ReviewState;
    /** 入力欄ごと（`formKey`）の書きかけと溜める状態 */
    forms: Map<string, FormState>;
    /** 項目の ID → 選んだ箇所の入口を押して入力に添えた箇所 */
    pendingLoc: Map<string, Location>;
    /** コメントの一覧でチェックしたコメントの ID */
    checked: Set<string>;
    /** 一覧を開いている間に消したコメント */
    removed: ReviewState["items"];
    /** 箇所が合わないコメントの ID → 理由 */
    stale: Map<string, string>;
    /** コメントの一覧を開いているか */
    listOpen: boolean;
    /** 一覧の行から開いたコメントの ID */
    opened: string | null;
    /** スレッドの向けた項目を開いたとき、その項目の中で示す箇所 */
    highlight: { target: string; loc: Location } | null;
    /** 最後に読めたスレッド（読めなかったときは前のまま残す） */
    threads: Thread[];
    /** 直前のスレッドの読み取りが断られた・届かなかったときの理由。読めたら null */
    threadsError: { detail: string | null } | null;
    /** パネルの中に出している画面。パネルを開くたびに `list` に戻す */
    view: PanelView;
    /** レビュー中の書き込みを開く前の画面（「戻る」の戻り先） */
    reviewFrom: "list" | "thread";
    /** スレッドの状態の絞り込み。ページを開いたときは `open` で、パネルを閉じても保つ */
    filter: ThreadFilter;
    /** スレッドを絞っているタグ。パネルを閉じても保つ */
    tag: string | null;
    /** 開いているスレッド（`pending` が真なら `id` はまだ送っていない新しいスレッドのコメントの ID） */
    openedThread: OpenedThread | null;
    /** 新しいスレッドの入力を出しているか */
    composing: boolean;
    /** 開いているスレッドの理由の入力の状態。スレッドを開く・一覧へ戻るときに閉じて空にする */
    reason: ReasonState;
    /** スレッドの画面からレビュー中の書き込みを開いたときの、そのスレッドの ID */
    reviewFocus: string | null;
    /** レビュー中の書き込みの画面で本文を開いている書き込みの ID（`on.fold` で足し引きする。描き直しと本文の書き換えでは保ち、パネルを閉じると空にする） */
    expanded: Set<string>;
  };

  /** 表示の設定の画面の状態（開いている間だけ持つ。描き直し・書き換えの知らせでも保つ） */
  export type DisplayState = {
    /** 表示の設定のパネルを開いているか（コメントの一覧を開いているときは偽） */
    open: boolean;
    /** 既定の保存の確かめを開いている間の状態。閉じていれば null */
    confirm: { busy: boolean; error: string | null } | null;
    /** パネルに残す最後の知らせ（既定にした・既定が変わった。時刻つき） */
    message: SettingsMessage | null;
    /** 自分が既定にした直後の値。次に読んだ記録の `settings.display` がこれと等しければ、画面の下の知らせを出さずに null に戻す */
    savedDisplay: DisplayDefaults | null;
    /** 端末の保存領域に書けたか（`savePrefs` の結果） */
    storageOk: boolean;
  };

  /** 編集と保存待ちの状態（開いている間だけ持つ。保存待ちの編集はサーバーが持ち、ここには読んだ写しを置く。描き直し・書き換えの知らせでも保つ） */
  export type EditState = {
    /** 最後に読んだ保存待ちの編集 */
    edits: PendingEdit[];
    /** 直前の保存で書き込めなかった編集（その編集を取り消すか、次に保存できたら外す） */
    blocked: BlockedEdit[];
    /** 保存待ちのパネルを開いているか（コメントの一覧・表示の設定・絞り込みのドロワーとは 1 つだけが真） */
    open: boolean;
    /** 詳細パネルで編集の表示にしている項目の ID（足す項目は仮の ID。別の項目を開くと null） */
    editing: string | null;
    /** 仮の ID をまだ振られていない、開いたばかりの項目を追加する入力の種類 */
    adding: Kind | null;
    /** まとめて保存の状態（`offline` は直前の保存が届かなかった） */
    status: SaveStatus;
    /** `{target}:{key}` → 溜められなかった理由（届かない・断られた） */
    errors: Map<string, string>;
    /** 保存した知らせの文言（「{n} 件を保存しました。」。`SAVED_NOTICE_MS` で消す） */
    toast: string | null;
    /** 設定の画面を開いているか */
    workspaceOpen: boolean;
  };

  /** 入力欄のキー。向けた先（`target` と `loc` の組か、`thread`）を 1 つの文字列にする */
  export function formKey(target: string | null, loc: Location | null, thread: string | null = null): string {
    return JSON.stringify([target, loc?.kind ?? null, loc?.start ?? null, loc?.end ?? null, loc?.key ?? null, loc?.text ?? null, thread]);
  }

  /** 絞り込みの状態（開いている間の状態。表示形式の切り替え・描き直し・書き換えの知らせでも保つ。サーバーの配信では、条件を変えるたびに `Prefs.filters` へ写して端末に残す） */
  export type FilterState = {
    /** 画面（記録の表は種類）ごとの絞り込み。初めて開いた画面は `initialFilters` で入れる（サーバーの配信では `Prefs.filters` の分を `pruneFilters` にかけて渡す） */
    byTab: Record<string, Filters>;
    /** 絞り込みのドロワーを開いているか。コメントの一覧（`CommentState.listOpen`）と同時に真にしない */
    drawerOpen: boolean;
  };

  /** ロックの状態（ページを開いている間だけ持つ、画面ごとのロックした項目。タブの行き来・描き直し・書き換えの知らせでも保ち、URL のハッシュにも端末の保存領域にも書かない。絞り込みで描かれなくなっても外さず、画面と `lockTap` へは描いている間だけ渡す） */
  export type LockState = {
    /** ネットワークでロックしている項目 */
    graph: string | null;
    /** 検討事項のマップでロックしている検討事項 */
    map: string | null;
  };

  /** 重なりの状態（幅 900px 以下で詳細パネルと左のパネルを両方開いているときに前に出す側。ページを開いている間だけ持ち、URL のハッシュにも端末の保存領域にも書かない） */
  export type StackState = {
    /** 後から開いた側。左のパネルをトップバーから開いたら `left`、詳細パネルを開く・別の項目へ移ったら `detail` */
    front: "left" | "detail";
  };

  /** 端末に残す設定 */
  export type Prefs = {
    /** ライト / ダーク。null は OS の設定に従う */
    theme: Theme | null;
    /** 種類ごとの表示する列とピン留め。種類のキーが無ければ既定の列 */
    columns: Record<string, TablePrefs>;
    /** ネットワークの見た目。null はワークスペースの既定 */
    look: NetworkLook | null;
    /** 表示する種類。null はワークスペースの既定 */
    kinds: Kind[] | null;
    /** 変更履歴で選んだ時点（`since`・`pending`・まとまりの ID）。null は差分を出さない。個人の上書きではなく、「既定に戻す」でも消さない */
    diffSel: string | null;
    /** サーバーの配信で残した、画面（記録の表は種類）ごとの絞り込みの条件（`FilterState.byTab` と同じ形）。画面のキーが無ければ画面の既定の条件で開く。配る書き出しでは読まず書かない */
    filters: Record<string, Filters>;
    /** 差分のミニマップを表示しない上書き。null は表示する（ワークスペースの既定は持たない） */
    minimap: false | null;
    /** 本文の差分を左右に並べる上書き。null はインライン（ワークスペースの既定は持たない） */
    bodyLayout: "side" | null;
    /** 表の列の固定をオフにする上書き。null はオン（ワークスペースの既定は持たない） */
    tablePin: false | null;
    /** 表の見出しの固定をオフにする上書き。null はオン */
    tableHead: false | null;
    /** 表のしま模様をオンにする上書き。null はオフ */
    tableStripes: true | null;
    /** セクションの折りたたみをオフにする上書き。null はオン */
    sectionFold: false | null;
    /** 配る書き出しだけが持つ、前回開いた時点（`OpenedPoint`）。`isOpenedPoint` で確かめてから読み、通し番号を持たない前の版の値（日時の文字列）は無いものとして扱う */
    opened?: unknown;
  };

  /** 狭い幅（詳細パネルを別画面として積む幅） */
  const NARROW_QUERY = "(max-width: 900px)";

  /** タブのアイコン */
  const TAB_ICON: Record<Exclude<Tab, "graph">, IconName> = {
    overview: "home",
    decisions: "decision",
    tasks: "task",
    research: "research",
    docs: "doc",
    terms: "term",
    notes: "note",
    logs: "log",
  };

  /** タブの名前（種類の名前は読み込み順によらないよう、呼ばれたときに引く） */
  function tabLabel(key: Exclude<Tab, "graph">): string {
    return key === "overview" ? "概要" : KIND_LABEL[key];
  }

  /** 画面の名前（ネットワークは種類のタブに無いので、ここで持つ） */
  function screenName(tab: Tab): string {
    return tab === "graph" ? "ネットワーク" : tabLabel(tab);
  }

  /** `mindmap-data` の要素の中身を `JSON.parse` して返す。中身が空なら（サーバーの配信）null */
  export function readEmbeddedData(doc: Document): MindmapData | null {
    const text = doc.getElementById(DATA_ELEMENT_ID)?.textContent;
    // 要素が無い（同梱の雛形か書き出しの誤り）
    if (text === undefined || text === null) throw new Error("記録を読み込めませんでした。");
    // 中身が空: サーバーの配信なので、記録は取得で読む
    if (text.trim() === "") return null;
    try {
      return JSON.parse(text) as MindmapData;
    } catch {
      throw new Error("記録を読み込めませんでした。");
    }
  }

  /** 既定の設定 */
  function defaultPrefs(): Prefs {
    return {
      theme: null,
      columns: {},
      look: null,
      kinds: null,
      diffSel: null,
      filters: {},
      minimap: null,
      bodyLayout: null,
      tablePin: null,
      tableHead: null,
      tableStripes: null,
      sectionFold: null,
    };
  }

  /** 端末の保存領域から設定を読む。読めないときは既定を返す */
  export function loadPrefs(storage: Storage): Prefs {
    try {
      const saved = storage.getItem(PREFS_KEY);
      if (saved === null) return defaultPrefs();
      const parsed = { ...defaultPrefs(), ...(JSON.parse(saved) as Partial<Prefs>) };
      // 選べない値の見た目・種類は、その項目だけワークスペースの既定に従う
      const looks: readonly unknown[] = NETWORK_LOOKS.map((option) => option.key);
      if (!looks.includes(parsed.look)) parsed.look = null;
      const kinds: readonly unknown[] = KIND_KEYS;
      if (!Array.isArray(parsed.kinds) || !parsed.kinds.every((kind) => kinds.includes(kind))) parsed.kinds = null;
      // 画面ごとの条件が値の配列の対応でないときは、残した条件を使わない
      if (!isFiltersByTab(parsed.filters)) parsed.filters = {};
      // 差分のミニマップの上書きは false だけを読む（表示するは上書きを持たない）
      if (parsed.minimap !== false) parsed.minimap = null;
      // 本文の差分の並べ方の上書きは side だけを読む（インラインは上書きを持たない）
      if (parsed.bodyLayout !== "side") parsed.bodyLayout = null;
      // 本文の表とセクションの見せ方の上書きは、既定と違う値だけを読む
      if (parsed.tablePin !== false) parsed.tablePin = null;
      if (parsed.tableHead !== false) parsed.tableHead = null;
      if (parsed.tableStripes !== true) parsed.tableStripes = null;
      if (parsed.sectionFold !== false) parsed.sectionFold = null;
      return parsed;
    } catch {
      return defaultPrefs();
    }
  }

  /** 画面ごとの絞り込みの条件として読めるか（画面のキーごとに、条件のキー → 文字の配列の対応） */
  function isFiltersByTab(value: unknown): value is Record<string, Filters> {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
    return Object.values(value).every(
      (filters: unknown) =>
        typeof filters === "object" &&
        filters !== null &&
        !Array.isArray(filters) &&
        Object.values(filters).every((values: unknown) => Array.isArray(values) && values.every((v) => typeof v === "string")),
    );
  }

  /** 絞り込みの条件が同じか（値の並びと、値の無い条件は区別しない） */
  function sameFilters(a: Filters, b: Filters): boolean {
    const normal = (filters: Filters): string =>
      JSON.stringify(
        Object.entries(filters)
          .filter(([, values]) => values.length > 0)
          .map(([key, values]): [string, string[]] => [key, [...values].sort()])
          .sort(([x], [y]) => (x < y ? -1 : x > y ? 1 : 0)),
      );
    return normal(a) === normal(b);
  }

  /** 絞り込みの条件を端末に残す画面（種類のタブとネットワーク。概要は絞り込みを持たない。読み込み順によらないよう、呼ばれたときに作る） */
  function filterTabs(): Tab[] {
    return [...KIND_KEYS, "graph"];
  }

  /** 設定を端末の保存領域に残し、書けたかを返す。保存領域が例外を送るときは偽を返す（開いている間だけ設定を保つ） */
  export function savePrefs({ storage, prefs }: { storage: Storage; prefs: Prefs }): boolean {
    try {
      storage.setItem(PREFS_KEY, JSON.stringify(prefs));
      return true;
    } catch {
      return false;
    }
  }

  /** 項目ごとに、個人の上書きがあればそれを、無ければワークスペースの既定を、それも無ければ組み込みの既定を使う */
  export function resolveDisplay(
    prefs: Prefs,
    display: DisplayDefaults | undefined,
  ): {
    look: NetworkLook;
    kinds: Set<Kind>;
    defaultLook: NetworkLook;
    defaultKinds: Set<Kind>;
    overrides: string[];
    minimap: boolean;
    bodyLayout: BodyLayout;
    bodyView: BodyView;
  } {
    const defaultLook = display?.network_look ?? BUILTIN_LOOK;
    const defaultKinds = new Set<Kind>(display?.visible_kinds ?? KIND_KEYS);
    // 上書きを持つ項目の名前を、見た目・種類・ライト / ダーク・表の列・絞り込み・差分のミニマップ・本文の表とセクションの見せ方・本文の差分の並べ方の順に並べる（条件が画面の既定と同じ画面は並べない）
    const overrides = [
      ...(prefs.look === null ? [] : ["ネットワークの見た目"]),
      ...(prefs.kinds === null ? [] : ["表示する種類"]),
      ...(prefs.theme === null ? [] : ["ライト / ダーク"]),
      ...KIND_KEYS.filter((kind) => prefs.columns[kind] !== undefined).map((kind) => `表の列（${KIND_LABEL[kind]}）`),
      ...filterTabs().filter(
        (tab) => prefs.filters[tab] !== undefined && !sameFilters(prefs.filters[tab], initialFilters(tab, {}, null)),
      ).map((tab) => `絞り込み（${screenName(tab)}）`),
      ...(prefs.minimap === false ? [MINIMAP_LABEL] : []),
      ...(prefs.tablePin === false ? [BODY_VIEW_LABELS.pin] : []),
      ...(prefs.tableHead === false ? [BODY_VIEW_LABELS.head] : []),
      ...(prefs.tableStripes === true ? [BODY_VIEW_LABELS.stripes] : []),
      ...(prefs.sectionFold === false ? [BODY_VIEW_LABELS.fold] : []),
      ...(prefs.bodyLayout === "side" ? [BODY_LAYOUT_LABEL] : []),
    ];
    return {
      look: prefs.look ?? defaultLook,
      kinds: prefs.kinds === null ? defaultKinds : new Set(prefs.kinds),
      defaultLook,
      defaultKinds,
      overrides,
      // 上書きが false のときだけ表示しない
      minimap: prefs.minimap !== false,
      // 上書きが side のときだけ左右に並べる
      bodyLayout: prefs.bodyLayout === "side" ? "side" : "inline",
      // 上書きのある項目だけ既定と逆にする
      bodyView: {
        pin: prefs.tablePin !== false,
        head: prefs.tableHead !== false,
        stripes: prefs.tableStripes === true,
        fold: prefs.sectionFold !== false,
      },
    };
  }

  /** 「既定に戻す」で、見た目・表示する種類・ライト / ダーク・表の列・絞り込みの条件・差分のミニマップ・本文の表とセクションの見せ方・本文の差分の並べ方を外した設定を返す（`diffSel` は残し、渡した設定は変えない） */
  export function clearOverrides(prefs: Prefs): Prefs {
    return {
      ...prefs,
      theme: null,
      look: null,
      kinds: null,
      columns: {},
      filters: {},
      minimap: null,
      bodyLayout: null,
      tablePin: null,
      tableHead: null,
      tableStripes: null,
      sectionFold: null,
    };
  }

  /** 本文の見せ方の項目 → 個人の上書きの項目 */
  const BODY_VIEW_PREF = { pin: "tablePin", head: "tableHead", stripes: "tableStripes", fold: "sectionFold" } as const;

  /** 表示の既定が同じか（無いキーは同じ無しとして比べる） */
  function sameDisplay(a: DisplayDefaults | null | undefined, b: DisplayDefaults | null | undefined): boolean {
    const key = (display: DisplayDefaults | null | undefined): string =>
      JSON.stringify([display?.network_look ?? null, display?.visible_kinds ?? null]);
    return key(a) === key(b);
  }

  /** 端末の保存領域（開けない環境では、何も返さない保存領域） */
  function openStorage(kind: "localStorage" | "sessionStorage"): Storage {
    try {
      return window[kind];
    } catch {
      return {
        length: 0,
        clear: () => undefined,
        getItem: () => null,
        key: () => null,
        removeItem: () => undefined,
        // 残せない旨を呼び手に伝える（`savePrefs` が偽を返す）
        setItem: () => {
          throw new Error("保存領域が使えません");
        },
      };
    }
  }

  /** そのタブで変えた詳細パネルの幅を読む。正の整数でなければ、残っていないものとして扱う（既定の幅で開く） */
  export function readPanelWidth(session: Storage): number | null {
    let saved: string | null;
    try {
      saved = session.getItem(PANEL_WIDTH_KEY);
    } catch {
      return null;
    }
    return saved !== null && /^[1-9]\d*$/.test(saved) ? Number(saved) : null;
  }

  /** 変えた詳細パネルの幅をそのタブに残す。書けない保存領域では何もしない（開き直すと既定の幅で開く） */
  export function writePanelWidth({ session, width }: { session: Storage; width: number }): void {
    try {
      session.setItem(PANEL_WIDTH_KEY, String(width));
    } catch {
      return;
    }
  }

  /** そのタブの「前回開いてから」の始まりを決める。同じタブで読み込み直したときは、残した始まりをそのまま使う */
  export async function resolveSince({
    serverMode,
    prefs,
    persist,
    headSeq,
    session = openStorage("sessionStorage"),
    post = postOpened,
    now = () => new Date().toISOString(),
  }: {
    serverMode: boolean;
    prefs: Prefs;
    persist: () => void;
    /** 読んだ記録の先頭のまとまりの `until_seq`（まとまりが無ければ 0） */
    headSeq: number;
    session?: Storage;
    post?: () => Promise<OpenedReply | null>;
    now?: () => string;
  }): Promise<OpenedPoint> {
    // 同じタブに残した始まりがあれば使う（読めない・前の版の日時の文字列は残っていないものとして続ける）
    try {
      const kept: unknown = JSON.parse(session.getItem(SINCE_KEY) ?? "null");
      if (isOpenedPoint(kept)) return kept;
    } catch {
      // 読めない保存領域・JSON でない値: 決め直す
    }
    // タブを開いた時点
    let opened: OpenedPoint = { at: now(), seq: headSeq };
    let previous: OpenedPoint | null;
    if (serverMode) {
      // サーバーの配信は、ワークスペースに残る前回の時点を引き、今の時点に書き換えてもらう
      const reply = await post();
      previous = reply?.previous ?? null;
      opened = reply?.opened ?? opened;
    } else {
      // 配る書き出しは、前回の時点を端末の設定に持ち、今の時点に書き換える
      previous = isOpenedPoint(prefs.opened) ? prefs.opened : null;
      prefs.opened = opened;
      persist();
    }
    // 前回の時点が無い・通し番号が今の記録より先（ワークスペースを戻した・作り直した）ときは、今の時点からにする
    const since = previous !== null && previous.seq <= headSeq ? previous : opened;
    try {
      session.setItem(SINCE_KEY, JSON.stringify(since));
    } catch {
      // 残せない環境では、読み込み直すたびに決め直す
    }
    return since;
  }

  /** 変更履歴のモーダルに、差分を出さない行と、まだまとめていない変更・前回開いてから・まとまりの行を新しい順に並べる */
  function historyPoints({ changes, since }: { changes: Changes; since: OpenedPoint }): HistoryPoint[] {
    /** その時点で足した・変えた・消した項目の数（合わせた範囲で足して消した項目は、消した項目として 1 件に数える） */
    const countOf = (sel: string): number => {
      const point = resolveDiffPoint(changes, sel, since);
      return point === null ? 0 : point.added.size + point.changed.size + point.removed.size;
    };
    const hasPending =
      changes.pending.added.length + changes.pending.changed.length + (changes.pending.removed ?? []).length > 0;
    return [
      { sel: "", name: "差分を出さない（今の内容）", sub: "印と差分を出さずに今の内容だけを読む" },
      ...(hasPending
        ? [{ sel: "pending", name: "まだまとめていない変更", sub: "AI がまだ区切っていない書き換え", count: countOf("pending") }]
        : []),
      { sel: "since", name: "前回開いてから", sub: `${formatJst(since.at)} より後`, count: countOf("since") },
      ...changes.sets.map((set) => ({ sel: set.id, name: set.summary, sub: formatJst(set.at), count: countOf(set.id) })),
    ];
  }

  /** 選んだ時点の、項目の ID → 差分の印 */
  function marksOf(point: DiffPoint | null): DiffMarks | undefined {
    if (point === null) return undefined;
    return Object.fromEntries([
      ...[...point.added].map((id) => [id, "new" as const]),
      ...[...point.changed].map((id) => [id, "changed" as const]),
    ]);
  }

  /** レビュー中のコメントを `target` ごとに数え、項目の ID → 件数を返す（箇所を指すコメントもその項目に数え、項目を指さないコメントと件数 0 の項目は含めない） */
  export function commentCounts(items: ReviewState["items"]): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const item of items) {
      if (item.target === null) continue;
      counts[item.target] = (counts[item.target] ?? 0) + 1;
    }
    return counts;
  }

  /** 2 つの件数の対応が同じか */
  function sameCounts(a: Record<string, number>, b: Record<string, number>): boolean {
    const keys = Object.keys(a);
    return keys.length === Object.keys(b).length && keys.every((key) => a[key] === b[key]);
  }

  /** 記録を読み、ハッシュが指す画面を描き、操作と履歴をつなぐ */
  export function start(): void {
    let embedded: MindmapData | null;
    try {
      embedded = readEmbeddedData(document);
    } catch (error) {
      document.body.prepend(h({ tag: "p", attrs: { class: "md-error" }, children: [(error as Error).message] }));
      return;
    }
    void run(embedded);
  }

  /** サーバーが記録を読めるまで待つ。読めない間は、接続の状態と理由だけを出し、書き換えの知らせか接続が戻ったときに読み直す */
  function waitForRecords(theme: Theme): Promise<MindmapData> {
    const holder = h({ tag: "div", attrs: { id: "unavailable" } });
    document.body.prepend(holder);
    return new Promise((resolve) => {
      const attempt = async (): Promise<void> => {
        const result = await fetchRecords();
        if (result.ok) {
          stop();
          holder.remove();
          resolve(result.data);
          return;
        }
        const message =
          result.reason === "invalid" && result.detail !== null
            ? result.detail
            : "サーバーにつながりません。起動スクリプトで立ち上げ直し、示された新しい URL で開いてください。";
        holder.replaceChildren(
          topbar({
            title: "mindstella",
            tabs: [],
            current: "overview",
            theme,
            onNavigate: () => undefined,
            onSearch: () => undefined,
            onTheme: () => undefined,
            connection: "offline",
          }),
          h({ tag: "p", attrs: { class: "md-error" }, children: [message] }),
        );
      };
      const stop = subscribeEvents({
        onChanged: () => void attempt(),
        onConnection: (connected) => {
          if (connected) void attempt();
        },
      });
      void attempt();
    });
  }

  /** 記録を用意し（サーバーの配信では取得して）、画面を描いて操作とつなぐ */
  async function run(embedded: MindmapData | null): Promise<void> {
    /** サーバーの配信か（配る書き出しは記録を埋め込みから読み、送信も書き換えの知らせも持たない） */
    const serverMode = embedded === null;
    const storage = openStorage("localStorage");
    const session = openStorage("sessionStorage");
    const prefs = loadPrefs(storage);
    const persist = (): boolean => savePrefs({ storage, prefs });
    restoreTablePrefs(prefs.columns, (kind, tablePrefs) => {
      if (tablePrefs === null) delete prefs.columns[kind];
      else prefs.columns[kind] = tablePrefs;
      display.storageOk = persist();
      // 表の列の上書きは、パネルの「この端末で変えている項目」に合わせる
      resolved = resolveDisplay(prefs, data.settings.display);
      if (display.open) renderSettings();
    });

    // ===== テーマ =====
    /** 端末のライト / ダーク（個人の上書きが無いときに従う） */
    const systemTheme = (): Theme => (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    let theme: Theme = prefs.theme ?? systemTheme();
    document.documentElement.dataset["theme"] = theme;

    // ===== 記録 =====
    let data: MindmapData = embedded ?? (await waitForRecords(theme));
    let index = buildIndex(data);
    /** サーバーが返した記録そのもの（保存待ちの編集を当てる前）。`data` は保存待ちの編集を当てた、画面に出す値 */
    let serverData: MindmapData = data;
    /** 保存待ちの編集を当てる前の索引（保存待ちのパネルが項目の種類とタイトルを引く） */
    let serverIndex: RecordIndex = index;
    document.title = `${data.settings.summary} | mindstella`;
    let connection: "online" | "offline" = "online";
    // 表示の設定: 項目ごとに、個人の上書き → ワークスペースの既定 → 組み込みの既定の順で読み分けた値
    let resolved = resolveDisplay(prefs, data.settings.display);
    const display: DisplayState = { open: false, confirm: null, message: null, savedDisplay: null, storageOk: true };
    /** 表示しない種類のタブを指す route は、概要へ置き換える（`id` は残し、詳細パネルは開く） */
    const visibleRoute = (next: Route): Route =>
      next.tab === "overview" || next.tab === "graph" || resolved.kinds.has(next.tab)
        ? next
        : { ...next, tab: "overview", view: defaultView("overview"), filters: {} };
    // 差分の表示: そのタブの「前回開いてから」の始まりと、選んだ時点（持たない・記録に無いときは差分を出さない）
    const since = await resolveSince({ serverMode, prefs, persist, headSeq: data.changes.sets[0]?.until_seq ?? 0 });

    // ===== 画面の土台 =====
    const top = h({ tag: "div", attrs: { id: "top" } });
    const main = h({ tag: "main", attrs: { class: "content", id: "main" } });
    document.body.prepend(top, main);
    /** ハッシュの `diff`（無ければ端末の設定）が指す時点を引き、引けた時点を端末の設定と route に揃える（引けなければどちらも null） */
    const settleDiffPoint = (next: Route): { route: Route; point: DiffPoint | null } => {
      const settled = resolveDiffPoint(data.changes, next.diff ?? prefs.diffSel ?? null, since);
      const sel = settled?.sel ?? null;
      if ((prefs.diffSel ?? null) !== sel) {
        prefs.diffSel = sel;
        persist();
      }
      return { route: { ...next, diff: sel }, point: settled };
    };
    const initial = settleDiffPoint(visibleRoute(parseHash({ hash: location.hash, index })));
    let route = initial.route;
    let point: DiffPoint | null = initial.point;
    let fullViewer: HTMLElement | null = null;
    /** 詳細パネルがもう画面に入れた見出し（同じ項目・同じ見出しでは、描き直しのたびに本文のスクロールを戻さない） */
    let shownHeading: { id: string; heading: string } | null = null;
    const filterState: FilterState = { byTab: {}, drawerOpen: false };
    const lockState: LockState = { graph: null, map: null };
    const stack: StackState = { front: "detail" };
    const editState: EditState = {
      edits: [],
      blocked: [],
      open: false,
      editing: null,
      adding: null,
      status: "idle",
      errors: new Map(),
      toast: null,
      workspaceOpen: false,
    };

    /** 差分の表示中でなければ、保存待ちの編集（項目の追加を除く）を当てた記録と索引を作り直す。追加する項目は索引に入れず、一覧の画面の `adds` として別に渡す */
    const rebuildIndex = (): void => {
      data =
        point === null
          ? applyEdits(
              serverData,
              editState.edits.filter((entry) => entry.op !== "item-add"),
            )
          : serverData;
      index = buildIndex(data);
      serverIndex = buildIndex(serverData);
    };

    /** 差分の表示に移ったら、保存待ちのパネル・設定の画面・編集の表示を閉じる。そのうえで索引を作り直す */
    const syncEditView = (): void => {
      if (point !== null) {
        editState.open = false;
        editState.workspaceOpen = false;
        editState.editing = null;
        editState.adding = null;
      }
      rebuildIndex();
    };

    // ===== 移動 =====
    /** 詳細パネルを別画面として積む幅か */
    const isNarrow = (): boolean => matchMedia(NARROW_QUERY).matches;

    /** 画面の既定の URL（絞り込みは書かない）に route を書き、画面を描く */
    const go = (next: Route, push: boolean): void => {
      leaveEditViews();
      const screenChanged =
        next.tab !== route.tab || next.view !== route.view || Object.keys(next.filters).length > 0;
      const idChanged = next.id !== route.id;
      // 差分の時点は、画面・項目を移っても引き継ぐ
      route = { ...next, diff: route.diff };
      navigate({ route: { ...route, filters: {} }, push });
      render({ screen: screenChanged || (route.tab === "decisions" && route.view === "map" && idChanged) });
    };

    /** 項目を開く。パネル・全画面の中の移動は履歴に積み、見てきた項目を行き来できるようにする */
    const openItem = (id: string, inPanel: boolean): void => {
      // 追加する項目は、追加の入力で開く
      if (id.startsWith(NEW_ID_PREFIX)) {
        openAdded(id);
        return;
      }
      flushDrafts();
      leaveEditViews();
      const next: Route = { ...route, id, filters: {}, heading: null };
      const trail = history.state as Trail | null;
      if (inPanel && route.id !== null) {
        // 今いる履歴にも先の項目を持たせ、戻った後に「→」で進めるようにする
        const items = [...(trail?.items ?? [route.id]).slice(0, (trail?.position ?? 0) + 1), id];
        navigate({ route: { ...route, filters: {} }, push: false, trail: { items, position: trail?.position ?? 0 } });
        route = next;
        navigate({ route: next, push: true, trail: { items, position: items.length - 1 } });
        render({ screen: route.tab === "decisions" && route.view === "map" });
        return;
      }
      route = next;
      // 狭い幅では詳細を別画面として積み、戻る操作で一覧へ戻す
      navigate({ route: next, push: isNarrow(), trail: { items: [id], position: 0 } });
      render({ screen: route.tab === "decisions" && route.view === "map" });
    };

    /** 詳細パネルを閉じる */
    const closeDetail = (): void => {
      flushDrafts();
      if (isNarrow() && history.state !== null && (history.state as Trail).items !== undefined && history.length > 1) {
        history.back();
        return;
      }
      route = { ...route, id: null, full: false, filters: {}, heading: null };
      navigate({ route, push: false });
      render({ screen: route.tab === "decisions" && route.view === "map" });
      reopenPendingPanel();
    };

    /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
    const openFromSearch = (id: string): void => {
      const kind = index.byId.get(id)?.kind;
      if (kind === undefined) return;
      // 表示しない種類の項目は、概要の上の詳細パネルで開く
      const tab: Tab = resolved.kinds.has(kind) ? kind : "overview";
      go({ tab, view: defaultView(tab), id, full: false, filters: {}, heading: null, diff: route.diff }, tab !== route.tab);
    };

    // ===== ロック =====
    /** 効いているロック。画面ごとの `LockState` の項目が、その画面の絞り込みの条件を通る（描いている）ときだけその ID、通らないときは null（`LockState` は残し、条件を戻して描かれたらまたロック中に戻る） */
    const effectiveLock = (key: keyof LockState): string | null => {
      const id = lockState[key];
      if (id === null) return null;
      const shown =
        key === "graph"
          ? shownGraphIds({ index, filters: filterState.byTab["graph"] ?? {} })
          : shownDecisionIds({ index, filters: filterState.byTab["decisions"] ?? {} });
      return shown.has(id) ? id : null;
    };

    /** 玉か節（余白なら null）を押した、または `L` キーを押した。`lockTap` で判定し、`lock`・`unlock` のときだけ `LockState` を変えて画面に反映する。`open` は詳細を切り替え、`blank` は詳細を閉じて全体の表示へ戻し、`shake` は何も変えない（画面が鍵を震わせる） */
    const lockPress = ({ key, pressed }: { key: keyof LockState; pressed: string | null }): LockAction => {
      const result = lockTap({ locked: effectiveLock(key), pressed, open: route.id });
      if (result.action === "lock" || result.action === "unlock") {
        lockState[key] = result.locked;
        // ネットワークは視点を保ったまま中心と強調を寄せ、マップは詳細パネルをそのままに描き直す
        if (key === "graph") setGraphLock(effectiveLock("graph"));
        else redrawKeepingState();
      } else if (result.action === "open" && pressed !== null) {
        openItem(pressed, false);
      } else if (result.action === "blank" && route.id !== null) {
        closeDetail();
      }
      return result.action;
    };

    /** ネットワークの見た目のドロップダウンで選んだ値を個人の上書きに残す（ネットワークは作り直さず、次のコマから当てる） */
    const changeLook = (value: NetworkLook): void => {
      prefs.look = value;
      changePrefs({ redrawMain: false });
      setGraphLook(resolved.look);
    };

    // ===== 描く =====
    /** トップバーとタブの帯 */
    const renderTop = (): void => {
      const marks = marksOf(point);
      top.replaceChildren(
        topbar({
          title: data.settings.summary,
          tabs: TAB_KEYS.filter((key) => key === "overview" || resolved.kinds.has(key as Kind)).map((key) => ({
            key,
            label: tabLabel(key as Exclude<Tab, "graph">),
            icon: TAB_ICON[key as Exclude<Tab, "graph">],
            count: key === "overview" ? undefined : data[key as Kind].length,
            // 差分の表示の間、新規・変更・消した項目を持つ種類のタブに点を重ねる
            marked:
              key !== "overview" &&
              ((marks !== undefined && data[key as Kind].some((item) => marks[item.id] !== undefined)) ||
                removedOf({ point, kind: key as Kind }).length > 0),
          })),
          current: route.tab,
          theme,
          connection,
          readAt: serverMode ? data.built_at : null,
          comments: serverMode,
          commentCount: comment.review.items.length,
          commentsOpen: comment.listOpen,
          commentsUnread: anyOpenUnseen(comment.threads),
          onComments: () => (comment.listOpen ? closeList() : openList()),
          settingsOpen: display.open,
          onSettings: () => (display.open ? closeSettings() : openSettings()),
          // 概要以外の画面に絞り込みのボタンを置き、値を選んでいる条件の数をバッジに出す
          filter: route.tab !== "overview",
          filterCount: activeConditionCount(filterState.byTab[route.tab] ?? {}),
          filterOpen: filterState.drawerOpen,
          onFilter: toggleDrawer,
          pending: serverMode && point === null && editState.edits.length > 0,
          pendingCount: editState.edits.length,
          pendingOpen: editState.open,
          pendingBlocked: editState.blocked.length > 0,
          onPending: togglePending,
          diffPoint: point === null ? null : { name: point.name, sub: point.sub },
          onHistory: openHistory,
          onDiffOff: () => selectPoint(null),
          onNavigate: (tab) => go({ ...route, tab, view: defaultView(tab), filters: {} }, true),
          onSearch: openSearch,
          onTheme: (next) => {
            theme = next;
            prefs.theme = next;
            changePrefs({ redrawMain: false });
            document.documentElement.dataset["theme"] = next;
          },
        }),
      );
    };

    /** 今の画面 */
    const screenElement = (): HTMLElement => {
      const on = {
        open: (id: string) => openItem(id, false),
        view: (view: View) => go({ ...route, view, filters: {} }, false),
        filter: changeFilters,
        closeDrawer,
      };
      const marks = marksOf(point);
      // サーバーにつながって開いたときだけ、項目ごとのコメントの件数を渡す（配る書き出しは印を出さない）
      const comments = serverMode ? commentsNow : undefined;
      const filters = filterState.byTab[route.tab] ?? {};
      const { drawerOpen } = filterState;
      // 選んだ時点で消した、この画面の種類の項目
      const removed = removedOf({ point, kind: route.tab as Kind });
      switch (route.tab) {
        case "overview":
          return overviewScreen({
            index,
            on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) },
            marks,
            visibleKinds: resolved.kinds,
          });
        case "decisions":
          return decisionsScreen({
            index,
            route,
            on: { ...on, clear: closeDetail, lock: (id) => lockPress({ key: "map", pressed: id }) },
            lockedId: effectiveLock("map"),
            filters,
            drawerOpen,
            marks,
            comments,
            removed,
            edit: screenEdit("decisions"),
          });
        case "tasks":
          return tasksScreen({ index, route, on, filters, drawerOpen, marks, comments, removed, edit: screenEdit("tasks") });
        case "docs":
          return docsScreen({ index, route, on, filters, drawerOpen, marks, comments, removed, edit: screenEdit("docs") });
        case "graph":
          return graphScreen({
            index,
            on: {
              open: on.open,
              filter: changeFilters,
              closeDrawer,
              lock: (id) => lockPress({ key: "graph", pressed: id }),
              look: changeLook,
            },
            filters,
            drawerOpen,
            selectedId: route.id,
            lockedId: effectiveLock("graph"),
            look: resolved.look,
            defaultLook: resolved.defaultLook,
            comments,
          });
        default:
          return recordsScreen({
            index,
            route,
            on: { open: on.open, filter: changeFilters, closeDrawer },
            filters,
            drawerOpen,
            marks,
            comments,
            removed,
            edit: screenEdit(route.tab as Kind),
          });
      }
    };

    /** 本文の領域を描く。画面（タブ・表示形式）が変わったときだけ描き直す */
    const renderMain = (): void => {
      main.classList.toggle("map-view", route.tab === "decisions" && route.view === "map");
      // 概要は題名が h1。それ以外の画面は、画面の名前を見えない h1 にする（見出しで画面を探せるように）
      main.replaceChildren(
        ...(route.tab === "overview"
          ? []
          : [h({ tag: "h1", attrs: { class: "sr-only" }, children: [screenName(route.tab)] })]),
        screenElement(),
      );
      if (route.tab === "graph") selectGraphItem(route.id);
    };

    /** 画面の絞り込みの条件の定義と行（残した条件を今の記録で刈り込むのに使う）。概要は絞り込みを持たないので null */
    const filterSource = (tab: Route["tab"]): { rows: Row[]; columns: FilterColumn[] } | null => {
      const open = (): void => undefined;
      switch (tab) {
        case "overview":
          return null;
        case "graph":
          return { rows: [...index.byId].map(([id, entry]) => ({ id, ...entry })), columns: graphConditions() };
        case "decisions":
          return { rows: index.data.decisions, columns: decisionColumns({ index, open }) };
        case "tasks":
          return { rows: index.data.tasks, columns: taskColumns({ index, open }) };
        case "docs":
          return { rows: index.data.docs, columns: docColumns(index) };
        default:
          return { rows: index.data[tab], columns: recordColumns({ index, kind: tab, open }) };
      }
    };

    /** サーバーの配信で残した、その画面の条件を今の記録で刈り込んだもの。残した条件が無い画面と、配る書き出しは null */
    const savedFilters = (tab: Route["tab"]): Filters | null => {
      const saved = prefs.filters[tab];
      const source = filterSource(tab);
      if (!serverMode || saved === undefined || source === null) return null;
      return pruneFilters({ ...source, saved });
    };

    /** 今の画面の絞り込みを用意する。ハッシュの `f.{列}` があればそれだけを（開き直したときも）、無く初めて開く画面なら端末に残した条件か既定を入れ、ハッシュの分は一度だけ使う。概要には絞り込みのドロワーを置かないので閉じる（タブを押したときも、戻る・進むで移ったときも通る） */
    const prepareFilters = (): void => {
      if (route.tab === "overview") filterState.drawerOpen = false;
      if (Object.keys(route.filters).length > 0 || filterState.byTab[route.tab] === undefined) {
        filterState.byTab[route.tab] = initialFilters(route.tab, route.filters, savedFilters(route.tab));
      }
      route = { ...route, filters: {} };
    };

    /** 本文の差分の並べ方を切り替えた: 個人の上書きに残し、開いている詳細パネル・詳細の全画面だけを描き直す（履歴にもハッシュにも書かない）。本文を送った位置と、押したボタンのフォーカスを保つ */
    const changeBodyLayout = (layout: BodyLayout): void => {
      const bodySelector = route.full ? "dialog.full .panel-body" : "aside.panel .panel-body";
      const scrollTop = document.querySelector<HTMLElement>(bodySelector)?.scrollTop ?? 0;
      prefs.bodyLayout = layout === "side" ? "side" : null;
      display.storageOk = persist();
      resolved = resolveDisplay(prefs, data.settings.display);
      renderDetail();
      // 描き直した本文の高さは、文書に入った後の次のコマで決まる
      requestAnimationFrame(() => {
        const next = document.querySelector<HTMLElement>(bodySelector);
        if (next === null) return;
        next.scrollTop = scrollTop;
        next.querySelector<HTMLElement>(`[data-layout="${layout}"]`)?.focus({ preventScroll: true });
      });
      renderSettings();
    };

    /** 詳細パネルと全画面 */
    const renderDetail = (): void => {
      // 項目を追加する入力: 詳細パネルと同じ置き方で、追加の入力を開く
      if (isAdding()) {
        document.querySelector("aside.panel:not(.pe-add-panel)")?.remove();
        const full = document.querySelector<HTMLDialogElement>("dialog.full");
        full?.close();
        full?.remove();
        fullViewer = null;
        closePill();
        document.body.classList.add("panel-open");
        markSelected(null);
        renderAddPanel();
        return;
      }
      document.querySelector("aside.pe-add-panel")?.remove();
      const existing = document.querySelector<HTMLElement>("aside.panel");
      const fullDialog = document.querySelector<HTMLDialogElement>("dialog.full");
      fullViewer = null;
      closePill();
      document.body.classList.toggle("panel-open", route.id !== null && !route.full);
      markSelected(route.id);
      // 別の項目へ移るかパネルを閉じた: 詳細パネルで始めた書き換えは、一覧を開いていても捨てる（入力欄の無い一覧の行に「修正」「削除」の無い行を残さない）。一覧を開いていない間は、消した行と書き換えをすべて捨てる
      if (route.id !== detailShown) {
        detailShown = route.id;
        // 詳細パネルを開く・別の項目へ移った: 左のパネルを開いていても詳細パネルを前に出す
        if (route.id !== null) stack.front = "detail";
        const hadEdit = editing !== null;
        if (!comment.listOpen) {
          comment.removed = [];
          editing = null;
        } else if (editingIn === "detail") {
          editing = null;
        }
        if (editing === null) {
          editError = null;
          editBody = null;
          // 一覧を開いていれば、本文だけで残っていた行を直す
          if (hadEdit && comment.listOpen) renderComments();
        }
      }
      // 別の項目へ移った・パネルを閉じた: 編集の表示は読む表示に戻す（溜めた編集は保存待ちに残る）。追加する項目の入力は別に持つ
      if (editState.editing !== null && !editState.editing.startsWith(NEW_ID_PREFIX) && editState.editing !== route.id) {
        editState.editing = null;
      }
      // 開いている項目が無い: パネルも全画面も閉じる
      if (route.id === null) {
        flushDrafts();
        comment.opened = null;
        existing?.classList.remove("open");
        fullDialog?.close();
        fullDialog?.remove();
        return;
      }
      const panel = detailPanel({
        id: route.id,
        index,
        full: route.full,
        minimap: resolved.minimap,
        bodyLayout: resolved.bodyLayout,
        bodyView: resolved.bodyView,
        edit: detailEdit(),
        // 詳細パネルの左端に、そのタブで変えた幅から始める幅の区切りを置く（全画面は置かない。幅 900px 以下は CSS が隠し、窓を広げたときに出る）
        resizer: route.full
          ? null
          : panelResizer({
            stored: readPanelWidth(session),
            mapView: () => route.tab === "decisions" && route.view === "map",
            onChange: (width) => writePanelWidth({ session, width }),
          }),
        on: {
          open: (id) => openItem(id, true),
          layout: changeBodyLayout,
          close: closeDetail,
          full: (full) => {
            // 全画面の中で図を拡大しているときは、本文へ戻る
            if (!full && fullViewer !== null) return closeFullViewer();
            go({ ...route, full }, false);
          },
          back: () => history.back(),
          forward: () => history.forward(),
          diagram: showDiagram,
          frame: { select: frameSelect, clear: frameClear },
          // 本文の見出しへ移った: ハッシュの `h` を、履歴に積まずに置き換える
          heading: (heading) => {
            route = { ...route, heading };
            shownHeading = heading === null || route.id === null ? null : { id: route.id, heading };
            navigate({ route: { ...route, filters: {} }, push: false });
          },
          // 本文のまとまりのリンクを押した: 記録にあるまとまりのときだけ、変更履歴で選んだときと同じに切り替える
          changeSet: openChangeSet,
        },
        comment: serverMode
          ? {
            form: formProps(route.id),
            reviews: comment.review.items.filter((item) => item.target === route.id),
            edit: {
              removed: comment.removed.filter((item) => item.target === route.id),
              editing,
              editingIn,
              editError,
              editBody,
              on: reviewRowHandlers(REVIEW_FOCUS),
            },
          }
          : null,
        highlight: openedLocation(),
        diff: point,
        // 開いたときにだけ見出しを画面に入れる
        heading: shownHeading?.id === route.id && shownHeading.heading === route.heading ? null : route.heading,
      });
      shownHeading = route.heading === null ? null : { id: route.id, heading: route.heading };
      if (route.full) {
        existing?.classList.remove("open");
        fullDialog?.remove();
        document.body.append(panel);
        (panel as HTMLDialogElement).showModal();
        return;
      }
      fullDialog?.close();
      fullDialog?.remove();
      if (existing === null) {
        // 初めて開く: すべり込ませるため、置いてから次のコマで開いた状態にする
        document.body.append(panel);
        requestAnimationFrame(() => panel.classList.add("open"));
      } else {
        // 開いたまま項目を移った: すべり込ませずに中身だけを入れ替える
        existing.className = `${panel.className} open`;
        existing.replaceChildren(...panel.children);
      }
    };

    /** コメントの一覧の行から開いたとき、そのコメントの箇所。別の項目へ移っていれば示すのをやめる */
    const openedLocation = (): Location | null => {
      // スレッドの向けた項目から開いた: その項目の中でだけ箇所を示す
      if (comment.highlight !== null) {
        if (comment.highlight.target === route.id) return comment.highlight.loc;
        comment.highlight = null;
      }
      const opened = comment.review.items.find((item) => item.id === comment.opened);
      if (opened === undefined || opened.target !== route.id) {
        comment.opened = null;
        return null;
      }
      return opened.loc;
    };

    /** 描く（`screen` が真のとき本文の領域も描き直す） */
    const render = ({ screen }: { screen: boolean }): void => {
      prepareFilters();
      renderTop();
      if (screen) {
        const wide = document.querySelector<HTMLElement>(".table-wrap, .map-wrap, .board");
        const keep = wide === null ? 0 : wide.scrollTop;
        renderMain();
        void keep;
      }
      renderDetail();
      renderPending();
      renderWorkspace();
      if (route.tab === "graph") selectGraphItem(route.id);
      // 作り直した本文にも、開いているパネルの下の部品を止める
      scheduleInert();
    };

    // ===== 絞り込み =====
    /** 開いているパネルが覆った本文の部品を止める関数が返した、止めた分を外す関数 */
    let releaseInert: (() => void) | null = null;

    /** 開いている左のパネル（絞り込みのドロワー・コメントの一覧・表示の設定のパネル）。開いていなければ null */
    const openLeftPanel = (): HTMLElement | null =>
      filterState.drawerOpen
        ? document.querySelector<HTMLElement>("dialog.drawer")
        : comment.listOpen
          ? document.querySelector<HTMLElement>(".comments-panel")
          : editState.open
            ? document.querySelector<HTMLElement>(".pending-panel")
            : display.open
              ? document.querySelector<HTMLElement>(".settings-drawer")
              : null;

    /** 幅 900px 以下で詳細パネルと左のパネルを両方開いていて、左のパネルを前に出しているか */
    const isLeftFront = (): boolean =>
      isNarrow() &&
      route.id !== null &&
      !route.full &&
      stack.front === "left" &&
      (filterState.drawerOpen || comment.listOpen || display.open || editState.open);

    /** 幅 900px 以下で両方を開いているとき、前に出す側を `left-front` で決め、後ろになった側の部品に `inert` を付ける。それ以外は付けた分を外す */
    const applyStack = (): void => {
      const detail = document.querySelector<HTMLElement>("aside.panel");
      const left = openLeftPanel();
      const both = isNarrow() && route.id !== null && !route.full && detail !== null && left !== null;
      const leftFront = both && stack.front === "left";
      document.body.classList.toggle("left-front", leftFront);
      if (detail !== null) detail.inert = leftFront;
      if (left !== null) left.inert = both && !leftFront;
    };

    /** 前に止めた分を外してから、開いているパネル（絞り込みのドロワー・コメントの一覧・表示の設定のパネル）が覆った本文の部品を止め、詳細パネルとの前後を当てる */
    const applyInert = (): void => {
      releaseInert?.();
      releaseInert = null;
      const panel = openLeftPanel();
      if (panel !== null) releaseInert = inertBehind(panel);
      applyStack();
    };

    // 幅が 900px をまたいだとき、前後と `inert` をやり直す
    matchMedia(NARROW_QUERY).addEventListener("change", applyInert);

    /** パネルが開いた後（ドロワーは文書に入った後の次のマイクロタスクで開く）に、本文の部品を止める */
    const scheduleInert = (): void => queueMicrotask(applyInert);

    /** 画面の条件を変えて描き直す（ドロワーは開いたまま） */
    const changeFilters = (next: Filters): void => {
      filterState.byTab[route.tab] = next;
      // サーバーの配信では、条件を変えるたびに端末へ残す（表示の設定の「この端末で変えている項目」も合わせる）
      if (serverMode) {
        prefs.filters[route.tab] = { ...next };
        display.storageOk = persist();
        resolved = resolveDisplay(prefs, data.settings.display);
        if (display.open) renderSettings();
      }
      redrawKeepingState();
    };

    /** 絞り込みのドロワーを閉じ、絞り込みのボタンへフォーカスを戻す */
    const closeDrawer = (): void => {
      filterState.drawerOpen = false;
      redrawKeepingState();
      document.querySelector<HTMLElement>("[data-act='filter']")?.focus();
    };

    /** 絞り込みのドロワーを開く・閉じる（開くときはコメントの一覧と表示の設定のパネルを閉じる） */
    const toggleDrawer = (): void => {
      if (filterState.drawerOpen) {
        closeDrawer();
        return;
      }
      if (comment.listOpen) closeList();
      if (display.open) {
        display.open = false;
        renderSettings();
      }
      editState.open = false;
      renderPending();
      filterState.drawerOpen = true;
      stack.front = "left";
      redrawKeepingState();
    };

    // ===== 図の拡大 =====
    /** 図を拡大して見る。詳細パネルからはモーダル、全画面からは全画面の中身を切り替える */
    const showDiagram = (svg: SVGElement, diff: DiagramViewerDiff | null): void => {
      if (route.full) {
        const dialog = document.querySelector<HTMLDialogElement>("dialog.full");
        const body = dialog?.querySelector<HTMLElement>(".panel-body");
        if (dialog === null || dialog === undefined || body === null || body === undefined) return;
        body.hidden = true;
        const viewer = h({
          tag: "div",
          attrs: { class: "full-viewer" },
          children: [diagramViewer({ svg, on: { close: closeFullViewer }, diff })],
        });
        body.after(viewer);
        fullViewer = viewer;
        return;
      }
      const modal = h({ tag: "dialog", attrs: { class: "viewer", "aria-label": "図の拡大" } });
      modal.append(diagramViewer({ svg, on: { close: () => modal.close() }, diff }));
      modal.addEventListener("close", () => modal.remove());
      document.body.append(modal);
      modal.showModal();
    };

    /** 全画面の中の図の拡大を閉じて、本文に戻す */
    const closeFullViewer = (): void => {
      fullViewer?.remove();
      fullViewer = null;
      const body = document.querySelector<HTMLElement>("dialog.full .panel-body");
      if (body !== null) body.hidden = false;
    };

    // ===== 全体の検索 =====
    /** 検索を開く（開いているときは何もしない） */
    const openSearch = (): void => {
      if (document.querySelector("dialog.search") !== null) return;
      const dialog = searchDialog({
        index,
        on: {
          open: (id) => {
            dialog.close();
            openFromSearch(id);
          },
          close: () => dialog.remove(),
        },
      });
      document.body.append(dialog);
      dialog.showModal();
    };

    // ===== コメント =====
    const api = commentApi();
    const comment: CommentState = {
      review: { items: [], drafts: [] },
      forms: new Map(),
      pendingLoc: new Map(),
      checked: new Set(),
      removed: [],
      stale: new Map(),
      listOpen: false,
      opened: null,
      highlight: null,
      threads: [],
      threadsError: null,
      view: "list",
      reviewFrom: "list",
      filter: "open",
      tag: null,
      openedThread: null,
      composing: false,
      reason: { open: false, body: "", status: "idle", detail: null },
      reviewFocus: null,
      expanded: new Set(),
    };
    const threadsApi = threadApi();
    /** 一覧のスクロールの位置（スレッドを開くときに控え、一覧へ戻るときに戻す） */
    let listScroll = 0;
    /** まとめて送った結果・本文を直している行・直せなかった理由・項目を指さない入力にフォーカスがあるか */
    let outcome: SendOutcome | null = null;
    let editing: string | null = null;
    /** `editing` の修正を始めた場所（入力欄はその場所だけに描く） */
    let editingIn: EditingIn = "list";
    let editError: string | null = null;
    let editBody: string | null = null;
    /** 詳細パネルが今出している項目（別の項目へ移ったか閉じたかを知るため） */
    let detailShown: string | null = null;
    /** チェックした状態で入れるのは、初めて読んだコメントだけ */
    const knownIds = new Set<string>();

    /** 各画面へ渡す項目の ID → コメントの件数。画面は描き直すたびにこれを読むので、件数が変わったときは同じ物の中身を入れ替える */
    const commentsNow: Record<string, number> = {};

    /** レビュー中のコメントの件数が変わっていれば、画面を描き直さずに印だけを差し替える（つながりは次のコマから） */
    const syncCommentMarks = (): void => {
      const next = commentCounts(comment.review.items);
      if (sameCounts(commentsNow, next)) return;
      for (const key of Object.keys(commentsNow)) delete commentsNow[key];
      Object.assign(commentsNow, next);
      refreshCommentMarks({ root: main, counts: commentsNow });
      setGraphComments(commentsNow);
    };
    /** 書きかけを保つ待ちのタイマー（入力欄のキー → タイマー） */
    const draftTimers = new Map<string, number>();

    /** 読んだレビュー中を状態に入れる。初めて読んだコメントはチェックした状態で入れ、最初の読み込みだけ書きかけの箇所を入力に添える */
    const applyReview = (review: ReviewState, first: boolean): void => {
      comment.review = review;
      syncCommentMarks();
      for (const item of review.items) {
        if (knownIds.has(item.id)) continue;
        knownIds.add(item.id);
        comment.checked.add(item.id);
      }
      if (!first) return;
      for (const draft of review.drafts) {
        if (draft.target !== null && draft.loc !== null && !comment.pendingLoc.has(draft.target)) {
          comment.pendingLoc.set(draft.target, draft.loc);
        }
      }
    };

    /** レビュー中のコメントと書きかけを読み直す。届かないときは前の写しのまま */
    const loadReview = async (first = false): Promise<void> => {
      const result = await api.read();
      if (result.ok && result.data !== null) applyReview(result.data, first);
    };

    /** 利用者の既読にする要求を送っているスレッドの ID（応答を待つ間に読み直しても、同じスレッドへ重ねて送らない） */
    const seenSending = new Set<string>();

    /** 既読にする要求が失敗したスレッドの ID（別のスレッドを開くか一覧へ戻るまで、同じスレッドへ重ねて送らない） */
    const seenFailed = new Set<string>();

    /** 開いているスレッドに利用者の未読があれば、写しを既読にして印を待たずに消し、要求は応答を待たずに送る。失敗しても画面に出さず、写しをサーバーの値に戻す */
    const markOpenedSeen = (): void => {
      const opened = comment.openedThread;
      if (comment.view !== "thread" || opened === null || opened.pending) return;
      if (seenSending.has(opened.id) || seenFailed.has(opened.id)) return;
      const thread = comment.threads.find((entry) => entry.id === opened.id);
      if (thread === undefined || !hasUnseen(thread)) return;
      seenSending.add(opened.id);
      const wasUnseen = anyOpenUnseen(comment.threads);
      comment.threads = withSeen({ threads: comment.threads, id: opened.id });
      if (wasUnseen !== anyOpenUnseen(comment.threads)) preserving(renderTop);
      void threadsApi
        .seen(opened.id)
        .then(async (result) => {
          if (result.ok) return;
          // 断られた・届かないとき: 送っている控えから失敗の控えへ移して、写しをサーバーの値に戻す
          seenSending.delete(opened.id);
          seenFailed.add(opened.id);
          await loadThreads();
          renderComments();
        })
        .finally(() => seenSending.delete(opened.id));
    };

    /** スレッドを読み直す。読めたら置き換え（トップバーの未読の点が変わるなら描き直し）、断られた・届かないときは前のまま残して理由を持つ */
    const loadThreads = async (): Promise<void> => {
      const result = await threadsApi.read();
      if (result.ok && result.data !== null) {
        const wasUnseen = anyOpenUnseen(comment.threads);
        // 既読にする要求を送っている間は、送る前のサーバーの値で写しを未読に戻さない
        comment.threads = [...seenSending].reduce(
          (threads, id) => withSeen({ threads, id }),
          result.data.threads,
        );
        comment.threadsError = null;
        if (wasUnseen !== anyOpenUnseen(comment.threads)) preserving(renderTop);
        markOpenedSeen();
        return;
      }
      comment.threadsError = { detail: result.ok ? null : result.detail };
    };

    /** 向けた先の入力欄の状態。無ければ、同じ向けた先の書きかけの本文で作る */
    const formStateOf = (target: string | null, loc: Location | null, thread: string | null = null): FormState => {
      const key = formKey(target, loc, thread);
      let state = comment.forms.get(key);
      if (state === undefined) {
        const draft = comment.review.drafts.find((entry) => formKey(entry.target, entry.loc, entry.thread ?? null) === key);
        state = { target, loc, thread, body: draft?.body ?? "", status: "idle", count: null, detail: null };
        comment.forms.set(key, state);
      }
      return state;
    };

    /** 書きかけをすぐ保つ（空なら消える）。届かないときは何も出さない */
    const saveDraftNow = (state: FormState): void => {
      const key = formKey(state.target, state.loc, state.thread);
      window.clearTimeout(draftTimers.get(key));
      draftTimers.delete(key);
      void api.saveDraft({
        ...(state.target === null ? {} : { target: state.target }),
        ...(state.loc === null ? {} : { loc: state.loc }),
        ...(state.thread === null ? {} : { thread: state.thread }),
        body: state.body,
      });
    };

    /** 入力が止まってから書きかけを保つ */
    const scheduleDraft = (state: FormState): void => {
      const key = formKey(state.target, state.loc, state.thread);
      window.clearTimeout(draftTimers.get(key));
      draftTimers.set(
        key,
        window.setTimeout(() => saveDraftNow(state), DRAFT_SAVE_DELAY_MS),
      );
    };

    /** 待っている書きかけを全て、待たずに保つ（パネル・一覧を閉じるときと項目を移るとき） */
    const flushDrafts = (): void => {
      for (const key of [...draftTimers.keys()]) {
        const state = comment.forms.get(key);
        if (state !== undefined) saveDraftNow(state);
      }
    };

    /** 開いている入力の結果を消す。入力中の欄を作り直さない（変換の途中を壊さないため） */
    const clearSendResult = (): void => {
      const form = document.activeElement?.closest("form.send");
      const message = form?.querySelector(".send-msg");
      if (message !== null && message !== undefined) {
        message.className = "send-msg";
        message.replaceChildren();
      }
      form?.querySelector("textarea")?.removeAttribute("aria-invalid");
    };

    /** 入力欄を、今の状態で差し替える（`focus` なら入力欄へフォーカスを戻す）。別の項目へ移っていたら状態だけ持っておく */
    const redrawForm = ({ target, focus }: { target: string | null; focus: boolean }): void => {
      // 項目を指さない入力（新しいスレッド）はパネルの一部なので、パネルを描き直す
      if (target === null) {
        renderComments();
        if (focus) {
          const field = document.querySelector<HTMLTextAreaElement>(".comments-panel .talk-new form.send textarea");
          field?.focus();
          field?.setSelectionRange(field.value.length, field.value.length);
        }
        return;
      }
      const current = document.querySelector<HTMLFormElement>(route.full ? "dialog.full form.send" : "aside.panel form.send");
      if (current === null || route.id !== target) return;
      const next = sendForm(formProps(target));
      current.replaceWith(next);
      if (!focus) return;
      const field = next.querySelector("textarea");
      field?.focus();
      field?.setSelectionRange(field.value.length, field.value.length);
    };

    /** 箇所を外す。書きかけは箇所を持たない向けた先へ移す */
    const unquote = (state: FormState): void => {
      const { target } = state;
      if (target === null || state.loc === null) return;
      const plain = formStateOf(target, null);
      // 箇所を持つ書きかけを消し、本文を箇所を持たない向けた先へ移す
      const moved = state.body;
      saveDraftNow({ ...state, body: "" });
      comment.forms.delete(formKey(target, state.loc));
      comment.pendingLoc.delete(target);
      if (moved !== "") {
        plain.body = plain.body === "" ? moved : `${plain.body}\n${moved}`;
        saveDraftNow(plain);
      }
      redrawForm({ target, focus: true });
    };

    /** 入力欄の引数。`target` が null なら、コメントの一覧の下端の項目を指さない入力 */
    const formProps = (target: string | null): SendFormProps => {
      const loc = target === null ? null : (comment.pendingLoc.get(target) ?? null);
      const state = formStateOf(target, loc);
      return {
        target,
        loc,
        body: state.body,
        status: state.status,
        count: state.count,
        detail: state.detail,
        collapsed: false,
        ...(target === null ? { label: "新しいスレッド" } : {}),
        on: {
          input: (body) => {
            state.body = body;
            scheduleDraft(state);
            // 溜めた・本文が空の結果は、入力を始めたら消す（溜められなかった結果は次に溜めるまで残す）
            if (state.status === "saved" || state.status === "empty") {
              state.status = "idle";
              clearSendResult();
            }
          },
          save: (body) => void saveComment(state, body),
          unquote: () => unquote(state),
          copy: (body) => void navigator.clipboard?.writeText(body),
          focus: () => undefined,
          blur: () => undefined,
        },
      };
    };

    /** 本文を溜め、結果を状態に残して部品を描き直す */
    const saveComment = async (state: FormState, body: string): Promise<void> => {
      state.body = body;
      // 空白だけ: 溜めず、入力欄へフォーカスを戻す
      if (body.trim() === "") {
        Object.assign(state, { status: "empty", detail: null });
        redrawForm({ target: state.target, focus: true });
        return;
      }
      // 溜める前に、この向けた先の書きかけを保つ待ちを止める（応答を待つ間にタイマーが切れて、消えた書きかけを書き戻さないため）
      window.clearTimeout(draftTimers.get(formKey(state.target, state.loc)));
      draftTimers.delete(formKey(state.target, state.loc));
      Object.assign(state, { status: "saving", detail: null });
      redrawForm({ target: state.target, focus: true });
      const result = await api.add({
        ...(state.target === null ? {} : { target: state.target }),
        ...(state.loc === null ? {} : { loc: state.loc }),
        body,
      });
      if (!result.ok || result.data === null) {
        // 断られた・届かない: 本文を残す
        Object.assign(state, { status: "failed", detail: result.ok ? null : result.detail });
        // 止めた待ちを戻す（本文を残したまま閉じても、書きかけは保つ）
        scheduleDraft(state);
        redrawForm({ target: state.target, focus: true });
        return;
      }
      // 溜めた: 入力欄と添えた箇所を空にし、結果は箇所を持たない入力に出す
      const added = result.data;
      if (state.loc !== null && state.target !== null) {
        comment.forms.delete(formKey(state.target, state.loc));
        comment.pendingLoc.delete(state.target);
      }
      const shown = formStateOf(state.target, null);
      Object.assign(shown, { status: "saved", count: added.count, detail: null });
      // 箇所を持たない入力を溜めたときだけ本文を空にする（箇所を持つ入力を溜めたときは、別の向けた先の書きかけを残す）
      if (state.loc === null) shown.body = "";
      knownIds.add(added.id);
      comment.checked.add(added.id);
      await loadReview();
      refreshComments();
      redrawForm({ target: state.target, focus: true });
    };

    // ===== コメントの一覧 =====
    /** 開いているスレッドの返信の入力の引数（書きかけの本文を含む） */
    const replyState = (): ReplyState => {
      const opened = comment.openedThread;
      // スレッドを開いていない・まだ送っていない新しいスレッド: 返信の入力は出さない
      if (opened === null || opened.pending) return { body: "", status: "idle", count: null, detail: null };
      const { body, status, count, detail } = formStateOf(null, null, opened.id);
      return { body, status: status === "empty" ? "idle" : status, count, detail };
    };

    /** 描き直す前に、打っている途中の理由を状態に写す（理由は確定のときにだけ入力部品が知らせるため） */
    const captureTyped = (): void => {
      const reasonField = document.querySelector<HTMLTextAreaElement>(".comments-panel form.th-reason textarea");
      if (reasonField !== null && comment.reason.open) comment.reason.body = reasonField.value;
    };

    /** 一覧を作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
    const renderComments = (): void => {
      const current = document.querySelector<HTMLElement>(".comments-panel");
      if (!comment.listOpen) {
        current?.remove();
        scheduleInert();
        return;
      }
      captureTyped();
      const active = document.activeElement;
      const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
      // 入力欄（新しいスレッド・返信・理由）に打っている途中なら、選択も保つ
      const typing =
        active instanceof HTMLTextAreaElement && active.closest(".comments-panel form.send, .comments-panel form.th-reason") !== null
          ? active
          : null;
      const typingForm = typing?.closest("form")?.classList.contains("th-reason") === true ? "form.th-reason" : "form.send";
      const selection = typing === null ? null : { start: typing.selectionStart, end: typing.selectionEnd };
      const scroll = current?.querySelector<HTMLElement>(".comments-body")?.scrollTop ?? 0;
      const next = commentsPanel(panelProps());
      if (current === null) {
        document.body.append(next);
        requestAnimationFrame(() => next.classList.add("open"));
      } else {
        current.className = `${next.className} open`;
        current.replaceChildren(...next.children);
      }
      const panel = document.querySelector<HTMLElement>(".comments-panel");
      const body = panel?.querySelector<HTMLElement>(".comments-body");
      if (body !== null && body !== undefined) body.scrollTop = scroll;
      if (typing !== null && selection !== null) {
        const restored = panel?.querySelector<HTMLTextAreaElement>(`${typingForm} textarea`);
        restored?.focus();
        restored?.setSelectionRange(selection.start, selection.end);
      } else if (focusKey !== null) {
        panel?.querySelector<HTMLElement>(`[data-focus="${focusKey}"]`)?.focus();
      }
      scheduleInert();
    };

    /** トップバーの件数・詳細パネルのレビュー中のコメント・一覧を、入力中の欄とスクロールの位置を保って描き直す */
    const refreshComments = (): void => {
      preserving(() => {
        renderTop();
        renderDetail();
      });
      renderComments();
    };

    /** パネルの中の画面の状態を、開いた直後（スレッドの一覧）に戻す */
    const resetPanelView = (): void => {
      comment.view = "list";
      comment.reviewFrom = "list";
      comment.openedThread = null;
      comment.composing = false;
      comment.reason = { open: false, body: "", status: "idle", detail: null };
      comment.reviewFocus = null;
    };

    /** コメントの一覧を開く（絞り込みのドロワーは閉じ、スレッドの一覧から始める） */
    const openList = (): void => {
      // 絞り込みのドロワー・表示の設定のパネルとは 1 つだけを開く
      if (filterState.drawerOpen) {
        filterState.drawerOpen = false;
        redrawKeepingState();
      }
      display.open = false;
      renderSettings();
      editState.open = false;
      renderPending();
      comment.listOpen = true;
      stack.front = "left";
      resetPanelView();
      renderTop();
      renderComments();
      // スレッドを読み直して、届いていた AI の返信などを足す
      void loadThreads().then(renderComments);
    };

    /** 一覧で始めた書き換えを捨てる（一覧を閉じると、詳細パネルの行が本文だけのまま残るため）。捨てたかを返す */
    const discardListEdit = (): boolean => {
      if (editing === null || editingIn !== "list") return false;
      editing = null;
      editError = null;
      editBody = null;
      return true;
    };

    /** コメントの一覧を閉じる */
    const closeList = (): void => {
      flushDrafts();
      comment.listOpen = false;
      comment.opened = null;
      comment.highlight = null;
      comment.removed = [];
      comment.expanded.clear();
      discardListEdit();
      renderTop();
      renderComments();
      renderDetail();
    };

    /** 行の向けた項目を、一覧を開いたまま詳細パネルに開く（箇所があればその箇所を示す） */
    const openRow = (item: ReviewItem): void => {
      if (item.target === null) return;
      comment.opened = item.id;
      comment.highlight = null;
      // いま開いている項目を指す行でも、詳細パネルを一覧の前に出す
      stack.front = "detail";
      if (route.id === item.target) {
        renderDetail();
        renderComments();
        return;
      }
      openItem(item.target, false);
      renderComments();
    };

    /** 本文の中の ID・スレッドの向けた項目を、パネルを開いたまま詳細パネルに開く（箇所があればその箇所を示す） */
    const openFromThread = (id: string, loc?: Location): void => {
      comment.opened = null;
      comment.highlight = loc === undefined ? null : { target: id, loc };
      // いま開いている項目を指すときでも、詳細パネルをパネルの前に出す
      stack.front = "detail";
      if (route.id === id) {
        renderDetail();
        renderComments();
        return;
      }
      openItem(id, false);
      renderComments();
    };

    /** スレッドを開く。一覧のスクロールの位置を控え、理由の入力は閉じて空にする */
    const openThread = (id: string, pending: boolean): void => {
      listScroll = document.querySelector<HTMLElement>(".comments-panel .comments-body")?.scrollTop ?? 0;
      comment.openedThread = { id, pending };
      comment.view = "thread";
      seenFailed.clear();
      comment.reason = { open: false, body: "", status: "idle", detail: null };
      renderComments();
      markOpenedSeen();
    };

    /** スレッドの返信の書きかけを、待たずに保つ */
    const flushReplyDraft = (): void => {
      const opened = comment.openedThread;
      if (opened === null || opened.pending) return;
      const state = comment.forms.get(formKey(null, null, opened.id));
      if (state !== undefined && draftTimers.has(formKey(null, null, opened.id))) saveDraftNow(state);
    };

    /** 一覧・開く前の画面へ戻る（スレッドの画面と、レビュー中の書き込みの画面の「戻る」） */
    const goBack = (): void => {
      if (comment.view === "thread") {
        flushReplyDraft();
        const opened = comment.openedThread;
        comment.view = "list";
        comment.openedThread = null;
        seenFailed.clear();
        comment.reason = { open: false, body: "", status: "idle", detail: null };
        renderComments();
        // 控えたスクロールの位置と、開いていた行へのフォーカスを戻す
        const body = document.querySelector<HTMLElement>(".comments-panel .comments-body");
        if (body !== null) body.scrollTop = listScroll;
        if (opened !== null) {
          const key = opened.pending ? `thread:new:${opened.id}` : `thread:${opened.id}`;
          document.querySelector<HTMLElement>(`.comments-panel [data-focus="${key}"]`)?.focus();
        }
        return;
      }
      if (comment.view === "review") {
        const opened = comment.openedThread;
        // 開く前に見ていた、まだ送っていない新しいスレッドが、送るか消すかで無くなっていたら一覧へ戻る
        const gone =
          comment.reviewFrom === "thread" &&
          opened !== null &&
          opened.pending &&
          !comment.review.items.some((item) => item.id === opened.id) &&
          !comment.removed.some((item) => item.id === opened.id);
        comment.view = gone ? "list" : comment.reviewFrom;
        if (gone) comment.openedThread = null;
        comment.reviewFocus = null;
        renderComments();
        document.querySelector<HTMLElement>('.comments-panel [data-focus="review"]')?.focus();
      }
    };

    /** レビュー中の書き込みの画面を開く（開く前の画面を控える） */
    const openReview = (): void => {
      flushDrafts();
      comment.reviewFrom = comment.view === "thread" ? "thread" : "list";
      const opened = comment.openedThread;
      comment.reviewFocus = comment.view === "thread" && opened !== null && !opened.pending ? opened.id : null;
      comment.view = "review";
      renderComments();
    };

    /** 開いているスレッドの状態を変える（理由は空白だけなら送らない） */
    const changeStatus = async (status: "open" | "closed", reason: string): Promise<void> => {
      const opened = comment.openedThread;
      if (opened === null || opened.pending) return;
      comment.reason = { open: true, body: reason, status: "saving", detail: null };
      renderComments();
      const result = await threadsApi.setStatus(opened.id, status, reason);
      // 断られた・届かない: 理由の入力を開いたまま、理由を出す
      if (!result.ok) {
        comment.reason = { open: true, body: reason, status: "failed", detail: result.detail };
        renderComments();
        return;
      }
      comment.reason = { open: false, body: "", status: "idle", detail: null };
      await loadThreads();
      renderComments();
      document.querySelector<HTMLElement>('.comments-panel [data-focus="status"]')?.focus();
    };

    /** 返信を溜める。溜めたらレビュー中を読み直して、パネルを描き直す */
    const saveReply = async (threadId: string, body: string): Promise<void> => {
      const state = formStateOf(null, null, threadId);
      state.body = body;
      // 溜める前に、この返信の書きかけを保つ待ちを止める（応答を待つ間にタイマーが切れて、消えた書きかけを書き戻さないため）
      window.clearTimeout(draftTimers.get(formKey(null, null, threadId)));
      draftTimers.delete(formKey(null, null, threadId));
      Object.assign(state, { status: "saving", detail: null });
      renderComments();
      const result = await api.add({ thread: threadId, body });
      if (!result.ok || result.data === null) {
        // 断られた・届かない: 本文を残す
        Object.assign(state, { status: "failed", detail: result.ok ? null : result.detail });
        scheduleDraft(state);
        renderComments();
        return;
      }
      Object.assign(state, { body: "", status: "saved", count: result.data.count, detail: null });
      knownIds.add(result.data.id);
      comment.checked.add(result.data.id);
      await loadReview();
      refreshComments();
      document.querySelector<HTMLTextAreaElement>(".comments-panel form.reply textarea")?.focus();
    };

    /** 返信の入力の中身が変わった。書きかけを保つ待ちを入れ、溜めた・失敗の結果は消す */
    const typeReply = (body: string): void => {
      const opened = comment.openedThread;
      if (opened === null || opened.pending) return;
      const state = formStateOf(null, null, opened.id);
      state.body = body;
      scheduleDraft(state);
      // 溜めた結果は、入力を始めたら消す（溜められなかった結果は次に溜めるまで残す）
      if (state.status === "saved") {
        state.status = "idle";
        clearSendResult();
      }
    };

    /** コメントの一覧の引数 */
    const panelProps = (): CommentsPanelProps => ({
      view: comment.view,
      items: comment.review.items,
      removed: comment.removed,
      threads: comment.threads,
      threadsError: comment.threadsError,
      filter: comment.filter,
      tag: comment.tag,
      opened: comment.openedThread,
      composing: comment.composing,
      free: formProps(null),
      reply: replyState(),
      reason: comment.reason,
      checked: comment.checked,
      editing,
      editingIn,
      editError,
      editBody,
      stale: comment.stale,
      result: outcome,
      selected: comment.opened,
      reviewFocus: comment.reviewFocus,
      titleOf: (id) => index.byId.get(id)?.item.title ?? null,
      changeSetOf: (id) => data.changes.sets.find((set) => set.id === id)?.summary ?? null,
      expanded: comment.expanded,
      on: {
        close: closeList,
        review: openReview,
        back: goBack,
        filter: (filter) => {
          comment.filter = filter;
          renderComments();
        },
        tag: (tag) => {
          comment.tag = comment.tag === tag ? null : tag;
          renderComments();
        },
        clearTag: () => {
          comment.tag = null;
          renderComments();
        },
        compose: (open) => {
          comment.composing = open;
          renderComments();
          // 出したときは入力欄へ、畳んだときは「新しいスレッド」へフォーカスを移す
          const target = open ? ".comments-panel .talk-new form.send textarea" : '.comments-panel [data-focus="compose"]';
          document.querySelector<HTMLElement>(target)?.focus();
        },
        openThread,
        openId: openFromThread,
        changeSet: openChangeSet,
        reply: (thread, body) => void saveReply(thread, body),
        replyInput: typeReply,
        reasonOpen: (open) => {
          comment.reason = { open, body: "", status: "idle", detail: null };
          renderComments();
          const target = open ? '.comments-panel [data-focus="reason"]' : '.comments-panel [data-focus="status"]';
          document.querySelector<HTMLElement>(target)?.focus();
        },
        reasonInput: (body) => {
          comment.reason.body = body;
        },
        setStatus: (status, reason) => void changeStatus(status, reason),
        check: (id, checked) => {
          if (checked) comment.checked.add(id);
          else comment.checked.delete(id);
          renderComments();
        },
        checkAll: (checked) => {
          comment.checked = checked
            ? new Set(comment.review.items.filter((item) => !isBlockedReply(item, comment.threads)).map((item) => item.id))
            : new Set();
          renderComments();
        },
        send: () => void sendChecked(),
        open: openRow,
        ...reviewRowHandlers(""),
        unloc: (id) => void detachLocation(id),
        fold: (id, open) => {
          // 部品が行の中でその場で切り替えているので、描き直さず覚えるだけにする
          if (open) comment.expanded.add(id);
          else comment.expanded.delete(id);
        },
      },
    });

    /** 読み直して一覧まで描き直す */
    const reloadAndRefresh = async (): Promise<void> => {
      await loadReview();
      refreshComments();
    };

    /** 行の本文を直す。`toDetail` は詳細パネルから直したときに、描き直した後のフォーカスを移す先を渡す */
    const saveEdit = async (id: string, body: string, toDetail: (key: string) => void): Promise<void> => {
      const result = await api.update(id, { body });
      if (!result.ok) {
        // 断られた・届かない: 入力を残して理由を出す
        editError = result.detail ?? "サーバーが止まっています。立ち上げ直してから直してください。";
        editBody = body;
        refreshComments();
        toDetail(`edit:${id}`);
        return;
      }
      editing = null;
      editError = null;
      editBody = null;
      await reloadAndRefresh();
      toDetail(`edit-open:${id}`);
    };

    /** 行を消す（確認は挟まず、元の場所に「元に戻す」を出す） */
    const removeComment = async (id: string): Promise<void> => {
      const result = await api.remove(id);
      if (result.ok && result.data !== null) {
        const { count: _count, ...item } = result.data;
        comment.removed = [...comment.removed, item];
        comment.stale.delete(id);
      }
      await reloadAndRefresh();
    };

    /** 消した行を、同じ ID と日時で元の場所に戻す */
    const restoreComment = async (id: string): Promise<void> => {
      const item = comment.removed.find((entry) => entry.id === id);
      if (item === undefined) return;
      const result = await api.add({
        id: item.id,
        created: item.created,
        ...(item.target === null ? {} : { target: item.target }),
        ...(item.loc === null ? {} : { loc: item.loc }),
        ...(item.thread === null ? {} : { thread: item.thread }),
        body: item.body,
      });
      if (result.ok) comment.removed = comment.removed.filter((entry) => entry.id !== id);
      await reloadAndRefresh();
    };

    /** 詳細パネルの中の部品へフォーカスを移す（全画面のときは全画面の中） */
    const focusDetail = (key: string): void => {
      const host = route.full ? "dialog.full" : "aside.panel";
      document.querySelector<HTMLElement>(`${host} [data-focus="${key}"]`)?.focus();
    };

    /** 行の修正・書き換えを送る・キャンセル・削除・元に戻す。コメントの一覧（接頭辞は空）と詳細パネル（`detail-`）で同じ処理を使い、詳細パネルのときだけ、描き直した後のフォーカスを移す */
    const reviewRowHandlers = (focus: string): ReviewEditProps["on"] => {
      const toDetail = (key: string): void => {
        if (focus !== "") focusDetail(`${focus}${key}`);
      };
      return {
        edit: (id) => {
          editing = id;
          editingIn = focus === "" ? "list" : "detail";
          editError = null;
          editBody = null;
          refreshComments();
          toDetail(`edit:${id}`);
        },
        saveEdit: (id, body) => void saveEdit(id, body, toDetail),
        cancelEdit: () => {
          const canceled = editing;
          editing = null;
          editError = null;
          editBody = null;
          refreshComments();
          if (canceled !== null) toDetail(`edit-open:${canceled}`);
        },
        remove: (id) => void removeComment(id).then(() => toDetail(`restore:${id}`)),
        restore: (id) => void restoreComment(id).then(() => toDetail(`edit-open:${id}`)),
      };
    };

    /** 箇所が合わないコメントから箇所を外し、項目へのコメントにする */
    const detachLocation = async (id: string): Promise<void> => {
      const result = await api.update(id, { loc: null });
      if (result.ok) comment.stale.delete(id);
      await reloadAndRefresh();
    };

    /** チェックしたコメントを溜めた順にまとめて送る */
    const sendChecked = async (): Promise<void> => {
      const ids = comment.review.items
        .filter((item) => comment.checked.has(item.id) && !isBlockedReply(item, comment.threads))
        .map((item) => item.id);
      // 送るものが無い
      if (ids.length === 0) return;
      outcome = { kind: "sending" };
      renderComments();
      const result = await api.send(ids);
      if (result.ok && result.data !== null) {
        comment.removed = [];
        comment.stale = new Map();
        outcome = { kind: "sent", count: ids.length, at: result.data.sent, entered: result.data.entered };
      } else if (!result.ok && result.status === 409) {
        comment.stale = new Map(result.stale.map((entry) => [entry.id, entry.reason]));
        outcome = { kind: "stale", count: result.stale.length };
      } else {
        outcome = { kind: "failed", detail: result.ok ? null : result.detail };
      }
      await loadThreads();
      await reloadAndRefresh();
    };

    // ===== 選んだ箇所のコメントの入口 =====
    /** 出している入口 */
    let pill: HTMLElement | null = null;
    /** ポインターを押している間は入口を出さない（選び終えてから出す） */
    let pointerHeld = false;
    /** HTML の本文の枠の中で選んでいる範囲（選びを外すと null）。枠の文書の選択は親の文書の選択に入らないので別に持つ */
    let frameSelected: HtmlFrameSelection | null = null;

    /** 入口を閉じる */
    const closePill = (): void => {
      pill?.remove();
      pill = null;
    };

    /** 選んだ箇所と選んだ範囲の矩形の近くに入口を出す。押したら入力に箇所を添える */
    const openPill = ({ loc, anchor, host }: { loc: Location; anchor: { first: DOMRect; last: DOMRect }; host: HTMLElement }): void => {
      if (route.id === null) return;
      const id = route.id;
      // 上に収まるかを決めるため、本文のスクロール領域の矩形を渡す
      const scroller = host.querySelector<HTMLElement>(".panel-body") ?? host;
      pill = selectionComment({
        anchor,
        area: { viewport: { width: innerWidth, height: innerHeight }, scroller: scroller.getBoundingClientRect() },
        on: {
          press: () => {
            closePill();
            comment.pendingLoc.set(id, loc);
            redrawForm({ target: id, focus: true });
          },
          close: () => {
            closePill();
            host.querySelector<HTMLElement>(".md")?.focus();
          },
        },
      });
      // 全画面はモーダルなので、入口もその中に置く（外に置くと押せない）
      (host.matches("dialog") ? host : document.body).append(pill);
    };

    /** 図の拡大を開いている間か、詳細パネルの外か（入口を出さない場面） */
    const pillBlocked = (): boolean =>
      !serverMode || route.id === null || document.querySelector("dialog.viewer") !== null || fullViewer !== null;

    /** 選んだ範囲から箇所を求め、あれば入口を出し、無ければ閉じる。枠の中の選択が生きていて、親の文書の選択が空のときは、枠の入口をそのままにする */
    const updatePill = (): void => {
      const selection = getSelection();
      const parentSelected = selection !== null && selection.rangeCount > 0 && !selection.isCollapsed;
      if (!parentSelected && frameSelected !== null) return;
      closePill();
      const host = document.querySelector<HTMLElement>(route.full ? "dialog.full[open]" : "aside.panel");
      // 図の拡大を開いている間・選んだ範囲が無い・詳細パネル（全画面を開いている間は全画面）の外
      if (pillBlocked()) return;
      if (selection === null || selection.rangeCount === 0 || selection.isCollapsed || host === null) return;
      const range = selection.getRangeAt(0);
      if (!host.contains(range.commonAncestorContainer)) return;
      const loc = selectionLocation(range);
      const rects = range.getClientRects();
      const first = rects[0];
      const last = rects[rects.length - 1];
      if (loc === null || first === undefined || last === undefined) return;
      openPill({ loc, anchor: { first, last }, host });
    };

    /** HTML の本文の枠で文を選び終えた: 元の HTML の行の範囲の箇所にして入口を出す */
    const frameSelect = (selection: HtmlFrameSelection): void => {
      frameSelected = selection;
      closePill();
      const host = document.querySelector<HTMLElement>(route.full ? "dialog.full[open]" : "aside.panel");
      if (pillBlocked() || host === null) return;
      openPill({
        loc: { kind: "body", start: selection.start, end: selection.end, text: selection.text },
        anchor: selection.rects,
        host,
      });
    };

    /** HTML の本文の枠で選びを外した: 入口を閉じる */
    const frameClear = (): void => {
      frameSelected = null;
      closePill();
    };

    document.addEventListener("pointerdown", (event) => {
      pointerHeld = true;
      // 枠の外を押したら、枠の中の選択を外す（入口を押したときは外さない）
      if ((event.target as Element | null)?.closest?.(".selection-comment") === null || event.target === document) {
        for (const frame of document.querySelectorAll<HTMLIFrameElement>("iframe.html-frame")) {
          frame.contentWindow?.getSelection()?.removeAllRanges();
        }
      }
    });
    document.addEventListener("pointerup", () => {
      pointerHeld = false;
      window.setTimeout(updatePill, 0);
    });
    document.addEventListener("selectionchange", () => {
      if (!pointerHeld) updatePill();
    });

    // ===== 書き換えの知らせ =====
    /** 入力中の欄の選択とスクロールの位置を保って、渡した描き方で描き直す */
    const preserving = (draw: () => void): void => {
      const field = document.activeElement;
      const form = field instanceof HTMLTextAreaElement ? field.closest("form.send") : null;
      const inList = form !== null && form.closest(".comments-panel") !== null;
      const selection =
        field instanceof HTMLTextAreaElement && form !== null ? { start: field.selectionStart, end: field.selectionEnd } : null;
      const bodyFocused = field instanceof HTMLElement && field.matches(".panel-body");
      // 編集の表示・設定の画面の入力欄: 溜める前に打った値と選択を、描き直した後の同じ入力欄に戻す
      const typed =
        (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement) &&
        field.id !== "" &&
        field.closest(".pe-form") !== null
          ? field
          : null;
      const typedState =
        typed === null
          ? null
          : {
              id: typed.id,
              value: typed.value,
              start: typed instanceof HTMLSelectElement ? null : typed.selectionStart,
              end: typed instanceof HTMLSelectElement ? null : typed.selectionEnd,
            };
      // 全画面のときは詳細パネルも文書に残るので、今の画面の本文を引く
      const bodySelector = route.full ? "dialog.full .panel-body" : "aside.panel .panel-body";
      const panelScroll = document.querySelector<HTMLElement>(bodySelector)?.scrollTop ?? 0;
      const pageScroll = window.scrollY;
      draw();
      const panelBody = document.querySelector<HTMLElement>(bodySelector);
      if (panelBody !== null) panelBody.scrollTop = panelScroll;
      if (bodyFocused) panelBody?.focus({ preventScroll: true });
      window.scrollTo(0, pageScroll);
      if (typedState !== null) {
        const restored = document.getElementById(typedState.id);
        if (restored instanceof HTMLInputElement || restored instanceof HTMLTextAreaElement || restored instanceof HTMLSelectElement) {
          const text = !(restored instanceof HTMLInputElement) || !["checkbox", "radio"].includes(restored.type);
          if (text && restored.value !== typedState.value) restored.value = typedState.value;
          restored.focus({ preventScroll: true });
          // 選択を持てない型の入力欄（数・日付など）は、フォーカスだけを戻す
          try {
            if (!(restored instanceof HTMLSelectElement) && typedState.start !== null && typedState.end !== null) {
              restored.setSelectionRange(typedState.start, typedState.end);
            }
          } catch {
            // 選択を持てない型
          }
        }
      }
      if (selection !== null) {
        const restored = document.querySelector<HTMLTextAreaElement>(
          inList ? ".comments-panel form.send textarea" : route.full ? "dialog.full form.send textarea" : "aside.panel form.send textarea",
        );
        restored?.focus();
        restored?.setSelectionRange(selection.start, selection.end);
      }
    };

    /** 入力中の欄の選択とスクロールの位置を保って、画面を描き直す */
    const redrawKeepingState = (): void => preserving(() => render({ screen: true }));

    // ===== 表示の設定 =====
    /** 端末の上書きを変えた後に、残して読み分け直し、描き直す。開いている画面の種類を外したときは概要へ移る（履歴に積まない） */
    const changePrefs = ({ redrawMain }: { redrawMain: boolean }): void => {
      display.storageOk = persist();
      resolved = resolveDisplay(prefs, data.settings.display);
      const visible = visibleRoute(route);
      const moved = visible !== route;
      if (moved) {
        route = visible;
        navigate({ route: { ...route, filters: {} }, push: false });
      }
      if (redrawMain || moved) redrawKeepingState();
      else renderTop();
      renderSettings();
    };

    /** 表示の設定の中身の引数 */
    const settingsProps = (): SettingsPanelProps => ({
      look: resolved.look,
      defaultLook: resolved.defaultLook,
      kinds: resolved.kinds,
      defaultKinds: resolved.defaultKinds,
      counts: Object.fromEntries(KIND_KEYS.map((kind) => [kind, data[kind].length])),
      overrides: resolved.overrides,
      canSave: serverMode,
      minimap: resolved.minimap,
      bodyView: resolved.bodyView,
      message: display.message,
      storageOk: display.storageOk,
      onWorkspace: serverMode && point === null ? openWorkspace : null,
      on: {
        kinds: (kinds) => {
          prefs.kinds = kinds as Kind[];
          changePrefs({ redrawMain: true });
        },
        // 表示するは上書きを外し、表示しないだけを上書きとして残す。開いている詳細をその場で描き直す
        minimap: (shown) => {
          prefs.minimap = shown ? null : false;
          changePrefs({ redrawMain: true });
        },
        // 既定と違う値だけを上書きとして残し、開いている詳細をその場で描き直す
        bodyView: ({ key, value }) => {
          prefs[BODY_VIEW_PREF[key]] = (value === BODY_VIEW_DEFAULT[key] ? null : value) as never;
          changePrefs({ redrawMain: true });
        },
        reset: () => {
          // 見た目・表示する種類・ライト / ダーク・表の列・絞り込みの条件・差分のミニマップ・本文の表とセクションの見せ方・本文の差分の並べ方を全て外し、ワークスペースの既定の表示に戻す
          Object.assign(prefs, clearOverrides(prefs));
          clearTablePrefs();
          // 開いている画面は、画面の既定の条件で開き直す
          filterState.byTab = {};
          theme = systemTheme();
          document.documentElement.dataset["theme"] = theme;
          changePrefs({ redrawMain: true });
          document.querySelector<HTMLElement>('.settings-drawer [data-focus="over"]')?.focus();
        },
        save: openConfirm,
        close: closeSettings,
      },
    });

    /** 表示の設定のパネルを作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
    const renderSettings = (): void => {
      const current = document.querySelector<HTMLElement>(".settings-drawer");
      if (!display.open) {
        current?.remove();
        return;
      }
      const active = document.activeElement;
      const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
      const scroll = current?.querySelector<HTMLElement>(".st-wrap")?.scrollTop ?? 0;
      const next = settingsDrawer({ panel: settingsProps() });
      if (current === null) {
        document.body.append(next);
        requestAnimationFrame(() => next.classList.add("open"));
      } else {
        current.className = `${next.className} open`;
        current.replaceChildren(...next.children);
      }
      const panel = document.querySelector<HTMLElement>(".settings-drawer");
      const wrap = panel?.querySelector<HTMLElement>(".st-wrap");
      if (wrap !== null && wrap !== undefined) wrap.scrollTop = scroll;
      if (focusKey !== null) panel?.querySelector<HTMLElement>(`[data-focus="${focusKey}"]`)?.focus();
    };

    /** 表示の設定のパネルを開く。コメントの一覧と絞り込みのドロワーは閉じ、右の詳細パネルは開いたままにする（履歴に積まない） */
    const openSettings = (): void => {
      if (comment.listOpen) {
        flushDrafts();
        comment.listOpen = false;
        comment.opened = null;
        comment.highlight = null;
        comment.removed = [];
        comment.expanded.clear();
        renderComments();
        if (discardListEdit()) renderDetail();
      }
      editState.open = false;
      renderPending();
      display.open = true;
      stack.front = "left";
      if (filterState.drawerOpen) {
        filterState.drawerOpen = false;
        redrawKeepingState();
      } else {
        renderTop();
      }
      renderSettings();
      scheduleInert();
    };

    /** 表示の設定のパネルを閉じ、トップバーのボタンへフォーカスを戻す */
    const closeSettings = (): void => {
      display.open = false;
      renderTop();
      renderSettings();
      scheduleInert();
      document.querySelector<HTMLElement>("[data-act='settings']")?.focus();
    };

    // ===== ワークスペースの既定の保存 =====
    /** 既定の保存の確かめを今の状態で描く（開き直して、最初のフォーカスを取り消すに置く） */
    const renderConfirm = (): void => {
      const old = document.querySelector<HTMLDialogElement>("dialog.sconfirm");
      old?.close();
      old?.remove();
      if (display.confirm === null) return;
      const dialog = settingsConfirm({
        from: { look: resolved.defaultLook, kinds: resolved.defaultKinds },
        to: { look: resolved.look, kinds: resolved.kinds },
        busy: display.confirm.busy,
        error: display.confirm.error,
        on: { save: () => void saveDefault(), cancel: closeConfirm },
      });
      document.body.append(dialog);
      dialog.showModal();
    };

    /** 確かめを開く */
    const openConfirm = (): void => {
      display.confirm = { busy: false, error: null };
      renderConfirm();
    };

    /** 何も書かずに確かめを閉じ、「ワークスペースの既定にする」へフォーカスを戻す */
    const closeConfirm = (): void => {
      display.confirm = null;
      renderConfirm();
      document.querySelector<HTMLElement>('.settings-drawer [data-focus="save"]')?.focus();
    };

    /** 今当てている見た目と表示する種類を、ワークスペースの既定として保存する */
    const saveDefault = async (): Promise<void> => {
      if (display.confirm === null) return;
      display.confirm = { busy: true, error: null };
      renderConfirm();
      const result = await putDisplay({
        network_look: resolved.look,
        visible_kinds: KIND_KEYS.filter((kind) => resolved.kinds.has(kind)),
      });
      if (!result.ok) {
        // 断られた・届かない: 確かめの中に理由を出し、config.yaml と画面の表示は保存の前のまま
        display.confirm = {
          busy: false,
          error:
            result.detail === null
              ? "保存できませんでした。サーバーが止まっています。起動スクリプトで立ち上げ直し、示された新しい URL で開いてから保存してください。"
              : `保存できませんでした。${result.detail}`,
        };
        renderConfirm();
        return;
      }
      // 書けた: 返った既定を記録に入れ、個人の上書きはそのまま残す
      const saved = result.data?.display ?? { network_look: resolved.look, visible_kinds: KIND_KEYS.filter((kind) => resolved.kinds.has(kind)) };
      serverData = { ...serverData, settings: { ...serverData.settings, display: saved } };
      rebuildIndex();
      display.savedDisplay = saved;
      display.message = { kind: "ok", text: `ワークスペースの既定にしました（${formatJst(new Date().toISOString())}）。` };
      display.confirm = null;
      renderConfirm();
      resolved = resolveDisplay(prefs, data.settings.display);
      redrawKeepingState();
      renderSettings();
      document.querySelector<HTMLElement>('.settings-drawer [data-focus="same"]')?.focus();
    };

    // ===== 編集と保存待ち（サーバーの配信だけ） =====
    const editsApi = editApi();

    /** 追加する項目の入力（仮の ID を振られるまで、タイトルを書く前の入力を持つ） */
    let addDraft: Record<string, unknown> = {};

    /** 直前の保存をサーバーが断った理由（保存待ちのパネルに出す）。次に保存するか、編集を取り消すまで残す */
    let rejected: string | null = null;

    /** 幅 900px 以下で保存待ちのパネルから項目を開いたとき、詳細パネルを閉じたらパネルを開き直すか */
    let reopenPending = false;

    /** 保存待ちの編集を読み直す。読めたときだけ置き換え、書き込めなかった編集の控えは今の編集に残る分だけにする */
    const loadEdits = async (): Promise<void> => {
      const result = await editsApi.read();
      if (!result.ok || result.data === null) return;
      editState.edits = result.data.items;
      const ids = new Set(editState.edits.map((entry) => entry.id));
      editState.blocked = editState.blocked.filter((entry) => ids.has(entry.id));
    };

    /** 書き込めなかった編集の ID */
    const blockedIds = (): Set<string> => new Set(editState.blocked.map((entry) => entry.id));

    /** 保存待ちの編集がある項目の印（項目の ID・仮の ID → 印の種類） */
    const editMarks = (): Record<string, PendingMarkKind> => {
      const blocked = blockedIds();
      const marks: Record<string, PendingMarkKind> = {};
      for (const target of new Set(editState.edits.map((entry) => entry.target))) {
        const mark = pendingMarkOf({ edits: editState.edits, blocked, target });
        if (mark !== null) marks[target] = mark;
      }
      return marks;
    };

    /** 追加する項目の編集を、一覧の画面に渡す項目にする（`id` は仮の ID） */
    const addedItem = (entry: PendingEdit): Item =>
      ({ id: entry.target, title: "", created: entry.created, updated: entry.created, ...(entry.value as object) }) as Item;

    /** 一覧の画面に渡す編集の入口。配る書き出しと差分の表示中は null */
    const screenEdit = (kind: Kind): ScreenEdit | null => {
      if (!serverMode || point !== null) return null;
      return {
        marks: editMarks(),
        adds: editState.edits.filter((entry) => entry.op === "item-add" && entry.key === kind).map(addedItem),
        onAdd: () => startAdd(kind),
      };
    };

    /** 編集が指す、項目のキーか案の記号（項目の追加・削除と設定は持たない） */
    const keyOf = (entry: PendingEdit): string | null => {
      if (entry.op === "adopt") return typeof entry.value === "string" ? entry.value : entry.key;
      if (entry.op === "item-add" || entry.op === "item-remove" || entry.op === "setting") return null;
      return entry.key;
    };

    /** 項目のキー・案の記号 → 印の種類。項目の ID には項目の印 */
    const keyMarks = (id: string): Record<string, PendingMarkKind> => {
      const blocked = blockedIds();
      const marks: Record<string, PendingMarkKind> = {};
      const own = pendingMarkOf({ edits: editState.edits, blocked, target: id });
      if (own !== null) marks[id] = own;
      for (const entry of editState.edits.filter((other) => other.target === id)) {
        const key = keyOf(entry);
        if (key === null) continue;
        const mark = pendingMarkOf({ edits: editState.edits, blocked, target: id, key });
        if (mark !== null) marks[key] = mark;
      }
      return marks;
    };

    /** 項目のキー・案の記号 → 直前の保存で書き込めなかった編集 */
    const blockedByKey = (id: string): Record<string, BlockedEdit> => {
      const byId = new Map(editState.blocked.map((entry) => [entry.id, entry]));
      const result: Record<string, BlockedEdit> = {};
      for (const entry of editState.edits) {
        const blocked = byId.get(entry.id);
        const key = keyOf(entry);
        if (entry.target === id && blocked !== undefined && key !== null) result[key] = blocked;
      }
      return result;
    };

    /** 向け先の、キー → 溜められなかった理由 */
    const formErrors = (target: string): Record<string, string> => {
      const prefix = `${target}:`;
      return Object.fromEntries(
        [...editState.errors].filter(([key]) => key.startsWith(prefix)).map(([key, text]) => [key.slice(prefix.length), text]),
      );
    };

    /** 溜められなかった理由の文（届かないとき・断られたとき） */
    const failureText = (result: { status: number | null; detail: string | null }): string =>
      result.status === null
        ? "サーバーにつながらないため、溜められませんでした。"
        : `溜められませんでした。${result.detail ?? ""}`;

    /** 編集を溜めた後の描き直し（入力中の欄・スクロールの位置を保つ。ネットワークは作り直さない） */
    const redrawEdit = (): void => preserving(() => render({ screen: route.tab !== "graph" }));

    /** 編集 1 件を溜める。溜められたら保存待ちの編集を読み直して描き直し、断られた・届かないときは入力を残して理由を持つ。溜められたときは返った結果を返す */
    const submitEdit = async ({
      payload,
      error,
      after,
    }: {
      payload: { target?: string; op: PendingEdit["op"]; key?: string; value?: unknown; map?: Record<string, string | null> };
      /** 理由を出すキー */
      error: { target: string; key: string };
      /** 溜められた後、描き直す前にすること */
      after?: (result: { target: string }) => void;
    }): Promise<{ id: string | null; target: string; count: number } | null> => {
      const errorKey = `${error.target}:${error.key}`;
      const result = await editsApi.add(payload);
      if (!result.ok || result.data === null) {
        editState.errors.set(errorKey, result.ok ? "溜められませんでした。" : failureText(result));
        redrawEdit();
        return null;
      }
      editState.errors.delete(errorKey);
      await loadEdits();
      after?.(result.data);
      rebuildIndex();
      redrawEdit();
      return result.data;
    };

    /** 案の編集の理由は、案の入力の下にまとめて出す */
    const errorKeyOf = (input: { op: PendingEdit["op"]; key?: string }): string =>
      ["option-add", "option-edit", "option-remove", "adopt"].includes(input.op) ? "options" : (input.key ?? "");

    /** 項目の削除の編集を外す */
    const cancelRemoval = async (id: string): Promise<void> => {
      const found = editState.edits.find((entry) => entry.target === id && entry.op === "item-remove");
      if (found !== undefined) await undoEdit(found.id);
    };

    /** 編集 1 件を保存待ちから外す。外したら、書き込めなかった編集の控えからも外す */
    const undoEdit = async (id: string): Promise<void> => {
      const result = await editsApi.remove(id);
      if (!result.ok) {
        if (result.status === null) editState.status = "offline";
        renderPending();
        return;
      }
      const gone = new Set(result.data?.removed ?? [id]);
      editState.blocked = editState.blocked.filter((entry) => !gone.has(entry.id));
      if (editState.blocked.length === 0 && editState.status === "idle") rejected = null;
      await loadEdits();
      rebuildIndex();
      redrawEdit();
    };

    /** 詳細パネルの編集の表示の引数 */
    const editFormProps = ({ id, kind, item }: { id: string; kind: Kind; item: Item }): DetailEditFormProps => {
      const own = editState.edits.filter((entry) => entry.target === id);
      return {
        kind,
        item,
        settings: index.data.settings,
        marks: keyMarks(id),
        removing: own.some((entry) => entry.op === "item-remove"),
        removedOptions: own.filter((entry) => entry.op === "option-remove").map((entry) => entry.key ?? ""),
        blocked: blockedByKey(id),
        referrers: serverIndex.referencedBy.get(id) ?? [],
        errors: formErrors(id),
        body: index.data.bodies[item.body ?? ""] ?? "",
        on: {
          change: (input) =>
            void submitEdit({ payload: { target: id, ...input }, error: { target: id, key: errorKeyOf(input) } }),
          remove: () => void submitEdit({ payload: { target: id, op: "item-remove" }, error: { target: id, key: "" } }),
          cancelRemove: () => void cancelRemoval(id),
        },
      };
    };

    /** 詳細パネルの編集の入口。配る書き出し・差分の表示中は null */
    const detailEdit = (): DetailEdit | null => {
      if (!serverMode || point !== null || route.id === null) return null;
      const id = route.id;
      const entry = index.byId.get(id);
      if (entry === undefined) return null;
      return {
        editing: editState.editing === id,
        marks: keyMarks(id),
        form: editFormProps({ id, kind: entry.kind, item: entry.item }),
        onToggle: () => toggleEdit(id),
      };
    };

    /** 「編集する」「編集を終える」。編集の表示にしたときは最初の入力欄へ、読む表示に戻したときは「編集する」へフォーカスを移す */
    const toggleEdit = (id: string): void => {
      editState.editing = editState.editing === id ? null : id;
      redrawEdit();
      const host = route.full ? "dialog.full" : "aside.panel";
      if (editState.editing === id) document.querySelector<HTMLElement>(`${host} [data-first]`)?.focus();
      else document.querySelector<HTMLElement>(`${host} [data-act="edit"]`)?.focus();
    };

    // ----- 項目を追加する入力 -----
    /** 項目を追加する入力を開いているか（タイトルを書く前の入力と、仮の ID を振られた項目の入力） */
    const isAdding = (): boolean =>
      serverMode && point === null && (editState.adding !== null || (editState.editing?.startsWith(NEW_ID_PREFIX) ?? false));

    /** 追加する入力の項目の種類 */
    const addingKind = (): Kind | null => {
      if (editState.adding !== null) return editState.adding;
      const entry = editState.edits.find((other) => other.op === "item-add" && other.target === editState.editing);
      return entry === undefined ? null : ((entry.key ?? "") as Kind);
    };

    /** 今日の日付（JST の `YYYY-MM-DD`。会話ログの日付の初期値） */
    const todayJst = (): string => new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });

    /** 設定の画面と追加の入力を閉じる（画面・項目を移るとき） */
    const leaveEditViews = (): void => {
      editState.workspaceOpen = false;
      if (editState.adding !== null || editState.editing?.startsWith(NEW_ID_PREFIX) === true) {
        editState.adding = null;
        editState.editing = null;
        addDraft = {};
      }
    };

    /** 追加の入力の最初の入力欄（タイトル）へフォーカスを移す */
    const focusAddInput = (): void => document.querySelector<HTMLElement>("aside.pe-add-panel [data-first]")?.focus();

    /** 「項目を追加」。開いていた詳細パネルを閉じ、空の項目の入力を詳細パネルと同じ置き方で開く */
    const startAdd = (kind: Kind): void => {
      flushDrafts();
      editState.workspaceOpen = false;
      editState.adding = kind;
      editState.editing = null;
      addDraft = {};
      if (route.id !== null) {
        route = { ...route, id: null, full: false, filters: {}, heading: null };
        navigate({ route, push: false });
      }
      redrawEdit();
      focusAddInput();
    };

    /** 追加する項目（仮の ID）を、追加の入力で開く */
    const openAdded = (target: string): void => {
      flushDrafts();
      editState.workspaceOpen = false;
      editState.adding = null;
      editState.editing = target;
      if (route.id !== null) {
        route = { ...route, id: null, full: false, filters: {}, heading: null };
        navigate({ route, push: false });
      }
      redrawEdit();
      focusAddInput();
    };

    /** 追加の入力を閉じる。タイトルを書いていなければ何も溜めていない */
    const closeAdd = (): void => {
      editState.adding = null;
      editState.editing = null;
      addDraft = {};
      redrawEdit();
      reopenPendingPanel();
    };

    /** 追加の入力でキーを書いたとき。タイトルを書くまでは溜めず、書いたら `item-add` を溜め（返った仮の ID を `editing` に入れる）、続くキーは同じ `item-add` の `value` を送り直す */
    const submitAddField = async ({ kind, input }: { kind: Kind; input: EditInput }): Promise<void> => {
      const entry = editState.edits.find((other) => other.op === "item-add" && other.target === editState.editing);
      const next: Record<string, unknown> =
        entry === undefined
          ? { ...addDefaults({ kind, today: todayJst() }), ...addDraft }
          : { ...(entry.value as Record<string, unknown>) };
      if (input.value === null) delete next[input.key];
      else next[input.key] = input.value;
      if (entry === undefined) {
        addDraft = next;
        const title = next["title"];
        // タイトルを書くまでは溜めない
        if (typeof title !== "string" || title.trim() === "") return;
      }
      await submitEdit({
        payload: { ...(entry === undefined ? {} : { target: entry.target }), op: "item-add", key: kind, value: next },
        error: { target: entry?.target ?? NEW_ID_PREFIX, key: input.key },
        after: (result) => {
          if (entry !== undefined) return;
          editState.editing = result.target;
          editState.adding = null;
          addDraft = {};
        },
      });
    };

    /** 追加の入力のパネルを描く（詳細パネルと同じ形と置き場所） */
    const renderAddPanel = (): void => {
      const kind = addingKind();
      if (kind === null) return;
      const entry = editState.edits.find((other) => other.op === "item-add" && other.target === editState.editing);
      const item =
        entry === undefined
          ? ({ id: NEW_ID_PREFIX, title: "", created: "", updated: "", ...addDefaults({ kind, today: todayJst() }), ...addDraft } as unknown as Item)
          : addedItem(entry);
      const record = item as unknown as Record<string, unknown>;
      const form = detailEditForm({
        kind,
        item,
        settings: index.data.settings,
        marks: entry === undefined ? {} : keyMarks(item.id),
        removing: false,
        removedOptions: [],
        blocked: entry === undefined ? {} : blockedByKey(item.id),
        referrers: [],
        errors: formErrors(entry === undefined ? NEW_ID_PREFIX : item.id),
        body: typeof record["body"] === "string" ? record["body"] : "",
        on: { change: (input) => void submitAddField({ kind, input }), remove: () => undefined, cancelRemove: () => undefined },
      });
      const body = h({
        tag: "div",
        attrs: { class: "panel-body", tabindex: "0", role: "region", "aria-label": "追加する項目の入力" },
        children: [form],
      });
      const panel = h({
        tag: "aside",
        attrs: { class: "panel open pe-add-panel pe-editing", "aria-label": `${KIND_LABEL[kind]}を追加` },
        children: [
          h({
            tag: "div",
            attrs: { class: "panel-head" },
            children: [
              h({
                tag: "button",
                attrs: { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: closeAdd },
                children: [icon("back")],
              }),
              h({
                tag: "span",
                attrs: { class: "panel-kind" },
                children: [h({ tag: "span", attrs: { class: "panel-kind-label" }, children: [`${KIND_LABEL[kind]}を追加`] })],
              }),
              h({ tag: "span", attrs: { class: "spacer" } }),
              h({
                tag: "button",
                attrs: { class: "icon-btn panel-close-x", type: "button", "aria-label": "追加の入力を閉じる", onclick: closeAdd },
                children: [icon("x")],
              }),
            ],
          }),
          diffMinimapFrame({ body, shown: false }),
        ],
      });
      const current = document.querySelector<HTMLElement>("aside.pe-add-panel");
      if (current === null) {
        document.body.append(panel);
      } else {
        current.className = panel.className;
        current.setAttribute("aria-label", panel.getAttribute("aria-label") ?? "");
        current.replaceChildren(...panel.children);
      }
    };

    // ----- 保存待ちのパネル -----
    /** 保存待ちのパネルの引数 */
    const pendingProps = (): PendingEditsPanelProps => ({
      edits: editState.edits,
      blocked: editState.blocked,
      index: serverIndex,
      status: editState.status,
      rejected,
      on: {
        close: closePending,
        open: openPendingTarget,
        undo: (id) => void undoFromPanel(id),
        save: () => void saveEdits(),
      },
    });

    /** 保存待ちのパネルを作り直す（描き直しても、操作していた部品へフォーカスを戻す） */
    const renderPending = (): void => {
      const current = document.querySelector<HTMLElement>(".pending-panel");
      if (!editState.open || point !== null || !serverMode) {
        current?.remove();
        return;
      }
      const active = document.activeElement;
      const focusKey = active instanceof HTMLElement && current?.contains(active) === true ? (active.dataset["focus"] ?? null) : null;
      const scroll = current?.querySelector<HTMLElement>(".comments-body")?.scrollTop ?? 0;
      const next = pendingEditsPanel(pendingProps());
      if (current === null) {
        document.body.append(next);
        // 開いた状態にしてから見出しへフォーカスを移す（閉じている間は隠れていて、フォーカスを受けない）
        requestAnimationFrame(() => {
          next.classList.add("open");
          next.querySelector<HTMLElement>("h2")?.focus();
        });
      } else {
        current.className = `${next.className} open`;
        current.replaceChildren(...next.children);
      }
      const panel = document.querySelector<HTMLElement>(".pending-panel");
      const body = panel?.querySelector<HTMLElement>(".comments-body");
      if (body !== null && body !== undefined) body.scrollTop = scroll;
      if (focusKey !== null) panel?.querySelector<HTMLElement>(`[data-focus="${focusKey}"]`)?.focus();
    };

    /** 保存待ちのパネルを開く・閉じる。開くときはコメントの一覧・表示の設定・絞り込みのドロワーを閉じる */
    const togglePending = (): void => {
      if (editState.open) {
        closePending();
        return;
      }
      if (comment.listOpen) closeList();
      if (display.open) {
        display.open = false;
        renderSettings();
      }
      if (filterState.drawerOpen) filterState.drawerOpen = false;
      editState.open = true;
      stack.front = "left";
      reopenPending = false;
      redrawKeepingState();
    };

    /** 保存待ちのパネルを閉じ、トップバーの保存待ちのボタンへフォーカスを戻す（保存待ちの編集は残る） */
    const closePending = (): void => {
      editState.open = false;
      reopenPending = false;
      renderTop();
      renderPending();
      scheduleInert();
      document.querySelector<HTMLElement>("[data-act='pending']")?.focus();
    };

    /** 幅 900px 以下で保存待ちのパネルから開いた項目の詳細パネルを閉じたら、保存待ちのパネルを開き直す */
    const reopenPendingPanel = (): void => {
      if (!reopenPending || route.id !== null || isAdding()) return;
      reopenPending = false;
      editState.open = true;
      stack.front = "left";
      renderTop();
      renderPending();
      scheduleInert();
    };

    /** 保存待ちのパネルのまとまりの項目を開く。項目は詳細パネルを編集の表示で、追加する項目は追加の入力で、設定は設定の画面で開く（幅 900px 以下ではパネルを閉じ、詳細パネルを閉じたら開き直す） */
    const openPendingTarget = (target: string): void => {
      if (isNarrow()) {
        editState.open = false;
        reopenPending = true;
      }
      if (target === SETTINGS_TARGET) {
        openWorkspace();
        return;
      }
      if (target.startsWith(NEW_ID_PREFIX)) {
        openAdded(target);
        return;
      }
      editState.editing = target;
      stack.front = "detail";
      if (route.id === target) redrawEdit();
      else openItem(target, false);
      document.querySelector<HTMLElement>(`${route.full ? "dialog.full" : "aside.panel"} [data-first]`)?.focus();
    };

    /** パネルの「取り消す」。外した後は次の行の取り消すボタン（無ければ見出し）へフォーカスを移す */
    const undoFromPanel = async (id: string): Promise<void> => {
      const before = [...document.querySelectorAll<HTMLElement>(".pending-panel .pe-undo")];
      const at = before.findIndex((button) => button.dataset["focus"] === `undo:${id}`);
      await undoEdit(id);
      const after = [...document.querySelectorAll<HTMLElement>(".pending-panel .pe-undo")];
      (after[at] ?? after[at - 1] ?? document.querySelector<HTMLElement>(".pending-panel h2"))?.focus();
    };

    /** 保存待ちの編集をまとめて保存する。全て書けたらパネルを閉じて知らせを出し、書き込めない編集があれば何も保存せずにその旨を出し、届かなければ `offline` にする */
    const saveEdits = async (): Promise<void> => {
      if (editState.edits.length === 0 || editState.status === "saving") return;
      const count = editState.edits.length;
      editState.status = "saving";
      rejected = null;
      renderPending();
      const result = await editsApi.save();
      if (result.ok) {
        editState.blocked = [];
        editState.open = false;
        editState.editing = null;
        editState.adding = null;
        editState.errors.clear();
        editState.status = "idle";
        editState.toast = `${count} 件を保存しました。`;
        await reload();
        showSavedNotice(count);
        return;
      }
      if (result.status === 409 && result.blocked !== undefined) {
        editState.blocked = result.blocked;
        editState.status = "idle";
        editState.open = true;
        redrawEdit();
        document.querySelector<HTMLElement>('.pending-panel [data-focus="alert"]')?.focus();
        return;
      }
      // 届かない: 保存待ちの編集は残し、次に保存するまで `offline` のままにする。断られた: その理由を出す
      editState.status = result.status === null ? "offline" : "idle";
      if (result.status !== null) rejected = result.detail ?? "";
      editState.open = true;
      redrawEdit();
      document.querySelector<HTMLElement>('.pending-panel [data-focus="alert"]')?.focus();
    };

    /** 保存した知らせを画面の下に出し、`SAVED_NOTICE_MS` 経ったら消す */
    const showSavedNotice = (count: number): void => {
      document.querySelector(".pe-toast")?.remove();
      const notice = savedNotice({ count });
      document.body.append(notice);
      window.setTimeout(() => {
        notice.remove();
        editState.toast = null;
      }, SAVED_NOTICE_MS);
    };

    // ----- 設定の画面 -----
    /** 設定の画面の引数 */
    const workspaceProps = (): WorkspaceSettingsProps => {
      const blocked = blockedIds();
      const marks: Record<string, PendingMarkKind> = {};
      for (const entry of editState.edits) {
        if (entry.target !== SETTINGS_TARGET || entry.key === null) continue;
        const mark = pendingMarkOf({ edits: editState.edits, blocked, target: SETTINGS_TARGET, key: entry.key });
        if (mark !== null) marks[entry.key] = mark;
      }
      return {
        settings: index.data.settings,
        index,
        marks,
        errors: formErrors(SETTINGS_TARGET),
        threads: comment.threads,
        on: {
          change: (input) =>
            void submitEdit({
              payload: { op: "setting", ...input },
              error: { target: SETTINGS_TARGET, key: input.key },
            }),
          close: closeWorkspace,
        },
      };
    };

    /** 設定の画面を描く（開いている間は本文の区画を置き換える）。閉じている間は作らない */
    const renderWorkspace = (): void => {
      const current = document.querySelector<HTMLElement>(".pe-ws");
      const show = serverMode && point === null && editState.workspaceOpen;
      main.hidden = show;
      if (!show) {
        current?.remove();
        return;
      }
      const next = workspaceSettings(workspaceProps());
      if (current === null) main.after(next);
      else current.replaceWith(next);
    };

    /** 表示の設定のパネルの「設定を編集する」。表示の設定は閉じ、設定の画面を開く（幅 900px 以下では保存待ちのパネルも閉じる） */
    const openWorkspace = (): void => {
      display.open = false;
      renderSettings();
      if (isNarrow()) editState.open = false;
      editState.workspaceOpen = true;
      editState.editing = null;
      redrawKeepingState();
      document.querySelector<HTMLElement>(".pe-ws h1")?.focus();
    };

    /** 設定の画面を閉じ、開く前の画面へ戻る（溜めた編集は保存待ちに残る） */
    const closeWorkspace = (): void => {
      editState.workspaceOpen = false;
      redrawKeepingState();
      document.querySelector<HTMLElement>("[data-act='settings']")?.focus();
    };

    // ===== 変更履歴と差分の表示 =====
    /** 選んだ時点を変えて残し、どの画面もその時点の差分の表示で描き直す（記録は読み直さず、履歴に積まない）。null は差分の表示をやめる */
    const selectPoint = (sel: string | null): void => {
      prefs.diffSel = sel;
      persist();
      point = resolveDiffPoint(data.changes, sel, since);
      syncEditView();
      // 選んだ時点を共有できるよう、履歴に積まずにハッシュへ書く
      route = { ...route, diff: sel };
      navigate({ route: { ...route, filters: {} }, push: false });
      redrawKeepingState();
    };

    /** 本文・書き込みのまとまりのリンクを押した: 記録にあるまとまりのときだけ、変更履歴で選んだときと同じに切り替える */
    const openChangeSet = (id: string): void => {
      if (resolveDiffPoint(data.changes, id, since) !== null) selectPoint(id);
    };

    /** 変更履歴のモーダルを開く（開いているときは何もしない） */
    const openHistory = (): void => {
      if (document.querySelector("dialog.hist") !== null) return;
      const dialog = historyDialog({
        points: historyPoints({ changes: data.changes, since }),
        current: point?.sel ?? "",
        onPick: (sel) => selectPoint(sel === "" ? null : sel),
        // 選ばずに閉じたときも、選んだときも、「変更履歴」のボタンへフォーカスを戻す
        onClose: () => document.querySelector<HTMLElement>("[data-act='hist']")?.focus(),
      });
      document.body.append(dialog);
      dialog.showModal();
    };

    /** 記録を読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
    const reload = async (): Promise<void> => {
      const result = await fetchRecords();
      if (!result.ok) return;
      await loadReview();
      await loadThreads();
      await loadEdits();
      const previousDisplay = serverData.settings.display;
      serverData = result.data;
      rebuildIndex();
      // ロックした項目が無くなっていれば、ロックを外す
      if (lockState.graph !== null && !index.byId.has(lockState.graph)) lockState.graph = null;
      if (lockState.map !== null && index.byId.get(lockState.map)?.kind !== "decisions") lockState.map = null;
      // 表示の既定が変わった: 上書きを持たない項目に新しい既定を当て、知らせる（自分が既定にした直後の知らせは出さない）
      if (display.savedDisplay !== null && sameDisplay(display.savedDisplay, data.settings.display)) {
        display.savedDisplay = null;
      } else if (!sameDisplay(previousDisplay, data.settings.display)) {
        display.savedDisplay = null;
        settingsNotice({ durationMs: NOTICE_MS });
        display.message = { kind: "info", text: `ワークスペースの既定が変わりました（${formatJst(new Date().toISOString())}）。` };
      }
      resolved = resolveDisplay(prefs, data.settings.display);
      // 開いていた画面の種類が表示しない種類になった: 概要へ移る
      const visible = visibleRoute(route);
      if (visible !== route) {
        route = visible;
        navigate({ route: { ...route, filters: {} }, push: false });
      }
      // 選んだ時点と「前回開いてから」の始まりは保ち、新しい記録で印を引き直す
      point = resolveDiffPoint(data.changes, prefs.diffSel ?? null, since);
      // 選んだ時点が引けなくなった（まとまりが消えた・まだまとめていない変更が空になった）: 差分を出さず、ハッシュからも外す
      if (point === null && route.diff !== null) {
        prefs.diffSel = null;
        persist();
        route = { ...route, diff: null };
        navigate({ route: { ...route, filters: {} }, push: false });
      }
      // 差分の表示に移っていれば保存待ちの編集は当てず、そうでなければ当て直す
      syncEditView();
      document.title = `${data.settings.summary} | mindstella`;
      // 開いていた項目が消えた: 詳細パネルを閉じる
      if (route.id !== null && !index.byId.has(route.id)) {
        route = { ...route, id: null, full: false, filters: {}, heading: null };
        navigate({ route, push: false });
      }
      redrawKeepingState();
      renderComments();
      renderSettings();
    };

    // ===== 操作と履歴 =====
    /** コメントの一覧の Esc。入力欄に打っている間は入力欄から外れるだけにし（パネルは動かさない）、スレッド・レビュー中の書き込みの画面では戻り、一覧ならパネルを閉じる */
    const closeListByEscape = (): void => {
      const active = document.activeElement;
      if (isTyping(active)) {
        if (active instanceof HTMLElement) active.blur();
      } else if (comment.view === "list") {
        closeList();
      } else {
        goBack();
      }
    };

    document.addEventListener("keydown", (event) => {
      // L: ネットワークで、詳細を開いている項目をもう一度押したのと同じ規則でロックを付け外しする。修飾キーがあるとき・変換中・入力欄にフォーカスがあるとき・重ねる面を開いているときは受けない
      if (
        event.key.toLowerCase() === "l" &&
        !event.ctrlKey &&
        !event.altKey &&
        !event.metaKey &&
        !event.isComposing &&
        !isTyping(document.activeElement) &&
        document.querySelector("dialog[open]") === null &&
        document.querySelector(":popover-open") === null &&
        matchMedia(LOCK_QUERY).matches &&
        route.tab === "graph" &&
        route.id !== null
      ) {
        if (lockPress({ key: "graph", pressed: route.id }) === "shake") shakeGraphKey();
      }
      // Ctrl+K（macOS は Cmd+K）で全体の検索を開く。入力欄に入力中でも開き、開いているときは検索の言葉を選び直す
      if ((event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const opened = document.querySelector<HTMLInputElement>("dialog.search input");
        if (opened !== null) opened.select();
        else openSearch();
      }
      // Esc: 幅 900px 以下で左のパネルを前に出しているときは、その左のパネルから閉じる（詳細パネルは閉じない）。重ねる面が無いときは、詳細パネルを閉じる
      if (
        event.key === "Escape" &&
        isLeftFront() &&
        document.querySelector("dialog[open]:not(.drawer)") === null &&
        document.querySelector(":popover-open") === null
      ) {
        if (filterState.drawerOpen) closeDrawer();
        else if (comment.listOpen) closeListByEscape();
        else if (editState.open) closePending();
        else closeSettings();
      } else if (
        event.key === "Escape" &&
        route.id !== null &&
        !route.full &&
        document.querySelector("dialog[open]:not(.drawer)") === null &&
        document.querySelector(":popover-open") === null
      ) {
        closeDetail();
      } else if (
        event.key === "Escape" &&
        route.id === null &&
        comment.listOpen &&
        document.querySelector("dialog[open]:not(.drawer)") === null &&
        document.querySelector(":popover-open") === null
      ) {
        closeListByEscape();
      } else if (
        event.key === "Escape" &&
        route.id === null &&
        editState.open &&
        document.querySelector("dialog[open]:not(.drawer)") === null &&
        document.querySelector(":popover-open") === null
      ) {
        closePending();
      } else if (
        event.key === "Escape" &&
        isAdding() &&
        document.querySelector("dialog[open]:not(.drawer)") === null &&
        document.querySelector(":popover-open") === null
      ) {
        // 入力欄に打っている間は入力欄から外れるだけにし、追加の入力は閉じない
        if (isTyping(document.activeElement)) (document.activeElement as HTMLElement).blur();
        else closeAdd();
      } else if (
        event.key === "Escape" &&
        route.id === null &&
        display.open &&
        document.querySelector("dialog[open]") === null &&
        document.querySelector(":popover-open") === null
      ) {
        closeSettings();
      }
    });
    /** ハッシュが変わったとき（戻る・進む・手で書き換えた）、その画面を描く */
    const onLocationChange = (): void => {
      const parsed = parseHash({ hash: location.hash, index });
      const visible = visibleRoute(parsed);
      // 差分の時点を引き直し、引けた時点に揃える
      const settled = settleDiffPoint(visible);
      const next = settled.route;
      point = settled.point;
      syncEditView();
      // 表示しない種類のタブを指していた・時点が引けなかった: ハッシュを置き換える
      if (visible !== parsed || next.diff !== parsed.diff) navigate({ route: { ...next, filters: {} }, push: false });
      // 画面・表示形式・項目・差分の時点が同じで絞り込み（`f.{列}`）も無いときは、描き直さない。絞り込みだけを足したハッシュは、開き直しとして使う
      if (toHash(next) === toHash(route) && Object.keys(next.filters).length === 0) return;
      leaveEditViews();
      const screen =
        next.tab !== route.tab ||
        next.view !== route.view ||
        next.diff !== route.diff ||
        Object.keys(next.filters).length > 0 ||
        (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
      route = next;
      render({ screen });
      reopenPendingPanel();
      // 絞り込みは画面に渡した後、ハッシュから消す（残すと、次のハッシュの変化で使い回される）
      if (Object.keys(next.filters).length > 0) navigate({ route: { ...route, filters: {} }, push: false });
    };
    addEventListener("popstate", onLocationChange);
    addEventListener("hashchange", onLocationChange);

    // ===== 最初の描き =====
    // サーバーの配信では、レビュー中のコメントと書きかけを読んでおく（コメントのボタンの件数と入力に使う）
    if (serverMode) {
      await loadReview(true);
      await loadThreads();
      await loadEdits();
      syncEditView();
    }
    // 記録に無い項目を指すハッシュは、項目の無いハッシュに置き換える
    const requested = new URLSearchParams(location.hash.replace(/^#/, "")).get("id");
    if (requested !== null && route.id === null) navigate({ route: { ...route, filters: {} }, push: false });
    render({ screen: true });
    // 絞り込みは画面に渡した後、ハッシュから消す
    navigate({ route: { ...route, filters: {} }, push: false });

    // ===== 書き換えの知らせにつなぐ（サーバーの配信だけ） =====
    if (serverMode) {
      subscribeEvents({
        onChanged: () => void reload(),
        onConnection: (connected) => {
          // 切れた: 接続の状態を出し、最後に読めた記録で描き続ける
          if (!connected) {
            connection = "offline";
            renderTop();
            return;
          }
          // つながり直した: 切れていた間の書き換えを読み直す（最初の接続は切れていないので何もしない）
          if (connection === "offline") {
            connection = "online";
            renderTop();
            void reload();
          }
        },
      });
    }
  }

  // 文書が読み込まれたら起動する（記録の要素が無い文書では、読んだだけでは何もしない）
  if (document.getElementById(DATA_ELEMENT_ID) !== null) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }
}
