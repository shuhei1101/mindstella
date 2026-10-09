// トップバー。話し合いの題名・全体の検索の入口・変更履歴・ライト / ダークの切り替え・表示の設定・絞り込み・コメントのボタンと、画面を移るタブの帯（右端にネットワークの入口）を出す。

namespace MindmapPreview {
  /** ライト / ダーク */
  export type Theme = "light" | "dark";

  /** タブの帯に並べる 1 つの画面 */
  export type TopbarTab = {
    key: Tab;
    label: string;
    icon: IconName;
    /** その種類の項目の件数（概要は持たない） */
    count?: number;
    /** 差分の表示の間、その種類に新規・変更・消した項目があるか。真のとき、件数を残したまま右上に点を重ねる */
    marked?: boolean;
  };

  /** 変更履歴で選んだ時点（札に出す名前と補足） */
  export type DiffPointLabel = {
    /** 「前回開いてから」・「まだまとめていない変更」・まとまりの説明 */
    name: string;
    /** 日時など */
    sub: string;
  };

  /** トップバーの引数 */
  export type TopbarProps = {
    /** 話し合いの題名（`config.yaml` の `summary`）。1 行で末尾を省略し、全文を `title` 属性に持たせる */
    title: string;
    /** タブの帯に並べる画面（概要と、表示する種類。ネットワークは含めない） */
    tabs: TopbarTab[];
    /** 開いている画面 */
    current: Tab;
    /** 今のライト / ダーク */
    theme: Theme;
    /** タブかネットワークの入口を押したとき（開いている詳細パネルは閉じない） */
    onNavigate: (key: Tab) => void;
    /** 検索の入口を押したとき（`/` キーは使う側が受ける） */
    onSearch: () => void;
    /** ライト / ダークのボタンを押したとき（切り替え先を渡す） */
    onTheme: (theme: Theme) => void;
    /** サーバーにつながっているか。`offline` のとき接続の状態を出す（配る書き出しでは出さない） */
    connection?: "online" | "offline";
    /** 描いている記録を読んだ日時（`built_at`）。接続の状態に JST で添える */
    readAt?: string | null;
    /** コメントのボタンを出すか。サーバーの配信では true、配る書き出しでは false。出すときは右端に置き、検索の入口を中央へ寄せる */
    comments?: boolean;
    /** レビュー中のコメントの件数。印と「コメント」の右に出す（0 件は件数の塗りを外し、99 を超えたら `99+`） */
    commentCount?: number;
    /** コメントの一覧を開いているか */
    commentsOpen?: boolean;
    /** コメントのボタンを押したとき（0 件でも押せる。一覧を開く・閉じる） */
    onComments?: () => void;
    /** 変更履歴で選んだ時点。あるとき、「変更履歴」の右にその名前の札と外す × を出す */
    diffPoint?: DiffPointLabel | null;
    /** 「変更履歴」のボタンを押したとき。渡さないと「変更履歴」を出さない */
    onHistory?: () => void;
    /** 札の × を押したとき（差分の表示をやめる） */
    onDiffOff?: () => void;
    /** 表示の設定のパネルを開いているか。開いているとき、ボタンを枠と面で選んだ見た目にする */
    settingsOpen?: boolean;
    /** 表示の設定のボタンを押したとき（パネルを開く・閉じる）。渡さないと表示の設定のボタンを出さない。サーバーの配信でも配る書き出しでも渡し、絞り込みのボタンがあればその左、無ければコメントのボタンの左に置く */
    onSettings?: () => void;
    /** 絞り込みのボタンを出すか。項目を並べる画面では true、概要では false。出すときはコメントのボタンの左隣（コメントのボタンが無いときは右端）に置く */
    filter?: boolean;
    /** 値を 1 つ以上選んでいる条件の数。1 以上のときだけ、印の色のバッジで「絞り込み」の右に出す */
    filterCount?: number;
    /** 絞り込みのドロワーを開いているか */
    filterOpen?: boolean;
    /** 絞り込みのボタンを押したとき（ドロワーを開く・閉じる） */
    onFilter?: () => void;
  };

  /** 件数の表示を揺らさない上限 */
  const COMMENT_COUNT_CAP = 99;

  /** ブランドのマーク（木の形の線画） */
  function brandMark(): SVGSVGElement {
    const holder = document.createElement("template");
    holder.innerHTML =
      '<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="16" r="4"/><path d="M12 16h5M17 16V7h5M17 16v9h5"/><circle cx="25" cy="7" r="2.6"/><circle cx="25" cy="25" r="2.6"/></svg>';
    return holder.content.firstElementChild as SVGSVGElement;
  }

  /** 画面を移るリンク（ハッシュのリンクにして、押したときは使う側が移る） */
  function tabLink(
    { key, label, icon: iconName, count, marked = false }: TopbarTab,
    current: Tab,
    onNavigate: (key: Tab) => void,
    extraClass = "",
  ): HTMLElement {
    return h({
      tag: "a",
      attrs: {
        class: `tab ${extraClass}`.trim(),
        href: `#${key === "overview" ? "" : `tab=${key}`}`,
        "data-tab": key,
        "aria-current": key === current ? "page" : null,
        onclick: (event) => {
          event.preventDefault();
          onNavigate(key);
        },
      },
      children: [
        icon(iconName),
        label,
        count === undefined ? null : h({ tag: "span", attrs: { class: "count" }, children: [count] }),
        // 差分の表示の間、印の付いた項目を持つ種類に、件数を残したまま点を重ねる
        marked
          ? h({
            tag: "span",
            attrs: { class: "df-dot" },
            children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["新規・変更・消した項目があります"] })],
          })
          : null,
      ],
    });
  }

  /** 「変更履歴」のボタン（印と文言）。押すと変更履歴のモーダルを開く */
  function historyButton(onClick: () => void): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: "hist-btn",
        type: "button",
        "data-act": "hist",
        "aria-haspopup": "dialog",
        "aria-label": "変更履歴",
        onclick: onClick,
      },
      children: [icon("history"), h({ tag: "span", attrs: { class: "label" }, children: ["変更履歴"] })],
    });
  }

  /** 選んだ時点の札と、差分の表示をやめる × */
  function diffChip({ point, onOff }: { point: DiffPointLabel; onOff?: () => void }): HTMLElement {
    return h({
      tag: "span",
      attrs: { class: "df-chip" },
      children: [
        h({
          tag: "span",
          attrs: { class: "df-chip-t", title: `${point.name}（${point.sub}）` },
          children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["差分の時点: "] }), point.name],
        }),
        h({
          tag: "button",
          attrs: {
            type: "button",
            "data-act": "diffoff",
            "aria-label": "差分の表示をやめる",
            title: "差分の表示をやめる",
            onclick: () => onOff?.(),
          },
          children: [icon("x")],
        }),
      ],
    });
  }

  /** サーバーにつながらないときの表示。広い幅は読んだ日時つきの文言、狭い幅は短い文言で、日時は `title` に持つ */
  function connectionNotice(readAt: string | null): HTMLElement {
    const readAtText = readAt === null ? null : formatJst(readAt);
    return h({
      tag: "span",
      attrs: {
        class: "conn",
        role: "status",
        title: readAtText === null ? "サーバーにつながりません" : `${readAtText} に読んだ記録を出しています`,
      },
      children: [
        icon("offline"),
        h({
          tag: "span",
          attrs: { class: "conn-long" },
          children: [
            readAtText === null
              ? "サーバーにつながりません"
              : `サーバーにつながりません（${readAtText} に読んだ記録）`,
          ],
        }),
        h({ tag: "span", attrs: { class: "conn-short" }, children: ["つながりません"] }),
      ],
    });
  }

  /** コメントのボタン（印と「コメント」と件数）。押すとコメントの一覧を開く・閉じる */
  function commentsButton({ count, open, onClick }: { count: number; open: boolean; onClick?: () => void }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: `comments-btn${open ? " open" : ""}`,
        type: "button",
        "data-act": "comments",
        "aria-label": `コメント（レビュー中 ${count} 件）`,
        "aria-expanded": String(open),
        onclick: () => onClick?.(),
      },
      children: [
        icon("comment"),
        h({ tag: "span", attrs: { class: "label" }, children: ["コメント"] }),
        h({
          tag: "span",
          attrs: { class: `count${count === 0 ? " zero" : ""}` },
          children: [count > COMMENT_COUNT_CAP ? `${COMMENT_COUNT_CAP}+` : count],
        }),
      ],
    });
  }

  /** 表示の設定のボタン（印と「表示の設定」）。押すと表示の設定のパネルを開く・閉じる */
  function settingsButton({ open, onToggle }: { open: boolean; onToggle: () => void }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: `settings-btn${open ? " open" : ""}`,
        type: "button",
        "data-act": "settings",
        "aria-label": "表示の設定",
        "aria-expanded": String(open),
        onclick: () => onToggle(),
      },
      children: [icon("sliders"), h({ tag: "span", attrs: { class: "label" }, children: ["表示の設定"] })],
    });
  }

  /** 絞り込みのボタン（印と「絞り込み」と、値を選んでいる条件の数のバッジ）。押すと絞り込みのドロワーを開く・閉じる */
  function filterButton({ count, open, onClick }: { count: number; open: boolean; onClick?: () => void }): HTMLElement {
    return h({
      tag: "button",
      attrs: {
        class: `filter-btn${open ? " open" : ""}`,
        type: "button",
        "data-act": "filter",
        "aria-label": count === 0 ? "絞り込み" : `絞り込み（${count} つの条件で絞り込み中）`,
        "aria-expanded": String(open),
        // ドロワーを開いていて、指す先が文書にあるときだけ付ける（ドロワーを描いた後は、ドロワーが付け直す）
        "aria-controls": open && document.getElementById("drawer") !== null ? "drawer" : null,
        onclick: () => onClick?.(),
      },
      children: [
        icon("filter"),
        h({ tag: "span", attrs: { class: "label" }, children: ["絞り込み"] }),
        count === 0 ? null : h({ tag: "span", attrs: { class: "fbadge", "aria-hidden": "true" }, children: [count] }),
      ],
    });
  }

  /** トップバーとタブの帯を返す */
  export function topbar({
    title,
    tabs,
    current,
    theme,
    onNavigate,
    onSearch,
    onTheme,
    connection = "online",
    readAt = null,
    comments = false,
    commentCount = 0,
    commentsOpen = false,
    onComments,
    diffPoint = null,
    onHistory,
    onDiffOff,
    settingsOpen = false,
    onSettings,
    filter = false,
    filterCount = 0,
    filterOpen = false,
    onFilter,
  }: TopbarProps): HTMLElement {
    const nextTheme: Theme = theme === "dark" ? "light" : "dark";
    const bar = h({
      tag: "header",
      attrs: { class: comments ? "topbar has-comments" : "topbar" },
      children: [
        h({
          tag: "span",
          attrs: { class: "brand" },
          children: [
            brandMark(),
            h({ tag: "span", attrs: { class: "brand-name" }, children: ["mindstella"] }),
          ],
        }),
        h({ tag: "span", attrs: { class: "brand-sub", title }, children: [title] }),
        h({ tag: "span", attrs: { class: "spacer" } }),
        connection === "offline" ? connectionNotice(readAt) : null,
        h({
          tag: "button",
          attrs: {
            class: "search-trigger",
            type: "button",
            "data-act": "search",
            "aria-label": "すべての項目を検索",
            "aria-keyshortcuts": "Control+K Meta+K",
            onclick: () => onSearch(),
          },
          children: [
            icon("search"),
            h({ tag: "span", attrs: { class: "label" }, children: ["すべての項目を検索"] }),
            h({ tag: "kbd", children: [/Mac|iPhone|iPad/.test(navigator.platform) ? "⌘K" : "Ctrl+K"] }),
          ],
        }),
        onHistory === undefined ? null : historyButton(onHistory),
        // 差分の表示の間は、選んだ時点の札と外すボタンを「変更履歴」の右に出す
        diffPoint === null ? null : diffChip({ point: diffPoint, onOff: onDiffOff }),
        // コメントのボタンを右端に置くとき、検索の入口を中央へ寄せる
        comments ? h({ tag: "span", attrs: { class: "spacer" } }) : null,
        onSettings === undefined ? null : settingsButton({ open: settingsOpen, onToggle: onSettings }),
        filter ? filterButton({ count: filterCount, open: filterOpen, onClick: onFilter }) : null,
        comments ? commentsButton({ count: commentCount, open: commentsOpen, onClick: onComments }) : null,
        h({
          tag: "button",
          attrs: {
            class: "top-btn",
            type: "button",
            "data-theme": nextTheme,
            "aria-label": theme === "dark" ? "ライトに切り替え" : "ダークに切り替え",
            onclick: () => onTheme(nextTheme),
          },
          children: [icon(theme === "dark" ? "sun" : "moon")],
        }),
      ],
    });
    const tabbar = h({
      tag: "nav",
      attrs: { class: "tabbar", "aria-label": "項目の種類" },
      children: [
        ...tabs.map((tab) => tabLink(tab, current, onNavigate)),
        h({ tag: "span", attrs: { class: "tab-gap" } }),
        tabLink({ key: "graph", label: "ネットワーク", icon: "network" }, current, onNavigate, "tab-special"),
      ],
    });
    return h({ tag: "div", attrs: { class: "top" }, children: [bar, tabbar] });
  }
}
