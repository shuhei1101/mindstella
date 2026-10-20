// PR #325 で足す、画面からの編集・保存待ち・まとめての保存を、今のプレビューの上に重ねるモックの仕組み。
// app.js が描いた画面へ、編集の入口・保存待ちのバッジ・トップバーの件数・保存待ちのパネル・設定の画面を差し込み、
// 保存待ちの編集を当てた記録を mock.js から画面へ返させる。
// 見本と論点の案はクエリで切り替える（無いときは body の data-* の案）。
//   sample: 保存待ちの見本（無し: D-17 の 4 件と T-13 の 1 件 / none: 0 件 / mixed: 書き換え・足す・消す・設定 /
//           blocked: 保存で書き込めない編集がある / offline: サーバーにつながらない）
//   place: 編集の置き方（a: 詳細パネルの中で切り替える / b: 別の画面）
//   stage: 保存待ちに溜める時点（a: 入力欄を離れたとき / b: 「保存待ちに入れる」を押したとき）
//   entry: 設定の画面の入口（a: 表示の設定のパネルの下端 / b: トップバーの題名 / c: トップバーのボタン / d: 表示の設定のパネルのタブ）
//   save: トップバーの保存の入口（a: 件数だけ / b: 件数と保存のボタン）
//   del: 消す編集を含む保存（a: ボタンに消す件数を出す / b: 消す行を先頭に分ける）
//   edit=1: 開いた項目を編集の表示で始める / pe=1: 保存待ちのパネルを開いて始める（0 で閉じて始める） / ws=1: 設定の画面で始める /
//   add: その種類の項目を足す入力で始める / sp=1: 表示の設定のパネルを開いて始める / diff: 差分の表示中（mock.js が時点を選ぶ） / mark: 撮影用に赤枠を付ける要素
// 見本と論点の案は、クエリに無いときは body の data-* を画面の既定にする
(() => {
  const body = document.body;
  /** 一部だけ覆われていても子をたどらない押せる要素（子だけを止めると読み上げの名前が消える） */
  const operable = "button, a[href], input, select, textarea, summary, [tabindex]";
  /** 左から重ねるパネルが覆った本文の部品に `inert` を付け、外す関数を返す。一部だけ覆われた押せる要素は、見えている側から押せるまま残す */
  MindmapPreview.inertBehind = (panel) => {
    const covered = {
      left: panel.offsetLeft,
      top: panel.offsetTop,
      right: panel.offsetLeft + panel.offsetWidth,
      bottom: panel.offsetTop + panel.offsetHeight,
    };
    const attached = [];
    /** 要素がパネルの矩形に全体が収まるなら `inert` を付け、一部だけ重なるなら子をたどる */
    const visit = (element) => {
      if (element === panel || element.inert) return;
      const rect = element.getBoundingClientRect();
      // 大きさを持たない要素（`display: contents` など）は、子をたどる
      if (rect.width === 0 || rect.height === 0) {
        for (const child of element.children) if (child instanceof HTMLElement) visit(child);
        return;
      }
      const overlaps =
        rect.left < covered.right && rect.right > covered.left && rect.top < covered.bottom && rect.bottom > covered.top;
      if (!overlaps) return;
      const inside =
        rect.left >= covered.left && rect.right <= covered.right && rect.top >= covered.top && rect.bottom <= covered.bottom;
      if (inside && !element.contains(panel)) {
        element.inert = true;
        attached.push(element);
        return;
      }
      if (element.matches(operable)) return;
      for (const child of element.children) if (child instanceof HTMLElement) visit(child);
    };
    const main = document.querySelector("main");
    if (main !== null) for (const child of main.children) if (child instanceof HTMLElement) visit(child);
    return () => {
      for (const element of attached) element.inert = false;
    };
  };
  const params = new URLSearchParams(location.search);
  /** 見本の指定（クエリ → body の data-*） */
  const given = (key) => params.get(key) ?? body.dataset[key] ?? null;
  /** 論点の案（指定が無ければ推奨の a） */
  const choice = (key) => given(key) ?? "a";
  const place = choice("place");
  const stage = choice("stage");
  const entry = choice("entry");
  const saveEntry = choice("save");
  const delStyle = choice("del");
  const sample = given("sample") ?? "edited";
  const diffing = params.has("diff");
  body.dataset.place = place;
  body.dataset.stage = stage;
  body.dataset.entry = entry;
  body.classList.toggle("pe-diffing", diffing);

  const server = window.mockServer;
  /** 元の記録（保存すると保存した編集を当てた記録に替わる） */
  let base = server.records;

  // ===== 種類とキー =====
  /** 種類ごとの呼び名・ID の頭・状態の選択肢 */
  const KINDS = {
    decisions: { label: "検討事項", prefix: "D", statuses: ["未決定", "決定済み", "要見直し", "保留", "未整理", "対象外", "取り下げ"], first: "未整理" },
    tasks: { label: "タスク", prefix: "T", statuses: ["未着手", "進行中", "完了", "保留", "中止"], first: "未着手" },
    research: { label: "調査", prefix: "R", statuses: null, first: null },
    docs: { label: "資料", prefix: "A", statuses: ["下書き", "確認中", "完成"], first: "下書き" },
    terms: { label: "用語集", prefix: "G", statuses: null, first: null },
    notes: { label: "メモ", prefix: "N", statuses: null, first: null },
    logs: { label: "会話ログ", prefix: "L", statuses: null, first: null },
  };
  /** タブの名前から種類（records の画面はタブごとに 1 種類） */
  const KIND_OF_TAB = { decisions: "decisions", tasks: "tasks", research: "research", docs: "docs", terms: "terms", notes: "notes", logs: "logs" };
  /** キーの呼び名（詳細パネルの見出しと同じ言葉） */
  const KEY_LABELS = {
    status: "状態", title: "タイトル", target: "機能", category: "カテゴリー", phase: "フェーズ", tags: "タグ", depends_on: "依存先",
    answer: "決定内容", reason: "理由", body: "本文", result: "結果", kind: "種類", question: "問い", conclusion: "結論",
    confidence: "確からしさ", related: "関連", withdrawn: "取り下げ", meaning: "意味", aliases: "別名", content: "内容", date: "日付",
    deliverable: "納品物",
  };
  /** 種類ごとに編集の表示に並べるキー（並びの順） */
  const FIELDS = {
    decisions: ["status", "title", "target", "category", "phase", "tags", "depends_on", "options", "answer", "reason", "body"],
    tasks: ["status", "title", "target", "kind", "tags", "result", "body"],
    research: ["title", "question", "conclusion", "confidence", "tags", "related", "withdrawn", "body"],
    docs: ["status", "title", "kind", "deliverable", "tags", "related", "withdrawn", "body"],
    terms: ["title", "meaning", "aliases", "tags", "withdrawn", "body"],
    notes: ["title", "content", "tags", "related", "withdrawn", "body"],
    logs: ["title", "date", "related", "withdrawn", "body"],
  };
  /** 1 行で書くキー・何行も書くキー・値を並べるキー */
  const LONG_KEYS = new Set(["answer", "reason", "body", "result", "question", "conclusion", "meaning", "content"]);
  const LIST_KEYS = new Set(["tags", "depends_on", "related", "aliases"]);
  /** 設定のキーの呼び名 */
  const SETTING_LABELS = {
    summary: "題名", playbooks: "プレイブック", phases: "フェーズ", target_label: "最上位の軸の呼び名", goal: "ゴール",
    targets: "対象", categories: "カテゴリー", tag_vocabulary: "タグの語彙", links: "関連する場所", keep: "保持する回数",
  };

  /** ID から種類を引く */
  const kindOf = (id) => Object.keys(KINDS).find((kind) => (base[kind] ?? []).some((item) => item.id === id)) ?? null;
  /** ID から元の項目を引く */
  const itemOf = (id) => {
    const kind = kindOf(id);
    return kind === null ? null : base[kind].find((item) => item.id === id);
  };
  /** 項目を指している項目の ID（依存先・関連・経緯） */
  const referrersOf = (id) => Object.keys(KINDS).flatMap((kind) =>
    base[kind].filter((item) => ["depends_on", "related", "sources"].some((key) => (item[key] ?? []).includes(id))).map((item) => item.id));
  /** 本文のファイルの名前 */
  const bodyKey = (id) => `${id}.md`;
  /** 値を 1 行の文字にする */
  const flat = (value) => {
    if (value === undefined || value === null || value === "") return "（空）";
    if (Array.isArray(value)) return value.length === 0 ? "（空）" : value.join("・");
    if (value === true) return "はい";
    if (value === false) return "いいえ";
    return String(value).replace(/\s+/g, " ");
  };
  /** 見本で使う、今使っているタグの一覧（タグの語彙の見本） */
  const vocabulary = () => [...new Set(Object.keys(KINDS).flatMap((kind) => base[kind].flatMap((item) => item.tags ?? [])))].sort();

  // ===== 保存待ちの編集 =====
  // 1 件 = 項目のキー 1 つ・本文・案 1 つの追加と書き換えと削除・採用する案の切り替え・設定のキー 1 つ・項目 1 つの追加と削除
  // op: set（キー）/ option-add / option-edit / option-remove / adopt / item-add / item-remove / setting
  /** 見本の保存待ちの編集 */
  const SAMPLES = {
    edited: [
      { target: "D-17", op: "set", key: "answer", value: "ゴールはフェーズごとに 1 つ持ち、話しながら足す・直す" },
      { target: "D-17", op: "set", key: "tags", value: ["mindstella", "ゴールと設定", "記録の形"] },
      { target: "D-17", op: "option-add", key: "C", value: "ゴールはフェーズごとに 1 つ持つ" },
      { target: "D-17", op: "adopt", key: "C", value: "C" },
      { target: "T-13", op: "set", key: "status", value: "中止" },
    ],
    mixed: [
      { target: "D-17", op: "set", key: "answer", value: "ゴールはフェーズごとに 1 つ持ち、話しながら足す・直す" },
      { target: "D-17", op: "option-add", key: "C", value: "ゴールはフェーズごとに 1 つ持つ" },
      { target: "D-17", op: "adopt", key: "C", value: "C" },
      { target: "new:1", op: "item-add", key: "tasks", value: { title: "画面を作る", status: "未着手" } },
      { target: "new:2", op: "item-add", key: "notes", value: { title: "画面の形" } },
      { target: "T-17", op: "item-remove", key: "tasks", value: null },
      { target: "settings", op: "setting", key: "summary", value: "画面の編集を話し合い、Issue に起票できる形にまとめる" },
    ],
    blocked: [
      { target: "D-17", op: "set", key: "answer", value: "ゴールはフェーズごとに 1 つ持ち、話しながら足す・直す", blocked: { reason: "changed", at: "2026-10-21T05:02:00+00:00" } },
      { target: "T-13", op: "set", key: "status", value: "完了" },
      { target: "D-8", op: "item-remove", key: "decisions", value: null, blocked: { reason: "referenced" } },
    ],
    offline: [
      { target: "D-17", op: "set", key: "answer", value: "ゴールはフェーズごとに 1 つ持ち、話しながら足す・直す" },
    ],
    none: [],
  };
  const STORE_KEY = `mock-325-edits:${sample}`;
  /** 保存待ちの編集（開き直しても残るよう、見本ごとに端末の作業の保存領域に持つ） */
  let edits = (() => {
    try {
      const kept = sessionStorage.getItem(STORE_KEY);
      if (kept !== null) return JSON.parse(kept);
    } catch {
      // 保てない端末では見本から始める
    }
    return (SAMPLES[sample] ?? SAMPLES.edited).map((edit, index) => ({ id: `E-${index + 1}`, ...edit }));
  })();
  let editSeq = edits.length;
  let newSeq = edits.filter((edit) => edit.op === "item-add").length;
  /** 保存の結果（blocked: 書き込めない編集がある / offline: つながらない / saving: 保存している / null: まだ保存していない） */
  let saveState = edits.some((edit) => edit.blocked) ? "blocked" : null;

  /** 保存待ちの編集を端末に保つ */
  const keep = () => {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify(edits));
    } catch {
      // 保てない端末では、開いている間だけ残る
    }
  };
  /** 項目の保存待ちの編集 */
  const editsOf = (target) => edits.filter((edit) => edit.target === target);
  /** キーの保存待ちの編集 */
  const editOfKey = (target, op, key) => edits.find((edit) => edit.target === target && edit.op === op && edit.key === key) ?? null;

  /** 保存待ちの編集を当てた記録を作る（足す項目は画面へ渡さず、edit.js が一覧へ差し込む） */
  const applied = () => {
    const next = structuredClone(base);
    for (const edit of edits) {
      if (edit.op === "setting") {
        next.settings[edit.key] = structuredClone(edit.value);
        continue;
      }
      const kind = kindOf(edit.target);
      if (kind === null) continue;
      const item = next[kind].find((entry) => entry.id === edit.target);
      if (edit.op === "set" && edit.key === "body") next.bodies[item.body ?? bodyKey(item.id)] = edit.value;
      else if (edit.op === "set") item[edit.key] = structuredClone(edit.value);
      else if (edit.op === "option-add") item.options = [...(item.options ?? []), { key: edit.key, content: edit.value }];
      else if (edit.op === "option-edit") item.options = item.options.map((option) => (option.key === edit.key ? { ...option, content: edit.value } : option));
      else if (edit.op === "option-remove") item.options = item.options.filter((option) => option.key !== edit.key);
      else if (edit.op === "adopt") {
        item.options = (item.options ?? []).map((option) => ({ ...option, adopted: option.key === edit.value }));
      }
    }
    return next;
  };
  /** 画面へ返す記録を差し替え、知らせるときは画面に読み直させる（差分の表示中は保存した記録だけを見せる） */
  const publish = (notify) => {
    server.serve(diffing ? base : applied());
    if (notify) server.notify();
  };

  /** 編集を足す・書き換える（元の値に戻ったら消す）。変わったら真 */
  const putEdit = ({ target, op, key, value, original }) => {
    const found = editOfKey(target, op, key);
    const same = JSON.stringify(value) === JSON.stringify(original);
    if (found !== null && same && op !== "option-add") {
      edits = edits.filter((edit) => edit !== found);
    } else if (found !== null) {
      if (JSON.stringify(found.value) === JSON.stringify(value)) return false;
      found.value = value;
      delete found.blocked;
    } else if (!same || op === "option-remove" || op === "item-remove") {
      editSeq += 1;
      edits = [...edits, { id: `E-${editSeq}`, target, op, key, value }];
    } else {
      return false;
    }
    keep();
    return true;
  };
  /** 1 件を取り消す（足した案を取り消すと、その案の採用の切り替えも取り消す） */
  const undo = (id) => {
    const found = edits.find((edit) => edit.id === id);
    edits = edits.filter((edit) => edit !== found && !(found.op === "option-add" && edit.target === found.target && edit.op === "adopt" && edit.value === found.key));
    if (!edits.some((edit) => edit.blocked)) saveState = null;
    keep();
  };

  // ===== 小さな部品 =====
  /** 要素を作る（attrs の値が null の属性は付けない。children は文字か要素） */
  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs)) {
      if (value === null || value === undefined || value === false) continue;
      if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
      else node.setAttribute(name, value === true ? "" : value);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  };
  /** 線のアイコン（今のプレビューと同じ 24 の枠・線の太さ） */
  const ICONS = {
    pencil: '<path d="M4 20h4L19 9l-4-4L4 16Z"></path><path d="m13.5 6.5 4 4"></path>',
    pending: '<path d="m12 3 9 5-9 5-9-5Z"></path><path d="m3 13 9 5 9-5"></path>',
    plus: '<path d="M12 5v14M5 12h14"></path>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"></path><path d="M10 11v6M14 11v6"></path>',
    undo: '<path d="M9 14 4 9l5-5"></path><path d="M4 9h10a6 6 0 0 1 0 12h-3"></path>',
    warn: '<path d="M12 4 2.5 20h19Z"></path><path d="M12 10v4M12 17v.5"></path>',
    close: '<path d="M18 6 6 18M6 6l12 12"></path>',
    check: '<path d="m5 12 5 5 9-10"></path>',
    gear: '<circle cx="12" cy="12" r="3"></circle><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"></path>',
    save: '<path d="M5 4h11l3 3v13H5Z"></path><path d="M8 4v5h7V4M8 20v-6h8v6"></path>',
    back: '<path d="m15 18-6-6 6-6"></path>',
    spin: '<path d="M12 3a9 9 0 1 0 9 9"></path>',
  };
  /** アイコンの SVG 要素 */
  const icon = (name) => {
    const wrap = document.createElement("span");
    wrap.innerHTML = `<svg class="icon" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
    return wrap.firstElementChild;
  };
  /** 読み上げにだけ出す文字 */
  const srOnly = (text) => el("span", { class: "sr-only" }, text);
  /** 保存待ちのバッジ（kind: edit 書き換え / add 足す / remove 消す / blocked 書き込めない。compact は印だけ） */
  const mark = (kind, compact = false) => {
    const text = { edit: "保存待ち", add: "保存待ち", remove: "保存で削除", blocked: "書き込めない" }[kind];
    const symbol = { edit: "pending", add: "pending", remove: "trash", blocked: "warn" }[kind];
    return el("span", { class: `pm pm-${kind}${compact ? " pm-compact" : ""}`, title: compact ? text : null }, icon(symbol), compact ? srOnly(text) : el("span", { class: "pm-text" }, text));
  };
  /** 項目の保存待ちの状態（無ければ null） */
  const markKindOf = (target) => {
    const list = editsOf(target);
    if (list.length === 0) return null;
    if (list.some((edit) => edit.blocked)) return "blocked";
    if (list.some((edit) => edit.op === "item-remove")) return "remove";
    if (list.some((edit) => edit.op === "item-add")) return "add";
    return "edit";
  };
  /** 日時を JST の短い形にする */
  const jst = (iso) => new Intl.DateTimeFormat("ja-JP", { timeZone: "Asia/Tokyo", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

  // ===== 画面の状態 =====
  const ui = {
    /** 編集の表示にしている項目（ID か足す項目の new:n） */
    editing: given("edit") === "1" ? "route" : null,
    /** 保存待ちのパネルを開いているか */
    pendingOpen: given("pe") === "1" && !diffing,
    /** 設定の画面を開いているか */
    wsOpen: given("ws") === "1" && !diffing,
    /** 保存待ちのパネルから開いた項目か（幅 900px 以下で閉じるとパネルへ戻る） */
    fromPending: false,
    /** 「保存待ちに入れる」の案で、まだ溜めていない入力があるか */
    dirty: false,
    /** 表示の設定のパネルのタブ（d の案。view: この端末の表示 / ws: ワークスペースの設定） */
    drawerTab: "view",
    /** 直前の保存の知らせ */
    toast: null,
  };

  /** 今のハッシュの値 */
  const route = () => new URLSearchParams(location.hash.replace(/^#/, ""));
  /** 開いている項目の ID */
  const openedId = () => route().get("id");
  /** ハッシュを組み替えて移る */
  const go = (changes) => {
    const next = route();
    for (const [key, value] of Object.entries(changes)) {
      if (value === null) next.delete(key);
      else next.set(key, value);
    }
    location.hash = next.toString();
  };

  // ===== 描き直し =====
  /** app.js の描き直し（要素の入れ替えと、パネルを開くクラスの付け外し）を見張り、差し込みを当て直す（差し込みで起きた変化は見ない） */
  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      decorate();
    });
  });
  const observe = () => observer.observe(body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
  /** 画面の全ての差し込みを当て直す */
  const decorate = () => {
    observer.disconnect();
    // 差し込みが途中で止まっても、見張りは戻す（誤りはそのまま投げる）
    try {
      decorateTopbar();
      decorateToolbar();
      decorateLists();
      decoratePanel();
      decorateDrawer();
      renderPending();
      renderWorkspace();
      renderEditScreen();
      renderToast();
    } finally {
      observe();
    }
  };

  // ===== トップバー =====
  /** 保存待ちの件数のボタン（と、保存の入口の案 B の保存のボタン）・題名の入口（案 B）・設定のボタン（案 C） */
  const decorateTopbar = () => {
    const bar = document.querySelector(".topbar");
    if (bar === null) return;
    const comments = bar.querySelector(".comments-btn");
    let button = bar.querySelector(".pending-btn");
    if (button === null && comments !== null) {
      button = el("button", { class: "pending-btn", type: "button", "aria-haspopup": "true", onclick: () => togglePending() },
        el("span", { class: "pb-icon" }, icon("pending")), el("span", { class: "label" }, "保存待ち"), el("span", { class: "count" }));
      comments.before(button);
    }
    if (button !== null) {
      const count = edits.length;
      const blocked = saveState === "blocked";
      button.hidden = count === 0 || diffing;
      button.classList.toggle("open", ui.pendingOpen);
      button.classList.toggle("blocked", blocked);
      button.setAttribute("aria-expanded", String(ui.pendingOpen));
      button.setAttribute("aria-label", `保存待ち（${count} 件${blocked ? "・書き込めない編集あり" : ""}）`);
      const countNode = button.querySelector(".count");
      if (countNode.textContent !== String(count)) countNode.textContent = String(count);
      const iconSlot = button.querySelector(".pb-icon");
      const want = blocked ? "warn" : "pending";
      if (iconSlot.dataset.icon !== want) {
        iconSlot.replaceChildren(icon(want));
        iconSlot.dataset.icon = want;
      }
    }
    // 保存の入口の案 B: 件数の隣に保存のボタンを置き、上端から直接保存する
    let quick = bar.querySelector(".pending-save-btn");
    if (saveEntry === "b" && quick === null && button !== null) {
      quick = el("button", { class: "pending-save-btn", type: "button", onclick: () => save() }, icon("save"), el("span", { class: "label" }, "保存する"));
      button.after(quick);
    }
    if (quick !== null) {
      quick.hidden = edits.length === 0 || diffing;
      quick.disabled = saveState === "saving";
      quick.setAttribute("aria-label", `保存待ちの ${edits.length} 件を保存する`);
    }
    // 設定の画面の入口の案 B: 題名を押せるボタンにする
    const title = bar.querySelector(".brand-sub");
    if (entry === "b" && title !== null && !title.classList.contains("ws-entry-title")) {
      title.classList.add("ws-entry-title");
      title.setAttribute("role", "button");
      title.setAttribute("tabindex", "0");
      title.setAttribute("aria-label", `設定を編集する（題名: ${title.textContent}）`);
      title.addEventListener("click", () => openWorkspace());
      title.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openWorkspace();
        }
      });
    }
    // 設定の画面の入口の案 C: トップバーに設定のボタンを足す
    if (entry === "c" && bar.querySelector(".ws-btn") === null) {
      const settingsButton = bar.querySelector(".settings-btn");
      settingsButton?.before(el("button", { class: "ws-btn", type: "button", "aria-label": "設定を編集する", onclick: () => openWorkspace() }, icon("gear"), el("span", { class: "label" }, "設定")));
    }
    for (const node of bar.querySelectorAll(".ws-btn")) node.hidden = diffing;
  };

  // ===== 一覧 =====
  /** 開いている画面の種類（項目の種類の画面でなければ null） */
  const currentKind = () => KIND_OF_TAB[route().get("tab") ?? ""] ?? null;
  /** 一覧の上の帯に「項目を足す」を置く */
  const decorateToolbar = () => {
    const kind = currentKind();
    const toolbar = document.querySelector(".screen .toolbar, .screen.records .table-toolbar");
    const existing = document.querySelector(".pe-add");
    if (existing !== null && (existing.dataset.kind !== kind || existing.parentElement !== toolbar)) existing.remove();
    if (toolbar === null || kind === null || diffing || toolbar.querySelector(".pe-add") !== null) return;
    const button = el("button", { class: "btn pe-add", type: "button", "data-kind": kind, onclick: () => startAdd(kind) }, icon("plus"), el("span", { class: "lbl" }, "項目を追加"));
    button.setAttribute("aria-label", `${KINDS[kind].label}の項目を追加`);
    const columns = toolbar.querySelector(".cols-btn-table");
    if (columns !== null) columns.before(button);
    else toolbar.append(button);
  };
  /** 項目の行・カード・節に保存待ちのバッジを付け、足す項目を差し込む */
  const decorateLists = () => {
    // 付けたバッジを、今の保存待ちと合わない分だけ外す
    for (const node of document.querySelectorAll("[data-pe-mark]")) {
      const id = node.dataset.peMark;
      const want = diffing ? null : markKindOf(id);
      const host = node.closest("[data-id], [data-node]");
      if (want === null || node.dataset.kind !== want) {
        node.remove();
        host?.classList.remove("pe-removing", "pe-changed", "pe-blocked");
      }
    }
    if (diffing) {
      for (const node of document.querySelectorAll(".pe-new")) node.remove();
      return;
    }
    // カード（ボード・資料のカード）
    for (const card of document.querySelectorAll(".card[data-id], .doc-card[data-id]")) {
      attachMark(card, card.dataset.id, card.querySelector(".c-meta"), false);
    }
    // 表の行: タイトルの後ろ
    for (const row of document.querySelectorAll("tr[data-id]")) {
      const cell = row.querySelector(".row-open")?.parentElement ?? null;
      attachMark(row, row.dataset.id, cell, false);
    }
    // マップの節: 2 行目（ID と状態）の後ろに印だけ
    for (const node of document.querySelectorAll("button.n-item[data-node]")) {
      attachMark(node, node.dataset.node, node.querySelector(".r2"), true);
    }
    insertNewItems();
  };
  /** 1 つの行・カードにバッジを付ける */
  const attachMark = (host, id, slot, compact) => {
    const kind = markKindOf(id);
    host.classList.toggle("pe-changed", kind === "edit");
    host.classList.toggle("pe-removing", kind === "remove");
    host.classList.toggle("pe-blocked", kind === "blocked");
    if (kind === null || slot === null || slot.querySelector(`[data-pe-mark="${id}"]`) !== null) return;
    const badge = mark(kind, compact);
    badge.dataset.peMark = id;
    badge.dataset.kind = kind;
    const comment = slot.querySelector(":scope > .cmk-place");
    if (comment !== null) comment.before(badge);
    else slot.append(badge);
  };
  /** 足す項目を、開いている種類の一覧の先頭に差し込む（ID は保存で決まるため出さない） */
  const insertNewItems = () => {
    const kind = currentKind();
    const adds = edits.filter((edit) => edit.op === "item-add" && edit.key === kind);
    for (const node of document.querySelectorAll(".pe-new")) {
      if (!adds.some((edit) => edit.target === node.dataset.newId)) node.remove();
    }
    for (const edit of adds) {
      const title = edit.value.title === "" ? "（タイトル未入力）" : edit.value.title;
      const blocked = edit.blocked !== undefined;
      const open = () => openAdd(edit.target);
      // ボード: 状態の列の先頭
      const column = [...document.querySelectorAll(".board-col")].find((col) => col.getAttribute("aria-label") === (edit.value.status ?? KINDS[kind].first));
      upsert(column, ".board-col > h2", edit, () => el("button", { class: "card pe-new", type: "button", "data-new-id": edit.target, onclick: open },
        el("div", { class: "c-ttl" }, title),
        el("div", { class: "c-meta" }, el("span", { class: "pe-noid" }, "ID は保存で決まる"), mark(blocked ? "blocked" : "add"))));
      // 資料のカード
      upsert(document.querySelector(".doc-grid"), null, edit, () => el("button", { class: "card doc-card pe-new", type: "button", "data-new-id": edit.target, onclick: open },
        el("span", { class: "c-ttl" }, title),
        el("span", { class: "c-meta" }, el("span", { class: "pe-noid" }, "ID は保存で決まる"), mark(blocked ? "blocked" : "add"))));
      // 表: 先頭の行
      const tbody = document.querySelector(`.table-block[data-kind="${kind}"] tbody, .screen.${kind} table.grid tbody`);
      if (tbody !== null && tbody.querySelector(`.pe-new[data-new-id="${edit.target}"]`) === null) {
        const columns = tbody.closest("table").querySelectorAll("thead th").length;
        const row = el("tr", { class: "pe-new", "data-new-id": edit.target },
          el("td", { class: "nowrap" }, el("span", { class: "pe-noid" }, "—")),
          el("td", {}, el("button", { class: "row-open", type: "button", onclick: open }, title), mark(blocked ? "blocked" : "add")),
          ...Array.from({ length: Math.max(0, columns - 2) }, () => el("td", {})));
        tbody.prepend(row);
      }
    }
  };
  /** 入れ物に足す項目のカードが無ければ先頭（after の要素の後ろ）に入れ、タイトルが変わっていれば入れ替える */
  const upsert = (container, after, edit, build) => {
    if (container === null || container === undefined) return;
    const found = container.querySelector(`.pe-new[data-new-id="${edit.target}"]`);
    const title = edit.value.title === "" ? "（タイトル未入力）" : edit.value.title;
    if (found !== null && found.querySelector(".c-ttl")?.textContent === title) return;
    found?.remove();
    const card = build();
    const anchor = after === null ? null : container.querySelector(after);
    if (anchor !== null) anchor.after(card);
    else container.prepend(card);
  };

  // ===== 詳細パネル =====
  /** 開いている項目の詳細パネルに、編集の入口・バッジ・編集の表示を差し込む */
  const decoratePanel = () => {
    // 詳細の全画面を開いているときは、全画面の中に差し込む
    const panel = document.querySelector("dialog.full[open]") ?? document.querySelector("aside.panel.open:not(.pe-add-panel)");
    if (panel === null) return;
    const id = panel.querySelector(".panel-kind .mono")?.textContent ?? null;
    if (id === null || itemOf(id) === null) return;
    if (ui.editing === "route") ui.editing = id;
    if (ui.editing !== null && ui.editing !== id && !String(ui.editing).startsWith("new:")) ui.editing = null;
    const head = panel.querySelector(".panel-head");
    const editingHere = ui.editing === id && place === "a" && !diffing;
    // 編集の入口（差分の表示中・配る書き出しでは出さない）
    let toggle = head.querySelector(".pe-edit-toggle");
    if (diffing) toggle?.remove();
    else {
      if (toggle === null) {
        toggle = el("button", { class: "btn pe-edit-toggle", type: "button", onclick: () => toggleEdit(id) }, icon("pencil"), el("span", { class: "lbl" }));
        head.querySelector(".spacer").after(toggle);
      }
      const label = editingHere ? "編集を終える" : "編集する";
      toggle.setAttribute("aria-pressed", String(editingHere));
      toggle.title = label;
      const lbl = toggle.querySelector(".lbl");
      if (lbl.textContent !== label) lbl.textContent = label;
    }
    // 項目のバッジ（見出しの種類と ID の後ろ）
    const kindMark = markKindOf(id);
    const headMark = head.querySelector("[data-pe-head]");
    if (headMark !== null && (diffing || headMark.dataset.kind !== kindMark)) headMark.remove();
    if (!diffing && kindMark !== null && head.querySelector("[data-pe-head]") === null) {
      const badge = mark(kindMark, true);
      badge.dataset.peHead = id;
      badge.dataset.kind = kindMark;
      head.querySelector(".panel-kind").after(badge);
    }
    panel.classList.toggle("pe-editing", editingHere);
    const scrollBody = panel.querySelector(".panel-body");
    const detail = scrollBody.querySelector(":scope > .detail");
    const form = scrollBody.querySelector(".pe-form");
    if (editingHere) {
      if (form === null || form.dataset.id !== id) {
        form?.remove();
        panel.querySelector(".pe-stage-bar")?.remove();
        const fresh = buildForm(id, "panel");
        scrollBody.append(fresh);
        placeStageBar(fresh);
      }
      if (detail !== null) detail.hidden = true;
    } else {
      form?.remove();
      panel.querySelector(".pe-stage-bar")?.remove();
      if (detail !== null) {
        detail.hidden = false;
        if (!diffing) markKeys(detail, id);
      }
    }
  };
  /** 読む表示のキー・案に保存待ちのバッジを付ける */
  const markKeys = (detail, id) => {
    for (const node of detail.querySelectorAll("[data-pe-key]")) node.remove();
    for (const edit of editsOf(id)) {
      const badge = mark(edit.blocked ? "blocked" : "edit", true);
      badge.dataset.peKey = edit.key;
      if (edit.op === "set") {
        // 置き場所: メタの行の名前 → 値の前の太字の名前 → 節の見出し → 値（状態・タイトル）の後ろ
        const valueNode = detail.querySelector(`[data-key="${edit.key}"]`);
        const label = KEY_LABELS[edit.key];
        const dt = [...detail.querySelectorAll("dt")].find((node) => node.textContent === label);
        const bold = valueNode?.parentElement?.querySelector(":scope > b") ?? null;
        const heading = [...detail.querySelectorAll(".d-sec > h3")].find((node) => node.textContent === label);
        if (dt !== undefined) dt.append(badge);
        else if (bold !== null) bold.append(badge);
        else if (heading !== undefined) heading.append(badge);
        else if (valueNode !== null) valueNode.append(badge);
      } else if (edit.op === "adopt" || edit.op.startsWith("option")) {
        // 案の見出しに 1 つだけ付ける（足した案を採用したときも 1 つ）
        const option = detail.querySelector(`[data-key="options[${edit.op === "adopt" ? edit.value : edit.key}].content"]`)?.closest(".opt");
        const head = option?.querySelector(".o-head");
        if (head !== undefined && head !== null && head.querySelector("[data-pe-key]") === null) head.append(badge);
      }
    }
  };
  /** 編集の表示を切り替える（溜めていない入力があるときは確かめる） */
  const toggleEdit = (id) => {
    if (ui.editing === id) {
      confirmLeave(() => {
        ui.editing = null;
        publish(true);
        // 別の画面の案: 編集を終えたら、読む表示の詳細パネルへ戻る
        if (place === "b" && !id.startsWith("new:")) go({ id });
        decorate();
      });
      return;
    }
    ui.editing = id;
    // 別の画面の案: 詳細パネルを閉じて編集の画面へ移る
    if (place === "b") go({ id: null });
    decorate();
    // パネルの中では最初の入力欄へ、別の画面では見出しへ移る（画面の頭から読む）
    if (place === "a") document.querySelector(".pe-form [data-first]")?.focus();
    else document.querySelector(".pe-edit-screen h1")?.focus({ preventScroll: true });
  };
  /** 「保存待ちに入れる」の案で溜めていない入力があるとき、捨てるかを確かめてから進む */
  const confirmLeave = (proceed) => {
    if (stage !== "b" || !ui.dirty) {
      proceed();
      return;
    }
    const dialog = el("dialog", { class: "pe-confirm", "aria-labelledby": "pe-confirm-title" },
      el("h2", { id: "pe-confirm-title" }, "入力を保存待ちに入れずに閉じますか"),
      el("p", {}, "「保存待ちに入れる」を押していない入力は消えます。"),
      el("div", { class: "pe-confirm-row" },
        el("button", { class: "btn", type: "button", onclick: () => dialog.close() }, "編集に戻る"),
        el("button", { class: "btn primary", type: "button", onclick: () => {
          ui.dirty = false;
          dialog.close();
          proceed();
        } }, "入力を捨てて閉じる")));
    dialog.addEventListener("close", () => dialog.remove());
    body.append(dialog);
    dialog.showModal();
  };

  // ===== 編集の表示 =====
  /** 項目（足す項目は new:n）の編集の表示を作る。where: panel 詳細パネル / screen 別の画面 */
  const buildForm = (id, where) => {
    const adding = id.startsWith("new:");
    const addEdit = adding ? edits.find((edit) => edit.target === id && edit.op === "item-add") ?? null : null;
    const kind = adding ? (addEdit?.key ?? ui.addKind) : kindOf(id);
    const original = adding ? { title: "", status: KINDS[kind].first, tags: [] } : itemOf(id);
    const view = adding ? { ...original, ...(addEdit?.value ?? {}) } : applied()[kind].find((item) => item.id === id);
    const formId = `pe-form-${where}-${id.replace(/[^A-Za-z0-9]/g, "")}`;
    const form = el("form", { class: `pe-form pe-form-${where}`, id: formId, "data-id": id, novalidate: true, "aria-label": adding ? `${KINDS[kind].label}を追加` : `${id} を編集` });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (stage === "b") stageAll(form, id);
    });

    // 編集できないキー（ID・作成日時・更新日時・編集した人）
    form.append(el("dl", { class: "pe-fixed" },
      el("dt", {}, "ID"), el("dd", { class: "mono" }, adding ? "保存で決まる" : id),
      ...(adding ? [] : [
        el("dt", {}, "作成"), el("dd", {}, jst(original.created)),
        el("dt", {}, "更新"), el("dd", {}, `${jst(original.updated)}（${original.updated_by === "user" ? "利用者" : "AI"}）`),
      ])));

    for (const key of FIELDS[kind]) {
      if (adding && !["status", "title", "tags", "body"].includes(key)) continue;
      if (key === "options") {
        form.append(buildOptions(id, original, view));
        continue;
      }
      form.append(buildField({ id, kind, key, original, view, adding }));
    }
    // 消す（足す項目は保存待ちのパネルで取り消す）
    if (!adding) {
      const removing = editOfKey(id, "item-remove", kind);
      const referrers = referrersOf(id);
      form.append(el("section", { class: "pe-remove-sec" },
        el("h2", {}, "項目を削除"),
        removing === null
          ? el("button", { class: "btn pe-danger", type: "button", onclick: () => {
            putEdit({ target: id, op: "item-remove", key: kind, value: null, original: undefined });
            decorate();
          } }, icon("trash"), "項目を削除")
          : el("button", { class: "btn", type: "button", onclick: () => {
            undo(removing.id);
            decorate();
          } }, icon("undo"), "削除を取り消す"),
        referrers.length > 0 ? el("p", { class: "pe-hint" }, icon("warn"), `${referrers.join("・")} が指しているため、保存のときに削除できません。指している項目から外すと削除できます。`) : null));
    }
    // 溜めた知らせ（読み上げにも伝える）
    form.append(el("p", { class: "pe-form-msg", role: "status" }));
    // 「保存待ちに入れる」の案: 入力の区画の外（パネル・画面の下端）に置くボタンの帯。置く側が placeStageBar で動かす
    if (stage === "b") {
      form.stageBar = el("div", { class: "pe-stage-bar", "data-for": formId },
        el("button", { class: "btn", type: "button", onclick: () => {
          ui.dirty = false;
          const fresh = buildForm(id, where);
          form.stageBar.remove();
          form.replaceWith(fresh);
          placeStageBar(fresh);
        } }, "入力を捨てる"),
        el("button", { class: "btn primary", type: "submit", form: formId }, icon("pending"), "保存待ちに入れる"));
    }
    return form;
  };
  /** 「保存待ちに入れる」の帯を、入力の区画の外に置く（パネル・全画面は送る区画の下、別の画面は入力の後ろ） */
  const placeStageBar = (form) => {
    if (form.stageBar === undefined) return;
    const scroll = form.closest(".panel-scroll, dialog.full .panel-body");
    if (scroll !== null) scroll.after(form.stageBar);
    else form.after(form.stageBar);
  };
  /** キー 1 つの入力欄 */
  const buildField = ({ id, kind, key, original, view, adding }) => {
    const fieldId = `pe-${id.replace(/[^A-Za-z0-9]/g, "")}-${key}`;
    const pending = adding ? null : editOfKey(id, "set", key);
    const label = key === "title" && kind === "terms" ? "用語" : KEY_LABELS[key];
    const wrap = el("div", { class: `pe-field${pending ? " is-pending" : ""}${pending?.blocked ? " is-blocked" : ""}`, "data-key": key });
    const labelRow = el("div", { class: "pe-label-row" }, el("label", { for: fieldId }, label, key === "title" ? el("span", { class: "pe-req" }, "必須") : null));
    if (pending !== null) labelRow.append(mark(pending.blocked ? "blocked" : "edit", true));
    wrap.append(labelRow);
    const value = key === "body" ? (adding ? (original.body ?? "") : (mockBody(id, view) ?? "")) : view[key];
    const originalValue = key === "body" ? (adding ? "" : mockBody(id, original, true) ?? "") : original[key];
    /** 入力した値を保存待ちに入れる（溜める時点の案 A では入力欄を離れたとき、B では「保存待ちに入れる」で） */
    const commit = (next) => {
      // 空のタイトルは溜めず、入力の誤りを出したままにする
      if (key === "title" && next.trim() === "") return;
      if (stage === "b") {
        ui.dirty = true;
        wrap.classList.add("is-dirty");
        return;
      }
      if (adding) {
        updateAdd(id, key, next);
        return;
      }
      if (putEdit({ target: id, op: "set", key, value: next, original: originalValue })) announce(`${id} の${label}を保存待ちに入れました`);
      decorate();
      refreshField(wrap, id, key);
    };
    let control;
    if (key === "status" || key === "confidence" || key === "target" || key === "category" || key === "phase") {
      const options = {
        status: KINDS[kind].statuses ?? [],
        confidence: ["高", "中", "低"],
        target: base.settings.targets.map((target) => target.name),
        category: base.settings.categories.map((category) => category.name),
        phase: base.settings.phases,
      }[key];
      control = el("select", { id: fieldId, name: key, class: "input" }, ...options.map((option) => el("option", { value: option, selected: option === value }, option)));
      control.addEventListener("change", () => commit(control.value));
    } else if (key === "withdrawn" || key === "deliverable") {
      control = el("input", { id: fieldId, name: key, type: "checkbox", checked: value === true });
      control.addEventListener("change", () => commit(control.checked));
      wrap.classList.add("pe-check");
    } else if (LIST_KEYS.has(key)) {
      control = buildChips({ fieldId, key, label, value: value ?? [], onChange: commit });
    } else if (LONG_KEYS.has(key)) {
      control = el("textarea", { id: fieldId, name: key, class: `input pe-text${key === "body" ? " pe-body" : ""}`, rows: key === "body" ? 8 : 3 });
      control.value = value ?? "";
      control.addEventListener("change", () => commit(control.value));
    } else {
      control = el("input", { id: fieldId, name: key, class: "input", type: key === "date" ? "date" : "text", value: value ?? "", autocomplete: "off" });
      control.addEventListener("change", () => commit(control.value));
    }
    if (key === "title") {
      control.setAttribute("required", "");
      control.dataset.first = "";
      const error = el("p", { class: "pe-error", id: `${fieldId}-error` }, icon("warn"), "タイトルを書いてください。");
      control.setAttribute("aria-describedby", error.id);
      control.addEventListener("blur", () => {
        const empty = control.value.trim() === "";
        control.toggleAttribute("aria-invalid", empty);
        wrap.classList.toggle("is-invalid", empty);
      });
      wrap.append(control, error);
    } else {
      wrap.append(control);
    }
    if (pending?.blocked) wrap.append(blockedNote(pending));
    return wrap;
  };
  /** 本文の今の値（元の本文は data.js の本文のファイル） */
  const mockBody = (id, item, original = false) => {
    const pending = original ? null : editOfKey(id, "set", "body");
    if (pending !== null) return pending.value;
    return base.bodies?.[item.body ?? bodyKey(id)] ?? "";
  };
  /** 溜めた後に入力欄の印を出し直す */
  const refreshField = (wrap, id, key) => {
    const pending = editOfKey(id, "set", key);
    wrap.classList.toggle("is-pending", pending !== null);
    wrap.querySelector(".pe-label-row .pm")?.remove();
    if (pending !== null) wrap.querySelector(".pe-label-row").append(mark("edit", true));
  };
  /** 値を並べるキーの入力（チップと、足す入力欄） */
  const buildChips = ({ fieldId, key, label, value, onChange }) => {
    const placeholder = key === "tags" ? "語彙から選ぶ" : ["depends_on", "related"].includes(key) ? "ID を入れる" : `${label}を入れる`;
    let current = [...value];
    const box = el("div", { class: "pe-chips", role: "group", "aria-labelledby": `${fieldId}-label` });
    const listId = `${fieldId}-list`;
    const draw = () => {
      box.replaceChildren(
        ...current.map((entry) => el("span", { class: `tag pe-chip${key === "tags" ? "" : " mono"}` }, entry,
          el("button", { class: "pe-chip-x", type: "button", "aria-label": `${entry} を外す`, onclick: () => {
            current = current.filter((other) => other !== entry);
            draw();
            onChange(current);
          } }, icon("close")))),
        input,
        ...(key === "tags" ? [el("datalist", { id: listId }, ...vocabulary().map((tag) => el("option", { value: tag })))] : []),
      );
    };
    const input = el("input", { id: fieldId, class: "input pe-chip-input", type: "text", list: key === "tags" ? listId : null, placeholder: placeholder, "aria-label": `${label}を追加`, autocomplete: "off" });
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.isComposing) return;
      event.preventDefault();
      const text = input.value.trim();
      if (text === "" || current.includes(text)) return;
      current = [...current, text];
      input.value = "";
      draw();
      onChange(current);
      box.querySelector(".pe-chip-input").focus();
    });
    draw();
    return box;
  };
  /** 検討事項の案（1 案ごとに書き換え・消す。採用する案の切り替えと、案を足す） */
  const buildOptions = (id, original, view) => {
    const section = el("fieldset", { class: "pe-field pe-options", "data-key": "options" }, el("legend", {}, "案"));
    const adopted = (view.options ?? []).find((option) => option.adopted)?.key ?? null;
    const removed = edits.filter((edit) => edit.target === id && edit.op === "option-remove").map((edit) => edit.key);
    const all = [...(view.options ?? []), ...removed.map((key) => original.options.find((option) => option.key === key))];
    for (const option of all) {
      const isRemoved = removed.includes(option.key);
      const pending = edits.find((edit) => edit.target === id && edit.key === option.key && edit.op.startsWith("option")) ?? null;
      const adoptPending = edits.find((edit) => edit.target === id && edit.op === "adopt" && edit.value === option.key) ?? null;
      const textId = `pe-${id.replace(/[^A-Za-z0-9]/g, "")}-opt-${option.key}`;
      const row = el("div", { class: `pe-opt${pending || adoptPending ? " is-pending" : ""}${isRemoved ? " is-removed" : ""}` });
      const head = el("div", { class: "pe-opt-head" },
        el("label", { class: "key", for: textId }, option.key, srOnly(" の案")),
        el("label", { class: "pe-adopt" },
          el("input", { type: "radio", name: `${id}-adopt`, value: option.key, checked: adopted === option.key, disabled: isRemoved, onchange: () => {
            const originalAdopted = original.options.find((entry) => entry.adopted)?.key ?? null;
            putEdit({ target: id, op: "adopt", key: "adopted", value: option.key, original: originalAdopted });
            const found = editOfKey(id, "adopt", "adopted");
            if (found !== null) found.key = option.key;
            keep();
            announce(`${id} の採用する案を ${option.key} にしました`);
            decorate();
            section.replaceWith(buildOptions(id, original, applied().decisions.find((item) => item.id === id)));
          } }), "採用"),
        pending || adoptPending ? mark("edit", true) : null,
        el("span", { class: "spacer" }),
        isRemoved
          ? el("button", { class: "btn ghost", type: "button", onclick: () => {
            undo(pending.id);
            decorate();
            section.replaceWith(buildOptions(id, original, applied().decisions.find((item) => item.id === id)));
          } }, icon("undo"), "削除を取り消す")
          : el("button", { class: "icon-btn", type: "button", "aria-label": `案 ${option.key} を削除`, title: `案 ${option.key} を削除`, onclick: () => {
            const added = editOfKey(id, "option-add", option.key);
            if (added !== null) undo(added.id);
            else putEdit({ target: id, op: "option-remove", key: option.key, value: null, original: undefined });
            announce(`${id} の案 ${option.key} の削除を保存待ちに入れました`);
            decorate();
            section.replaceWith(buildOptions(id, original, applied().decisions.find((item) => item.id === id)));
          } }, icon("trash")));
      const text = el("textarea", { id: textId, class: "input pe-text", rows: 2, disabled: isRemoved });
      text.value = option.content;
      text.addEventListener("change", () => {
        if (stage === "b") {
          ui.dirty = true;
          return;
        }
        const added = editOfKey(id, "option-add", option.key);
        if (added !== null) {
          added.value = text.value;
          keep();
        } else {
          putEdit({ target: id, op: "option-edit", key: option.key, value: text.value, original: original.options.find((entry) => entry.key === option.key)?.content });
        }
        announce(`${id} の案 ${option.key} を保存待ちに入れました`);
        decorate();
      });
      row.append(head, text);
      section.append(row);
    }
    section.append(el("button", { class: "btn pe-opt-add", type: "button", onclick: () => {
      const keys = [...original.options.map((option) => option.key), ...edits.filter((edit) => edit.target === id && edit.op === "option-add").map((edit) => edit.key)];
      const next = String.fromCharCode(Math.max(...keys.map((key) => key.charCodeAt(0))) + 1);
      putEdit({ target: id, op: "option-add", key: next, value: "", original: undefined });
      decorate();
      const fresh = buildOptions(id, original, applied().decisions.find((item) => item.id === id));
      section.replaceWith(fresh);
      fresh.querySelector(`#pe-${id.replace(/[^A-Za-z0-9]/g, "")}-opt-${next}`)?.focus();
    } }, icon("plus"), "案を追加"));
    return section;
  };
  /** 「保存待ちに入れる」の案: 開いている項目の入力をまとめて溜める */
  const stageAll = (form, id) => {
    if (id.startsWith("new:")) {
      const title = form.querySelector('[name="title"]').value.trim();
      if (title === "") {
        form.querySelector('[name="title"]').focus();
        form.querySelector('[data-key="title"]').classList.add("is-invalid");
        return;
      }
      for (const key of ["title", "status", "body"]) {
        const control = form.querySelector(`[name="${key}"]`);
        if (control !== null) updateAdd(id, key, control.value, true);
      }
    } else {
      const original = itemOf(id);
      for (const field of form.querySelectorAll(".pe-field.is-dirty")) {
        const key = field.dataset.key;
        const control = field.querySelector("select, textarea, input:not(.pe-chip-input)");
        const next = control.type === "checkbox" ? control.checked : control.value;
        putEdit({ target: id, op: "set", key, value: next, original: key === "body" ? mockBody(id, original, true) : original[key] });
        field.classList.remove("is-dirty");
      }
    }
    ui.dirty = false;
    announce(`${id.startsWith("new:") ? "追加する項目" : id} の入力を保存待ちに入れました`);
    decorate();
  };
  /** 溜めた知らせを、開いている編集の表示に出す */
  const announce = (text) => {
    for (const node of document.querySelectorAll(".pe-form-msg")) node.textContent = `${text}（保存待ち ${edits.length} 件）`;
  };
  /** 書き込めない編集の理由 */
  const blockedNote = (edit) => {
    if (edit.blocked.reason === "changed") {
      return el("p", { class: "pe-blocked-note" }, icon("warn"), `溜めた後の ${jst(edit.blocked.at)} に AI がこの項目を書き換えたため、書き込めません。取り消してから入れ直してください。`);
    }
    const referrers = referrersOf(edit.target);
    return el("p", { class: "pe-blocked-note" }, icon("warn"),
      ...referrers.flatMap((ref, index) => [index > 0 ? "・" : "", el("button", { class: "idlink", type: "button", onclick: () => openItem(ref) }, ref)]),
      " が指しているため削除できません。指している項目から外してください。");
  };

  // ===== 項目を足す =====
  /** 種類の画面から、足す項目の入力を開く */
  const startAdd = (kind) => {
    ui.addKind = kind;
    newSeq += 1;
    const target = `new:${newSeq}`;
    ui.pendingAdd = target;
    openAdd(target);
  };
  /** 足す項目の入力を、詳細パネルと同じ置き方で開く */
  const openAdd = (target) => {
    const existing = edits.find((edit) => edit.target === target && edit.op === "item-add");
    if (existing !== undefined) ui.addKind = existing.key;
    ui.editing = target;
    if (openedId() !== null) go({ id: null });
    decorate();
    renderAddPanel();
    document.querySelector(".pe-add-panel [data-first]")?.focus();
  };
  /** 足す項目の入力のキーを溜める（タイトルを書いたときに 1 件の足す編集になる） */
  const updateAdd = (target, key, value, force = false) => {
    const found = edits.find((edit) => edit.target === target && edit.op === "item-add") ?? null;
    if (found === null) {
      if (key !== "title" || value.trim() === "") return;
      editSeq += 1;
      edits = [...edits, { id: `E-${editSeq}`, target, op: "item-add", key: ui.addKind, value: { title: value.trim(), status: KINDS[ui.addKind].first } }];
      announce(`${KINDS[ui.addKind].label}の追加を保存待ちに入れました`);
    } else {
      if (key === "title" && value.trim() === "" && !force) return;
      found.value = { ...found.value, [key]: value };
    }
    keep();
    decorate();
  };
  /** 足す項目の入力のパネル（app.js の詳細パネルと同じ形と置き場所） */
  const renderAddPanel = () => {
    let panel = document.querySelector(".pe-add-panel");
    const target = ui.editing;
    const show = target !== null && String(target).startsWith("new:") && !diffing && place === "a";
    if (!show) {
      if (panel !== null) {
        panel.remove();
        body.classList.remove("panel-open");
      }
      return;
    }
    if (panel !== null && panel.dataset.id === target) return;
    panel?.remove();
    const kind = ui.addKind;
    panel = el("aside", { class: "panel open pe-add-panel", "aria-label": `${KINDS[kind].label}を追加`, "data-id": target },
      el("div", { class: "panel-head" },
        el("button", { class: "icon-btn panel-back", type: "button", "aria-label": "一覧へ戻る", onclick: () => confirmLeave(closeAdd) }, icon("back")),
        el("span", { class: "panel-kind" }, el("span", { class: "panel-kind-label" }, `${KINDS[kind].label}を追加`)),
        el("span", { class: "spacer" }),
        el("button", { class: "icon-btn panel-close-x", type: "button", "aria-label": "追加の入力を閉じる", onclick: () => confirmLeave(closeAdd) }, icon("close"))),
      el("div", { class: "panel-scroll" }, el("div", { class: "panel-body", tabindex: "0", role: "region", "aria-label": "追加する項目の入力" }, buildForm(target, "panel"))));
    body.append(panel);
    placeStageBar(panel.querySelector(".pe-form"));
    body.classList.add("panel-open");
  };
  /** 足す項目の入力を閉じる（タイトルを書いていなければ何も溜めない） */
  const closeAdd = () => {
    ui.editing = null;
    renderAddPanel();
    decorate();
  };

  // ===== 項目を開く =====
  /** 項目を詳細パネルで開く（保存待ちのパネルから開いたかを覚える） */
  const openItem = (id, fromPending = false) => {
    ui.fromPending = fromPending;
    if (ui.editing !== null && String(ui.editing).startsWith("new:")) closeAdd();
    const kind = kindOf(id);
    const tab = { research: "research", terms: "terms", notes: "notes", logs: "logs" }[kind] ?? kind;
    ui.wsOpen = false;
    go({ tab, id });
    if (fromPending && matchMedia("(max-width: 900px)").matches) {
      ui.pendingOpen = false;
      decorate();
    }
  };
  // 幅 900px 以下で保存待ちのパネルから開いた項目を閉じたら、保存待ちのパネルへ戻る
  addEventListener("hashchange", () => {
    if (openedId() === null && ui.fromPending && matchMedia("(max-width: 900px)").matches && !diffing) {
      ui.fromPending = false;
      ui.pendingOpen = true;
    }
    if (ui.editing !== null && !String(ui.editing).startsWith("new:") && openedId() !== ui.editing && place === "a") {
      ui.editing = null;
      publish(true);
    }
    decorate();
  });

  // ===== 保存待ちのパネル =====
  /** 保存待ちのパネルを開閉する（コメントの一覧・表示の設定とは片方だけを開く） */
  const togglePending = () => {
    ui.pendingOpen = !ui.pendingOpen;
    if (ui.pendingOpen) {
      document.querySelector(".comments-panel.open:not(.pending-panel) [data-focus='close']")?.click();
      document.querySelector(".settings-drawer.open [data-focus='close']")?.click();
    }
    decorate();
    if (ui.pendingOpen) document.querySelector(".pending-panel h2")?.focus();
    else document.querySelector(".pending-btn")?.focus();
  };
  /** 項目の呼び名（種類と ID とタイトル） */
  const describe = (target) => {
    if (target === "settings") return { kind: "設定", id: null, title: base.settings.summary };
    const add = edits.find((edit) => edit.target === target && edit.op === "item-add");
    if (add !== undefined) return { kind: `${KINDS[add.key].label}を追加`, id: null, title: add.value.title };
    const item = itemOf(target);
    return { kind: KINDS[kindOf(target)].label, id: target, title: applied()[kindOf(target)].find((entry) => entry.id === target)?.title ?? item.title };
  };
  /** 1 件の編集の中身の 1 行（何を・どう変えるか） */
  const describeEdit = (edit) => {
    if (edit.op === "item-add") return { what: "項目を追加", change: edit.value.title };
    if (edit.op === "item-remove") return { what: "項目を削除", change: null };
    if (edit.op === "setting") return { what: SETTING_LABELS[edit.key], change: [flat(base.settings[edit.key]), flat(edit.value)] };
    if (edit.op === "option-add") return { what: `案 ${edit.key} を追加`, change: flat(edit.value) };
    if (edit.op === "option-remove") return { what: `案 ${edit.key} を削除`, change: null };
    if (edit.op === "option-edit") return { what: `案 ${edit.key}`, change: [flat(itemOf(edit.target).options.find((option) => option.key === edit.key)?.content), flat(edit.value)] };
    if (edit.op === "adopt") return { what: "採用する案", change: [flat(itemOf(edit.target).options.find((option) => option.adopted)?.key ?? "なし"), edit.value] };
    const original = edit.key === "body" ? "（今の本文）" : itemOf(edit.target)[edit.key];
    return { what: KEY_LABELS[edit.key], change: edit.key === "body" ? null : [flat(original), flat(edit.value)] };
  };
  /** 保存待ちのパネルを描く */
  const renderPending = () => {
    let panel = document.querySelector(".pending-panel");
    if (diffing) {
      panel?.remove();
      return;
    }
    if (panel === null) {
      panel = el("aside", { class: "comments-panel pending-panel", "aria-label": "保存待ちの編集", id: "pending-panel" });
      body.append(panel);
    }
    panel.classList.toggle("open", ui.pendingOpen);
    const signature = JSON.stringify([edits, saveState, ui.pendingOpen]);
    if (panel.dataset.sig === signature) return;
    panel.dataset.sig = signature;
    // 閉じている間は中身を持たない（隠れた文字を読み上げ・検索に残さない）
    if (!ui.pendingOpen) {
      panel.replaceChildren();
      return;
    }
    const focusedUndo = document.activeElement?.closest?.(".pending-panel") !== null ? document.activeElement?.dataset?.focus : null;

    const removals = edits.filter((edit) => edit.op === "item-remove");
    const head = el("div", { class: "comments-head" },
      el("h2", { tabindex: "-1" }, "保存待ち", el("span", { class: "count" }, `${edits.length} 件`)),
      el("span", { class: "spacer" }),
      el("button", { class: "icon-btn", type: "button", "aria-label": "保存待ちの編集を閉じる", "data-focus": "close", onclick: () => togglePending() }, icon("close")));
    const list = el("div", { class: "comments-body pe-list" });
    // 保存の結果の知らせ（書き込めない・つながらない）
    if (saveState === "blocked") {
      const blocked = edits.filter((edit) => edit.blocked);
      list.append(el("div", { class: "pe-alert", role: "alert" },
        el("p", { class: "pe-alert-title" }, icon("warn"), `${blocked.length} 件の編集を書き込めないため、何も保存していません。`),
        el("ul", {}, ...blocked.map((edit) => {
          const who = describe(edit.target);
          return el("li", {}, el("a", { href: `#pe-row-${edit.id}`, onclick: (event) => {
            event.preventDefault();
            document.getElementById(`pe-row-${edit.id}`)?.querySelector("button")?.focus();
          } }, `${who.id ?? who.kind} の${describeEdit(edit).what}`));
        })),
        el("p", { class: "pe-alert-next" }, "書き込めない編集を取り消してから、もう一度保存してください。")));
    }
    if (saveState === "offline") {
      list.append(el("div", { class: "pe-alert", role: "alert" },
        el("p", { class: "pe-alert-title" }, icon("warn"), "サーバーにつながらないため、保存できませんでした。"),
        el("p", { class: "pe-alert-next" }, "保存待ちの編集は残っています。サーバーを立ち上げ直してから、もう一度保存してください。")));
    }
    if (edits.length === 0) {
      list.append(el("p", { class: "comments-empty" }, icon("pending"), "保存待ちの編集はありません。"));
    }
    /** 編集を項目ごとにまとめた節 */
    const groupsOf = (subset) => {
      const order = [...new Set(subset.map((edit) => edit.target))];
      return order.map((target) => {
        const who = describe(target);
        const rows = subset.filter((edit) => edit.target === target);
        const openTarget = () => {
          if (target === "settings") openWorkspace();
          else if (target.startsWith("new:")) openAdd(target);
          else openItem(target, true);
        };
        return el("section", { class: `pe-group${rows.some((edit) => edit.blocked) ? " is-blocked" : ""}` },
          el("h3", { class: "pe-group-head" },
            el("button", { class: "pe-open", type: "button", onclick: openTarget, "aria-label": `${who.id ?? who.kind}「${who.title}」を開く` },
              el("span", { class: "pe-kind" }, who.kind), who.id !== null ? el("span", { class: "mono" }, who.id) : null, el("span", { class: "pe-title" }, who.title))),
          el("ul", { class: "pe-rows" }, ...rows.map((edit) => {
            const text = describeEdit(edit);
            const name = `${who.id ?? who.kind} の${text.what}`;
            return el("li", { class: `pe-row${edit.blocked ? " is-blocked" : ""}${edit.op === "item-remove" ? " is-remove" : ""}`, id: `pe-row-${edit.id}` },
              el("div", { class: "pe-row-main" },
                el("span", { class: "pe-what" }, edit.op === "item-remove" ? icon("trash") : null, text.what),
                text.change === null ? null
                  : Array.isArray(text.change)
                    ? el("span", { class: "pe-change" }, el("del", {}, srOnly("前: "), text.change[0]), el("span", { class: "pe-arrow", "aria-hidden": "true" }, "→"), el("ins", {}, srOnly("後: "), text.change[1]))
                    : el("span", { class: "pe-change" }, el("ins", {}, text.change)),
                edit.blocked ? blockedNote(edit) : null),
              el("button", { class: "btn ghost pe-undo", type: "button", "data-focus": `undo:${edit.id}`, "aria-label": `${name}の編集を取り消す`, onclick: () => {
                undo(edit.id);
                publish(true);
                decorate();
                // 取り消した行の次の行（無ければ見出し）へフォーカスを移す
                (document.querySelector(".pending-panel .pe-undo") ?? document.querySelector(".pending-panel h2")).focus();
              } }, icon("undo"), el("span", { class: "lbl" }, "取り消す")));
          })));
      });
    };
    if (delStyle === "b" && removals.length > 0) {
      list.append(el("h3", { class: "pe-sec-head" }, icon("trash"), `削除する項目（${removals.length} 件）`), ...groupsOf(removals),
        el("h3", { class: "pe-sec-head" }, `変更・追加する項目（${edits.length - removals.length} 件）`), ...groupsOf(edits.filter((edit) => edit.op !== "item-remove")));
    } else {
      list.append(...groupsOf(edits));
    }
    // まとめて保存する
    const saving = saveState === "saving";
    const label = saving ? "保存しています…" : delStyle === "a" && removals.length > 0 ? `まとめて保存する（${removals.length} 件を削除）` : "まとめて保存する";
    const foot = el("div", { class: "comments-free pe-foot" },
      el("p", { class: "pe-foot-sum" }, `${edits.length} 件${removals.length > 0 ? `（うち削除 ${removals.length} 件）` : ""}をワークスペースに書きます`),
      el("button", { class: "btn primary pe-save", type: "button", disabled: saving || edits.length === 0, "aria-busy": saving ? "true" : null, onclick: () => save() },
        saving ? el("span", { class: "pe-spin" }, icon("spin")) : icon("save"), label));
    panel.replaceChildren(head, list, foot);
    if (focusedUndo) panel.querySelector(`[data-focus="${focusedUndo}"]`)?.focus();
  };

  // ===== まとめて保存する =====
  /** 保存する（見本で、書き込めない編集・つながらない・全て書けるを分ける） */
  const save = () => {
    if (edits.length === 0 || saveState === "saving") return;
    saveState = "saving";
    decorate();
    setTimeout(() => {
      if (sample === "offline") {
        saveState = "offline";
        ui.pendingOpen = true;
        decorate();
        return;
      }
      const blocked = edits.filter((edit) => edit.blocked !== undefined || (edit.op === "item-remove" && referrersOf(edit.target).length > 0 && !edit.blocked));
      for (const edit of blocked) edit.blocked ??= { reason: "referenced" };
      if (blocked.length > 0) {
        saveState = "blocked";
        ui.pendingOpen = true;
        keep();
        decorate();
        document.querySelector(".pending-panel .pe-alert")?.setAttribute("tabindex", "-1");
        document.querySelector(".pending-panel .pe-alert")?.focus();
        return;
      }
      // 全て書けた: 保存待ちの編集を元の記録に当て、足す項目に ID を振り、消す項目を外す
      const count = edits.length;
      const next = applied();
      for (const edit of edits) {
        if (edit.op === "item-add") {
          const list = next[edit.key];
          const seq = Math.max(...list.map((item) => Number(item.id.split("-")[1]))) + 1;
          list.push({ id: `${KINDS[edit.key].prefix}-${seq}`, ...edit.value, tags: [], created: new Date().toISOString(), updated: new Date().toISOString(), updated_by: "user" });
        }
        if (edit.op === "item-remove") next[edit.key] = next[edit.key].filter((item) => item.id !== edit.target);
      }
      for (const target of new Set(edits.map((edit) => edit.target))) {
        const kind = kindOf(target);
        const item = kind === null ? null : next[kind].find((entry) => entry.id === target);
        if (item) {
          item.updated_by = "user";
          item.updated = new Date().toISOString();
        }
      }
      base = next;
      server.records = next;
      edits = [];
      keep();
      saveState = null;
      ui.pendingOpen = false;
      ui.editing = null;
      ui.toast = `${count} 件を保存しました。`;
      publish(true);
      decorate();
    }, 900);
  };
  /** 保存した知らせ（短い完了の知らせだけを自動で消す） */
  const renderToast = () => {
    let toast = document.querySelector(".pe-toast");
    if (ui.toast === null) {
      toast?.remove();
      return;
    }
    if (toast === null) {
      toast = el("div", { class: "pe-toast", role: "status" }, icon("check"), el("span", {}, ui.toast));
      body.append(toast);
      setTimeout(() => {
        ui.toast = null;
        decorate();
      }, 5000);
    }
  };

  // ===== 表示の設定のパネル（設定の画面の入口） =====
  /** 表示の設定のパネルに、設定の画面の入口を置く（案 A: 下端 / 案 B: 狭い幅の題名の代わり / 案 D: タブ） */
  const decorateDrawer = () => {
    const drawer = document.querySelector(".settings-drawer");
    if (drawer === null) return;
    const wrap = drawer.querySelector(".st-wrap");
    if (wrap === null) return;
    const showEntry = !diffing && (entry === "a" || entry === "b");
    let section = drawer.querySelector(".pe-ws-entry");
    if (!showEntry) section?.remove();
    else if (section === null) {
      section = el("div", { class: `pe-ws-entry${entry === "b" ? " pe-narrow-only" : ""}` },
        el("h3", {}, "ワークスペースの設定"),
        el("p", { class: "pe-ws-sum" }, "題名・フェーズ・ゴール・対象・カテゴリー・タグの語彙"),
        el("button", { class: "btn", type: "button", onclick: () => openWorkspace() }, icon("pencil"), "設定を編集する"));
      wrap.append(section);
    }
    // 案 D: 表示の設定のパネルの頭にタブを置き、ワークスペースの設定を同じパネルで書き換える
    if (entry !== "d" || diffing) return;
    let tabs = drawer.querySelector(".pe-drawer-tabs");
    if (tabs === null) {
      tabs = el("div", { class: "segment pe-drawer-tabs", role: "tablist", "aria-label": "表示の設定の中身" },
        el("button", { type: "button", role: "tab", "data-tab": "view", onclick: () => {
          ui.drawerTab = "view";
          decorate();
        } }, "この端末の表示"),
        el("button", { type: "button", role: "tab", "data-tab": "ws", onclick: () => {
          ui.drawerTab = "ws";
          decorate();
        } }, "ワークスペースの設定"));
      drawer.querySelector(".comments-head").after(tabs);
    }
    for (const tab of tabs.querySelectorAll("button")) tab.setAttribute("aria-selected", String(tab.dataset.tab === ui.drawerTab));
    wrap.classList.toggle("pe-hide", ui.drawerTab !== "view");
    let inner = drawer.querySelector(".pe-drawer-ws");
    if (ui.drawerTab === "ws" && inner === null) {
      inner = el("div", { class: "pe-drawer-ws" }, buildWorkspaceForm(true));
      wrap.after(inner);
    }
    if (ui.drawerTab !== "ws") inner?.remove();
  };

  // ===== 設定の画面 =====
  /** 設定の画面を開く（表示の設定のパネルは閉じる） */
  const openWorkspace = () => {
    document.querySelector(".settings-drawer.open [data-focus='close']")?.click();
    if (matchMedia("(max-width: 900px)").matches) ui.pendingOpen = false;
    ui.wsOpen = true;
    decorate();
    document.querySelector(".pe-ws h1")?.focus();
  };
  /** 設定の画面を閉じ、元の画面へ戻る */
  const closeWorkspace = () => {
    confirmLeave(() => {
      ui.wsOpen = false;
      publish(true);
      decorate();
    });
  };
  /** 設定の 1 つのキーの入力を作る */
  const buildSetting = (key, compact) => {
    const settings = applied().settings;
    const pending = editOfKey("settings", "setting", key);
    const fieldId = `pe-ws-${key}${compact ? "-d" : ""}`;
    const wrap = el("div", { class: `pe-field${pending ? " is-pending" : ""}`, "data-key": key });
    const labelRow = el("div", { class: "pe-label-row" }, el("label", { for: fieldId, id: `${fieldId}-label` }, SETTING_LABELS[key]));
    if (pending !== null) labelRow.append(mark("edit", true));
    wrap.append(labelRow);
    /** 設定の値を保存待ちに入れる */
    const commit = (next) => {
      if (stage === "b") {
        ui.dirty = true;
        wrap.classList.add("is-dirty");
        return;
      }
      if (putEdit({ target: "settings", op: "setting", key, value: next, original: base.settings[key] })) announce(`設定の${SETTING_LABELS[key]}を保存待ちに入れました`);
      decorate();
      wrap.replaceWith(buildSetting(key, compact));
    };
    const value = settings[key];
    if (key === "summary" || key === "target_label") {
      const input = el("input", { id: fieldId, class: "input", type: "text", value: value ?? "", autocomplete: "off" });
      input.addEventListener("change", () => commit(input.value));
      if (key === "summary") input.dataset.first = "";
      wrap.append(input);
    } else if (key === "keep") {
      const input = el("input", { id: fieldId, class: "input pe-num", type: "number", min: "1", step: "1", inputmode: "numeric", value: value ?? 20 });
      input.addEventListener("change", () => commit(Number(input.value)));
      wrap.append(input, el("p", { class: "pe-hint" }, "変更履歴に残す書き換えのまとまりの数"));
    } else if (key === "playbooks" || key === "phases" || key === "tag_vocabulary") {
      wrap.append(buildChips({ fieldId, key: key === "tag_vocabulary" ? "vocabulary" : key, label: key === "tag_vocabulary" ? "タグ" : SETTING_LABELS[key], value: value ?? (key === "tag_vocabulary" ? vocabulary() : []), onChange: commit }));
    } else if (key === "goal") {
      const phase = el("select", { id: fieldId, class: "input" }, ...settings.phases.map((entry) => el("option", { value: entry, selected: entry === value.phase }, entry)));
      const summary = el("textarea", { id: `${fieldId}-summary`, class: "input pe-text", rows: 2 });
      summary.value = value.summary;
      const changeGoal = () => commit({ ...value, phase: phase.value, summary: summary.value });
      phase.addEventListener("change", changeGoal);
      summary.addEventListener("change", changeGoal);
      wrap.append(el("div", { class: "pe-sub" }, el("span", { class: "pe-sub-label" }, "届けるフェーズ"), phase),
        el("div", { class: "pe-sub" }, el("label", { class: "pe-sub-label", for: `${fieldId}-summary` }, "ゴールの中身"), summary),
        el("div", { class: "pe-sub" }, el("span", { class: "pe-sub-label" }, "納品物"),
          el("ul", { class: "pe-rowsx" }, ...value.deliverables.map((entry) => el("li", {}, el("span", { class: "mono" }, entry.doc), " ", entry.title)))));
    } else {
      // 対象・カテゴリー・関連する場所: 1 行ずつの表
      const columns = { targets: ["name", "summary"], categories: ["name", "target", "summary"], links: ["title", "url"] }[key];
      const heads = { name: "名前", summary: "説明", target: "対象", title: "表示名", url: "URL" };
      const table = el("table", { class: "pe-mini", "aria-labelledby": `${fieldId}-label` },
        el("thead", {}, el("tr", {}, ...columns.map((column) => el("th", { scope: "col" }, heads[column])), el("th", {}, srOnly("操作")))),
        el("tbody", {}, ...(value ?? []).map((row, index) => el("tr", {},
          ...columns.map((column) => el("td", {}, (() => {
            const input = el("input", { class: "input", type: column === "url" ? "url" : "text", value: row[column] ?? "", "aria-label": `${index + 1} 行目の${heads[column]}` });
            input.addEventListener("change", () => commit(value.map((entry, at) => (at === index ? { ...entry, [column]: input.value } : entry))));
            return input;
          })())),
          el("td", {}, el("button", { class: "icon-btn", type: "button", "aria-label": `${index + 1} 行目を削除`, onclick: () => commit(value.filter((_, at) => at !== index)) }, icon("trash")))))));
      wrap.append(el("div", { class: "pe-mini-wrap" }, table),
        el("button", { class: "btn pe-row-add", type: "button", onclick: () => commit([...(value ?? []), Object.fromEntries(columns.map((column) => [column, ""]))]) }, icon("plus"), `${SETTING_LABELS[key]}を追加`));
    }
    return wrap;
  };
  /** 設定の入力を並べる（compact: 表示の設定のパネルの中の案 D） */
  const buildWorkspaceForm = (compact) => {
    const form = el("form", { class: `pe-form pe-ws-form${compact ? " is-compact" : ""}`, novalidate: true, "aria-label": "ワークスペースの設定" });
    form.addEventListener("submit", (event) => event.preventDefault());
    const groups = [
      ["話し合い", ["summary", "playbooks", "goal"]],
      ["進め方", ["phases", "target_label", "targets", "categories"]],
      ["タグと関連", ["tag_vocabulary", "links"]],
      ["変更履歴", ["keep"]],
    ];
    for (const [title, keys] of groups) {
      form.append(el("fieldset", { class: "pe-ws-group" }, el("legend", {}, title), ...keys.map((key) => buildSetting(key, compact))));
    }
    form.append(el("p", { class: "pe-form-msg", role: "status" }));
    return form;
  };
  /** 設定の画面（別の画面。開いている間は本文の区画を置き換える） */
  const renderWorkspace = () => {
    let screen = document.querySelector(".pe-ws");
    const main = document.getElementById("main");
    const show = ui.wsOpen && !diffing;
    body.classList.toggle("pe-ws-open", show);
    if (!show) {
      screen?.remove();
      if (main !== null && !ui.editScreen) main.hidden = false;
      return;
    }
    // 本文の区画が描かれる前は待つ
    if (main === null) return;
    main.hidden = true;
    if (screen !== null) return;
    screen = el("main", { class: "content pe-ws pe-screen" },
      el("div", { class: "pe-screen-head" },
        el("h1", { tabindex: "-1" }, "設定"),
        el("span", { class: "spacer" }),
        el("button", { class: "btn", type: "button", onclick: () => closeWorkspace() }, icon("close"), "閉じる")),
      buildWorkspaceForm(false));
    main.after(screen);
  };

  // ===== 編集を別の画面にする案 B =====
  /** 編集の画面（開いている間は本文の区画と詳細パネルを置き換える） */
  const renderEditScreen = () => {
    const main = document.getElementById("main");
    let screen = document.querySelector(".pe-edit-screen");
    const target = ui.editing;
    const show = place === "b" && target !== null && target !== "route" && !diffing;
    ui.editScreen = show;
    body.classList.toggle("pe-edit-open", show);
    if (!show) {
      screen?.remove();
      if (main !== null && !ui.wsOpen) main.hidden = false;
      return;
    }
    if (main === null) return;
    main.hidden = true;
    if (screen !== null && screen.dataset.id === target) return;
    screen?.remove();
    const adding = String(target).startsWith("new:");
    const who = adding ? { kind: `${KINDS[ui.addKind].label}を追加`, id: null, title: "" } : describe(target);
    screen = el("main", { class: "content pe-edit-screen pe-screen", "data-id": target },
      el("div", { class: "pe-screen-head" },
        el("button", { class: "icon-btn", type: "button", "aria-label": "一覧へ戻る", onclick: () => toggleEdit(target) }, icon("back")),
        el("h1", { tabindex: "-1" }, adding ? who.kind : el("span", {}, el("span", { class: "mono" }, who.id), ` ${who.title} を編集`)),
        el("span", { class: "spacer" }),
        el("button", { class: "btn", type: "button", "aria-pressed": "true", onclick: () => toggleEdit(target) }, icon("pencil"), "編集を終える")),
      buildForm(target, "screen"));
    main.after(screen);
    placeStageBar(screen.querySelector(".pe-form"));
  };

  // ===== モックの操作 =====
  // 見本の保存待ちに戻す: この端末に残した保存待ちの編集を消し、見本の状態で開き直す
  document.querySelector('.mockbar [data-mock-act="reset"]')?.addEventListener("click", () => {
    for (const key of Object.keys(sessionStorage).filter((name) => name.startsWith("mock-325-"))) sessionStorage.removeItem(key);
    location.reload();
  });

  // ===== 起動 =====
  publish(false);
  observe();
  decorate();
  // 見本: 表示の設定のパネルを開いて始める・足す項目の入力で始める
  const waitFor = (selector, callback) => {
    const timer = setInterval(() => {
      const found = document.querySelector(selector);
      if (found === null) return;
      clearInterval(timer);
      callback(found);
    }, 50);
  };
  // 撮影用: mark に渡した CSS セレクタの要素に赤枠を付ける（詳細の全画面のような最前面の面の中でも見える枠）
  const markSelector = params.get("mark");
  if (markSelector !== null) {
    new MutationObserver(() => {
      for (const target of document.querySelectorAll(markSelector)) target.classList.add("mock-mark");
    }).observe(body, { childList: true, subtree: true });
  }
  if (given("sp") === "1") waitFor(".settings-btn", (button) => button.click());
  if (given("add") !== null && !diffing) waitFor(".pe-add", () => startAdd(given("add")));
  if (ui.editing === "route" && place === "b") waitFor("#main .screen", () => {
    ui.editing = openedId();
    go({ id: null });
  });
})();
