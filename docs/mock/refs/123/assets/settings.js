// 表示の設定のパネルと、ワークスペースの既定として保存する前の確かめの中身を組む
// 画面のモック（app.js）と部品のモック（components/settings-panel）が同じ組み方を使う
(() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const ICONS = {
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    alert: '<path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17h.01"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    save: '<path d="M5 4h11l3 3v13H5Z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
    network: '<path d="M4 18.5 10 13.5l5 3M10 13.5 7.5 6.5M15 16.5l3.2-6.6" stroke-width="1.15"/><circle cx="4" cy="18.5" r="2" fill="currentColor" stroke="none"/><circle cx="10" cy="13.5" r="2.2" fill="currentColor" stroke="none"/><circle cx="15" cy="16.5" r="1.8" fill="currentColor" stroke="none"/><circle cx="7.5" cy="6.5" r="1.8" fill="currentColor" stroke="none"/><path d="m19 1.8 1.05 3.15L23.2 6l-3.15 1.05L19 10.2l-1.05-3.15L14.8 6l3.15-1.05Z" fill="currentColor" stroke="none"/>',
    decision: '<circle cx="12" cy="12" r="8"/><path d="m9 12 2 2 4-4"/>',
    task: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    research: '<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/><path d="M8 10.5h5"/>',
    doc: '<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v4h4"/>',
    term: '<path d="M4 5h11a3 3 0 0 1 3 3v12H7a3 3 0 0 1-3-3Z"/><path d="M4 17a3 3 0 0 1 3-3h11"/>',
    note: '<path d="M5 4h14v12l-4 4H5Z"/><path d="M15 20v-4h4"/>',
    log: '<path d="M4 6h16v10H9l-5 4Z"/>',
  };
  const icon = (n) => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n]}</svg>`;

  // ネットワークの見た目: 値・名前・中身の短い説明（上書きの一覧と確かめに名前を出す）
  const LOOKS = [
    { key: "glow", label: "グロウ", note: "玉と流れる光に、やわらかい光のにじみ" },
    { key: "starlight", label: "星の光", note: "白い芯と色の光。明るい星に十字の光条" },
    { key: "constellation", label: "星図", note: "回転に合わせて回る天球の経緯線" },
    { key: "deep", label: "深宇宙", note: "星空と星雲の地に、光のにじむ星" },
    { key: "dust", label: "星屑", note: "色を抜いた細かな点と細い線" },
  ];
  // 組み込みの既定: ワークスペースの既定も個人の上書きも無いときの値
  const BUILTIN_LOOK = "deep";
  // 表示する種類を選べる画面。概要とネットワークは選べず、常に出す
  const KINDS = [
    { key: "decisions", label: "検討事項", icon: "decision" },
    { key: "tasks", label: "タスク", icon: "task" },
    { key: "research", label: "調査", icon: "research" },
    { key: "docs", label: "資料", icon: "doc" },
    { key: "terms", label: "用語集", icon: "term" },
    { key: "notes", label: "メモ", icon: "note" },
    { key: "logs", label: "会話ログ", icon: "log" },
  ];
  const THEMES = [["system", "端末に合わせる"], ["light", "ライト"], ["dark", "ダーク"]];
  const lookLabel = (k) => LOOKS.find((l) => l.key === k).label;
  // 表示する種類を、外した種類の名前で書く（全て出すときは「すべて表示」）
  const kindsText = (shown) => {
    const off = KINDS.filter((k) => !shown.has(k.key)).map((k) => k.label);
    return off.length ? `${off.join("・")}を表示しない` : "すべて表示";
  };
  const sameSet = (a, b) => a.size === b.size && [...a].every((x) => b.has(x));

  // ライト / ダーク（パネルにも置く案だけ）: 端末に合わせるを含む 3 つのセグメント
  const themeField = (m) => `<fieldset class="st-sec"><legend>ライト / ダーク</legend><div class="st-seg">${THEMES.map(([v, l]) =>
    `<label><input type="radio" name="${m.p}theme" value="${v}" data-act="stheme" ${m.theme === v ? "checked" : ""}><span>${l}</span></label>`).join("")}</div></fieldset>`;
  // 表示する種類: 先頭にまとめて選ぶチェック、概要とネットワークは常に出す行にする
  const kindsField = (m) => {
    const n = KINDS.filter((k) => m.shown.has(k.key)).length;
    const always = (key, label, ic) => `<li class="st-always"><span class="st-always-box">${icon("check")}</span>${icon(ic)}<span class="st-k-label">${label}</span><span class="st-always-note">常に表示</span></li>`;
    return `<fieldset class="st-sec"><legend>表示する種類</legend><ul class="st-kinds">
      <li class="st-all"><label><input type="checkbox" data-act="skindall" ${n === KINDS.length ? "checked" : ""} data-mixed="${n > 0 && n < KINDS.length ? 1 : 0}"><span class="st-k-label">すべて</span><span class="n mono">${n}/${KINDS.length}</span></label></li>
      ${always("overview", "概要", "home")}
      ${KINDS.map((k) => `<li><label><input type="checkbox" data-act="skind" value="${k.key}" ${m.shown.has(k.key) ? "checked" : ""}>${icon(k.icon)}<span class="st-k-label">${k.label}</span><span class="n mono">${m.counts[k.key] ?? ""}</span></label></li>`).join("")}
      ${always("graph", "ネットワーク", "network")}
    </ul></fieldset>`;
  };
  // 既定に戻す: この端末で変えている項目を並べ、全ての上書きを外す。上書きが無いときはボタンを出さない
  const resetBlock = (m) => `<div class="st-reset">${m.overrides.length
    ? `<p class="st-over"><span class="st-over-h">この端末で変えている項目</span><span>${m.overrides.map(esc).join("・")}</span></p><button class="btn" type="button" data-act="sreset">${icon("undo")}既定に戻す</button>`
    : `<p class="st-over st-none" id="${m.p}over" tabindex="-1">ワークスペースの既定のまま表示しています。</p>`}</div>`;
  // 案 A: 今の選びをワークスペースの既定にするボタン。既定と同じ選びのときはボタンを出さない
  const saveButton = (m) => {
    const differs = m.look !== m.defLook || !sameSet(m.shown, m.defShown);
    return `<div class="st-save">${differs
      ? `<button class="btn" type="button" data-act="ssave" aria-haspopup="dialog">${icon("save")}ワークスペースの既定にする</button>`
      : `<p class="st-same" id="${m.p}same" tabindex="-1">今の選びはワークスペースの既定と同じです。</p>`}</div>`;
  };
  // 案 B: ワークスペースの既定を別の区画で選び、区画の中の保存ボタンで保存する
  const wsSection = (m) => {
    const differs = m.ws.look !== m.defLook || !sameSet(m.ws.shown, m.defShown);
    return `<p class="st-part st-part-ws">ワークスペースの既定</p>
      <div class="st-ws">
        <label class="st-field"><span>ネットワークの見た目</span><select data-act="wslook">${LOOKS.map((l) => `<option value="${l.key}" ${m.ws.look === l.key ? "selected" : ""}>${l.label}</option>`).join("")}</select></label>
        <fieldset class="st-sec"><legend>表示する種類</legend><div class="st-ws-kinds">${KINDS.map((k) => `<label><input type="checkbox" data-act="wskind" value="${k.key}" ${m.ws.shown.has(k.key) ? "checked" : ""}>${k.label}</label>`).join("")}</div></fieldset>
        <div class="st-save">${differs
          ? `<button class="btn" type="button" data-act="ssave" aria-haspopup="dialog">${icon("save")}ワークスペースの既定を保存</button>`
          : `<p class="st-same" id="${m.p}same" tabindex="-1">保存している既定と同じです。</p>`}</div>
      </div>`;
  };
  const MSG_ICON = { ok: "check", info: "sliders", warn: "alert" };

  /**
   * 表示の設定のパネルの中身（見出しの帯と本文）を返す。見た目はネットワークのドロップダウンで選び、パネルには選びを置かない。
   * m: p（id と name の頭）・look・defLook・shown・defShown・counts・theme・showTheme・overrides・save（button / sections / none）・ws・msg・nostore
   */
  const panelHtml = (m) => {
    const sections = m.save === "sections";
    const msg = m.msg ? `${icon(MSG_ICON[m.msg.kind])}<span>${esc(m.msg.text)}</span>` : "";
    return `<div class="panel-head cdrawer-head"><h2 class="cm-h">表示の設定</h2><span class="spacer"></span><button class="icon-btn" type="button" data-act="settings" aria-label="表示の設定を閉じる">${icon("x")}</button></div>
      <div class="st-wrap">
        ${m.nostore ? `<p class="st-note" role="alert">${icon("alert")}<span>この端末に保存できません。選んだ表示は、このページを開いている間だけ当たります。</span></p>` : ""}
        ${sections ? `<p class="st-part">この端末</p>` : ""}
        ${m.showTheme ? themeField(m) : ""}
        ${kindsField(m)}
        ${resetBlock(m)}
        ${m.save === "button" ? saveButton(m) : sections ? wsSection(m) : ""}
        <p class="st-msg${m.msg ? " " + m.msg.kind : ""}" role="status">${msg}</p>
      </div>`;
  };

  // 確かめの 1 行: 変える項目は今の既定と保存する値を、変えない項目は今の値と「変えない」を出す
  const confirmRow = (label, from, to) => `<div class="sc-row"><dt>${label}</dt><dd>${from === to
    ? `<span class="sc-to">${esc(to)}</span><span class="sc-same">変えない</span>`
    : `<span class="sc-from"><span class="sr-only">今の既定 </span>${esc(from)}</span>${icon("arrow")}<span class="sc-to"><span class="sr-only">保存する値 </span>${esc(to)}</span>`}</dd></div>`;

  /**
   * ワークスペースの既定として保存する前の確かめの中身を返す。
   * c: from（今の既定の look・shown）・to（保存する値）・busy（保存している途中）・error（保存できなかった理由）
   */
  const confirmHtml = (c) => `<h2 id="sc-h">ワークスペースの既定を書き換えますか</h2>
    <p class="sc-lead">このワークスペースを開く全員の既定が変わります。表示の設定を自分で変えている人には、変えた項目は当たりません。</p>
    <dl class="sc-list">${confirmRow("ネットワークの見た目", lookLabel(c.from.look), lookLabel(c.to.look))}${confirmRow("表示する種類", kindsText(c.from.shown), kindsText(c.to.shown))}</dl>
    ${c.error ? `<div class="sc-error" role="alert">${icon("alert")}<span>${esc(c.error)}</span></div>` : ""}
    <div class="cf-row"><button class="btn ghost" type="button" data-act="scancel" ${c.busy ? "disabled" : ""}>取り消す</button><button class="btn primary" type="button" data-act="sconfirm" ${c.busy ? "disabled" : ""}>${c.busy ? '<span class="spinner" aria-hidden="true"></span>保存しています' : "保存する"}</button></div>`;

  // まとめて選ぶチェックの途中の状態（一部だけを選んでいる）は HTML の属性で持てないため、描いた後に付ける
  const markMixed = (root) => { for (const b of root.querySelectorAll("[data-act=skindall]")) b.indeterminate = b.dataset.mixed === "1"; };

  window.SETTINGS_UI = { LOOKS, KINDS, BUILTIN_LOOK, icon, lookLabel, kindsText, sameSet, panelHtml, confirmHtml, markMixed };
})();
