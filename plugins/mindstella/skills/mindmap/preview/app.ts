// 起動。記録を読み（配る書き出しは埋め込みから、サーバーの配信は記録の取得から）、URL のハッシュが指す画面を描き、操作を画面の移動・書き換えの知らせ・回答・意見の送信・端末の保存領域につなぐ。

namespace MindmapPreview {
  /** 埋め込みのデータの要素の ID */
  const DATA_ELEMENT_ID = "mindmap-data";

  /** 端末の保存領域のキー */
  export const PREFS_KEY = "mindmap-preview";

  /** 書きかけの本文を残す sessionStorage のキーの頭（`{頭}{項目の ID}`）。ポートを含むオリジンごとに分かれ、配信はワークスペースごとに別のポートなので、ワークスペースを含めなくても混ざらない */
  export const DRAFT_KEY_PREFIX = "mindmap-draft:";

  /** 項目 1 つの回答・意見の送信の状態（開いている間だけ持つ。`body` は sessionStorage にも残す） */
  export type SendState = {
    /** 入力欄の書きかけ */
    body: string;
    status: SendStatus;
    /** 送った日時 */
    sentAt: string | null;
    /** サーバーが返した送れなかった理由 */
    detail: string | null;
  };

  /** 端末に残す設定 */
  export type Prefs = {
    /** ライト / ダーク。null は OS の設定に従う */
    theme: Theme | null;
    /** 種類ごとの表示する列とピン留め */
    columns: Record<string, TablePrefs>;
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

  /** 画面の名前（つながりは種類のタブに無いので、ここで持つ） */
  function screenName(tab: Tab): string {
    return tab === "graph" ? "つながり" : tabLabel(tab);
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
    return { theme: null, columns: {} };
  }

  /** 端末の保存領域から設定を読む。読めないときは既定を返す */
  export function loadPrefs(storage: Storage): Prefs {
    try {
      const saved = storage.getItem(PREFS_KEY);
      if (saved === null) return defaultPrefs();
      const parsed = JSON.parse(saved) as Partial<Prefs>;
      return { ...defaultPrefs(), ...parsed };
    } catch {
      return defaultPrefs();
    }
  }

  /** 設定を端末の保存領域に残す。保存領域が例外を送るときは何もしない */
  export function savePrefs({ storage, prefs }: { storage: Storage; prefs: Prefs }): void {
    try {
      storage.setItem(PREFS_KEY, JSON.stringify(prefs));
    } catch {
      // 保存できない環境では、開いている間だけ設定を保つ
    }
  }

  /** その項目の書きかけを sessionStorage から読む。無いか保存領域が例外を送るときは空を返す */
  export function loadDraft(storage: Storage, id: string): string {
    try {
      return storage.getItem(`${DRAFT_KEY_PREFIX}${id}`) ?? "";
    } catch {
      return "";
    }
  }

  /** その項目の書きかけを sessionStorage に残す。空なら消す。保存領域が例外を送るときは何もしない */
  export function saveDraft(storage: Storage, id: string, body: string): void {
    try {
      if (body === "") storage.removeItem(`${DRAFT_KEY_PREFIX}${id}`);
      else storage.setItem(`${DRAFT_KEY_PREFIX}${id}`, body);
    } catch {
      // 保存できない環境では、開いている間のメモリの状態だけで保つ
    }
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
        setItem: () => undefined,
      };
    }
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
    const draftStorage = openStorage("sessionStorage");
    const prefs = loadPrefs(storage);
    const persist = (): void => savePrefs({ storage, prefs });
    restoreTablePrefs(prefs.columns, (kind, tablePrefs) => {
      if (tablePrefs === null) delete prefs.columns[kind];
      else prefs.columns[kind] = tablePrefs;
      persist();
    });

    // ===== テーマ =====
    let theme: Theme = prefs.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.dataset["theme"] = theme;

    // ===== 記録 =====
    let data: MindmapData = embedded ?? (await waitForRecords(theme));
    let index = buildIndex(data);
    document.title = `${data.settings.summary} | mindstella`;
    let connection: "online" | "offline" = "online";

    // ===== 画面の土台 =====
    const top = h({ tag: "div", attrs: { id: "top" } });
    const main = h({ tag: "main", attrs: { class: "content", id: "main" } });
    document.body.prepend(top, main);
    let route = parseHash({ hash: location.hash, index });
    let fullViewer: HTMLElement | null = null;

    // ===== 移動 =====
    /** 詳細パネルを別画面として積む幅か */
    const isNarrow = (): boolean => matchMedia(NARROW_QUERY).matches;

    /** 画面の既定の URL（絞り込みは書かない）に route を書き、画面を描く */
    const go = (next: Route, push: boolean): void => {
      const screenChanged =
        next.tab !== route.tab || next.view !== route.view || Object.keys(next.filters).length > 0;
      const idChanged = next.id !== route.id;
      route = next;
      navigate({ route: { ...route, filters: {} }, push });
      render({ screen: screenChanged || (route.tab === "decisions" && route.view === "map" && idChanged) });
    };

    /** 項目を開く。パネル・全画面の中の移動は履歴に積み、見てきた項目を行き来できるようにする */
    const openItem = (id: string, inPanel: boolean): void => {
      const next: Route = { ...route, id, filters: {} };
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
      if (isNarrow() && history.state !== null && (history.state as Trail).items !== undefined && history.length > 1) {
        history.back();
        return;
      }
      route = { ...route, id: null, full: false, filters: {} };
      navigate({ route, push: false });
      render({ screen: route.tab === "decisions" && route.view === "map" });
    };

    /** 項目を、その種類の画面で開く（画面を移るので履歴に積む） */
    const openFromSearch = (id: string): void => {
      const kind = index.byId.get(id)?.kind;
      if (kind === undefined) return;
      const tab: Tab = kind;
      go({ tab, view: defaultView(tab), id, full: false, filters: {} }, tab !== route.tab);
    };

    // ===== 描く =====
    /** トップバーとタブの帯 */
    const renderTop = (): void => {
      top.replaceChildren(
        topbar({
          title: data.settings.summary,
          tabs: TAB_KEYS.map((key) => ({
            key,
            label: tabLabel(key as Exclude<Tab, "graph">),
            icon: TAB_ICON[key as Exclude<Tab, "graph">],
            count: key === "overview" ? undefined : data[key as Kind].length,
          })),
          current: route.tab,
          theme,
          connection,
          readAt: serverMode ? data.built_at : null,
          onNavigate: (tab) => go({ ...route, tab, view: defaultView(tab), filters: {} }, true),
          onSearch: openSearch,
          onTheme: (next) => {
            theme = next;
            prefs.theme = next;
            persist();
            document.documentElement.dataset["theme"] = next;
            renderTop();
          },
        }),
      );
    };

    /** 今の画面 */
    const screenElement = (): HTMLElement => {
      const on = { open: (id: string) => openItem(id, false), view: (view: View) => go({ ...route, view, filters: {} }, false) };
      switch (route.tab) {
        case "overview":
          return overviewScreen({ index, on: { open: on.open, navigate: (next) => go({ ...next, id: route.id }, true) } });
        case "decisions":
          return decisionsScreen({ index, route, on });
        case "tasks":
          return tasksScreen({ index, route, on });
        case "docs":
          return docsScreen({ index, route, on });
        case "graph":
          return graphScreen({ index, on: { open: on.open }, selected: route.id });
        default:
          return recordsScreen({ index, route, on: { open: on.open } });
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
      // 開いたときの絞り込みは一度だけ使い、描き直しで使い回さない
      route = { ...route, filters: {} };
      if (route.tab === "graph") selectGraphItem(route.id);
    };

    /** 詳細パネルと全画面 */
    const renderDetail = (): void => {
      const existing = document.querySelector<HTMLElement>("aside.panel");
      const fullDialog = document.querySelector<HTMLDialogElement>("dialog.full");
      fullViewer = null;
      document.body.classList.toggle("panel-open", route.id !== null && !route.full);
      markSelected(route.id);
      // 開いている項目が無い: パネルも全画面も閉じる
      if (route.id === null) {
        existing?.classList.remove("open");
        fullDialog?.close();
        fullDialog?.remove();
        return;
      }
      const panel = detailPanel({
        id: route.id,
        index,
        full: route.full,
        on: {
          open: (id) => openItem(id, true),
          close: closeDetail,
          full: (full) => {
            // 全画面の中で図を拡大しているときは、本文へ戻る
            if (!full && fullViewer !== null) return closeFullViewer();
            go({ ...route, full }, false);
          },
          back: () => history.back(),
          forward: () => history.forward(),
          diagram: showDiagram,
        },
        send: serverMode ? sendFormProps(route.id) : null,
      });
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

    /** 描く（`screen` が真のとき本文の領域も描き直す） */
    const render = ({ screen }: { screen: boolean }): void => {
      renderTop();
      if (screen) {
        const wide = document.querySelector<HTMLElement>(".table-wrap, .map-wrap, .board");
        const keep = wide === null ? 0 : wide.scrollTop;
        renderMain();
        void keep;
      }
      renderDetail();
      if (route.tab === "graph") selectGraphItem(route.id);
    };

    // ===== 図の拡大 =====
    /** 図を拡大して見る。詳細パネルからはモーダル、全画面からは全画面の中身を切り替える */
    const showDiagram = (svg: SVGElement): void => {
      if (route.full) {
        const dialog = document.querySelector<HTMLDialogElement>("dialog.full");
        const body = dialog?.querySelector<HTMLElement>(".panel-body");
        if (dialog === null || dialog === undefined || body === null || body === undefined) return;
        body.hidden = true;
        const viewer = h({
          tag: "div",
          attrs: { class: "full-viewer" },
          children: [diagramViewer({ svg, on: { close: closeFullViewer } })],
        });
        body.after(viewer);
        fullViewer = viewer;
        return;
      }
      const modal = h({ tag: "dialog", attrs: { class: "viewer", "aria-label": "図の拡大" } });
      modal.append(diagramViewer({ svg, on: { close: () => modal.close() } }));
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

    // ===== 回答・意見の送信 =====
    /** 項目ごとの送信の状態（描き直し・項目の移動・詳細パネルと全画面の行き来でも保つ） */
    const sendStates = new Map<string, SendState>();

    /** 項目の送信の状態。無ければ、sessionStorage の書きかけから作る */
    const sendStateOf = (id: string): SendState => {
      let state = sendStates.get(id);
      if (state === undefined) {
        state = { body: loadDraft(draftStorage, id), status: "idle", sentAt: null, detail: null };
        sendStates.set(id, state);
      }
      return state;
    };

    /** 開いている送信の部品の結果を消す。入力中の欄を作り直さない（変換の途中を壊さないため） */
    const clearSendResult = (): void => {
      const form = document.querySelector<HTMLFormElement>("form.send");
      const message = form?.querySelector(".send-msg");
      if (message !== null && message !== undefined) {
        message.className = "send-msg";
        message.replaceChildren();
      }
      form?.querySelector("textarea")?.removeAttribute("aria-invalid");
    };

    /** 開いている項目の送信の部品を、今の状態で差し替え、入力欄へフォーカスを戻す */
    const redrawSend = (id: string): void => {
      const current = document.querySelector<HTMLFormElement>("form.send");
      // 別の項目へ移っていたら、状態だけ持っておく
      if (current === null || route.id !== id) return;
      const next = sendForm(sendFormProps(id));
      current.replaceWith(next);
      const field = next.querySelector("textarea");
      field?.focus();
      field?.setSelectionRange(field.value.length, field.value.length);
    };

    /** 本文を送り、結果を状態に残して部品を描き直す */
    const submit = async (id: string, body: string): Promise<void> => {
      const state = sendStateOf(id);
      state.body = body;
      // 空白だけ: 送らず、入力欄へフォーカスを戻す
      if (body.trim() === "") {
        Object.assign(state, { status: "empty", detail: null });
        redrawSend(id);
        return;
      }
      Object.assign(state, { status: "sending", detail: null });
      redrawSend(id);
      const result = await postSubmission(id, body);
      if (result.ok) {
        // 送れた: 書きかけを空にする
        Object.assign(state, { body: "", status: "sent", sentAt: result.sent, detail: null });
        saveDraft(draftStorage, id, "");
      } else {
        // 断られた・届かない: 本文を残す
        Object.assign(state, { status: "failed", detail: result.detail });
      }
      redrawSend(id);
    };

    /** 項目の送信の部品の引数 */
    const sendFormProps = (id: string): SendFormProps => {
      const state = sendStateOf(id);
      return {
        target: id,
        body: state.body,
        status: state.status,
        sentAt: state.sentAt,
        detail: state.detail,
        onInput: (body) => {
          state.body = body;
          saveDraft(draftStorage, id, body);
          // 送った・本文が空の結果は、入力を始めたら消す（送れなかった結果は次に送るまで残す）
          if (state.status === "sent" || state.status === "empty") {
            state.status = "idle";
            clearSendResult();
          }
        },
        onSend: (body) => void submit(id, body),
        onCopy: (body) => void navigator.clipboard?.writeText(body),
      };
    };

    // ===== 書き換えの知らせ =====
    /** 入力中の欄の選択とスクロールの位置を保って、画面を描き直す */
    const redrawKeepingState = (): void => {
      const field = document.activeElement;
      const typing = field instanceof HTMLTextAreaElement && field.closest("form.send") !== null;
      const selection = typing ? { start: field.selectionStart, end: field.selectionEnd } : null;
      const panelScroll = document.querySelector<HTMLElement>(".panel-body")?.scrollTop ?? 0;
      const pageScroll = window.scrollY;
      render({ screen: true });
      const panelBody = document.querySelector<HTMLElement>(".panel-body");
      if (panelBody !== null) panelBody.scrollTop = panelScroll;
      window.scrollTo(0, pageScroll);
      if (selection !== null) {
        const restored = document.querySelector<HTMLTextAreaElement>("form.send textarea");
        restored?.focus();
        restored?.setSelectionRange(selection.start, selection.end);
      }
    };

    /** 記録を読み直して描き直す。読み直しが読めないとき（422 など）は描き直さない */
    const reload = async (): Promise<void> => {
      const result = await fetchRecords();
      if (!result.ok) return;
      data = result.data;
      index = buildIndex(data);
      document.title = `${data.settings.summary} | mindstella`;
      // 開いていた項目が消えた: 詳細パネルを閉じる
      if (route.id !== null && !index.byId.has(route.id)) {
        route = { ...route, id: null, full: false, filters: {} };
        navigate({ route, push: false });
      }
      redrawKeepingState();
    };

    // ===== 操作と履歴 =====
    document.addEventListener("keydown", (event) => {
      const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName ?? "");
      if (event.key === "/" && !typing && document.querySelector("dialog[open]") === null) {
        event.preventDefault();
        openSearch();
      }
      // Esc: 重ねる面が無いときは、詳細パネルを閉じる
      if (
        event.key === "Escape" &&
        route.id !== null &&
        !route.full &&
        document.querySelector("dialog[open]") === null &&
        document.querySelector(":popover-open") === null
      ) {
        closeDetail();
      }
    });
    /** ハッシュが変わったとき（戻る・進む・手で書き換えた）、その画面を描く */
    const onLocationChange = (): void => {
      const next = parseHash({ hash: location.hash, index });
      if (toHash(next) === toHash(route)) return;
      const screen = next.tab !== route.tab || next.view !== route.view || (next.tab === "decisions" && next.view === "map" && next.id !== route.id);
      route = next;
      render({ screen });
    };
    addEventListener("popstate", onLocationChange);
    addEventListener("hashchange", onLocationChange);

    // ===== 最初の描き =====
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
