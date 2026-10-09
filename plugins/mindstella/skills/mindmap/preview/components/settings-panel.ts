// 表示の設定の中身。表示する種類を選び、この端末で変えている項目・既定に戻す・ワークスペースの既定にするを出す。見た目はネットワークのドロップダウンで選ぶので、ここでは選ばせない。

namespace MindmapPreview {
  /** ネットワークの見た目 1 つ（値・画面に出す名前・短い説明） */
  export type NetworkLookOption = { key: NetworkLook; label: string; note: string };

  /** 選べるネットワークの見た目 */
  export const NETWORK_LOOKS: readonly NetworkLookOption[] = [
    { key: "glow", label: "グロウ", note: "玉と流れる光に、やわらかい光のにじみ" },
    { key: "starlight", label: "星の光", note: "白い芯と色の光。明るい星に十字の光条" },
    { key: "constellation", label: "星図", note: "回転に合わせて回る天球の経緯線" },
    { key: "deep", label: "深宇宙", note: "星空と星雲の地に、光のにじむ星" },
    { key: "dust", label: "星屑", note: "色を抜いた細かな点と細い線" },
  ];

  /** ワークスペースの既定も個人の上書きも無いときの見た目 */
  export const BUILTIN_LOOK: NetworkLook = "deep";

  /** 見た目の値 → 画面に出す名前 */
  export function lookLabel(look: string): string {
    return NETWORK_LOOKS.find((option) => option.key === look)?.label ?? look;
  }

  /** パネルの下端に残す知らせ（`ok` は既定にした、`info` は既定が変わった） */
  export type SettingsMessage = { kind: "ok" | "info"; text: string };

  /** 表示の設定の中身の引数 */
  export type SettingsPanelProps = {
    /** 今当てているネットワークの見た目（パネルには出さず、`defaultLook` と比べる） */
    look: string;
    /** ワークスペースの既定の見た目（パネルには出さず、`look` と比べる） */
    defaultLook: string;
    /** 今当てている表示する種類 */
    kinds: Set<string>;
    /** ワークスペースの既定の表示する種類 */
    defaultKinds: Set<string>;
    /** 種類 → 件数 */
    counts: Record<string, number>;
    /** この端末で変えている項目の名前 */
    overrides: string[];
    /** 「ワークスペースの既定にする」を置くか（配る書き出しは偽） */
    canSave: boolean;
    /** 下端に残す知らせ */
    message?: SettingsMessage | null;
    /** 端末の保存領域に書けるか。偽のとき先頭にその旨を出す */
    storageOk?: boolean;
    on: {
      /** 表示する種類を変えたとき（変えた後の並びを渡す） */
      kinds: (kinds: string[]) => void;
      /** 「既定に戻す」を押したとき */
      reset: () => void;
      /** 「ワークスペースの既定にする」を押したとき */
      save: () => void;
      /** 見出しの × か Esc で閉じるとき */
      close: () => void;
    };
  };

  /** 種類 → 種類の行に出す印 */
  const KIND_ICON: Record<Kind, IconName> = {
    decisions: "decision",
    tasks: "task",
    research: "research",
    docs: "doc",
    terms: "term",
    notes: "note",
    logs: "log",
  };

  /** 2 つの集合が同じ要素を持つか */
  function sameSet(a: Set<string>, b: Set<string>): boolean {
    return a.size === b.size && [...a].every((value) => b.has(value));
  }

  /** 種類の並び（種類の定義の順）にそろえる */
  function orderedKinds(kinds: Set<string>): string[] {
    return KIND_KEYS.filter((kind) => kinds.has(kind));
  }

  /** 端末に保存できない旨（パネルの先頭） */
  function storageNote(): HTMLElement {
    return h({
      tag: "p",
      attrs: { class: "st-note", role: "alert" },
      children: [
        icon("alert"),
        h({ tag: "span", children: ["この端末に保存できません。選んだ表示は、このページを開いている間だけ当たります。"] }),
      ],
    });
  }

  /** 概要・ネットワークの行（常に出す。チェックの箱を持たない） */
  function alwaysRow({ iconName, label }: { iconName: IconName; label: string }): HTMLElement {
    return h({
      tag: "li",
      attrs: { class: "st-always" },
      children: [
        h({ tag: "span", attrs: { class: "st-always-box" }, children: [icon("check")] }),
        icon(iconName),
        h({ tag: "span", attrs: { class: "st-k-label" }, children: [label] }),
        h({ tag: "span", attrs: { class: "st-always-note" }, children: ["常に表示"] }),
      ],
    });
  }

  /** 表示する種類の選び（先頭にまとめて選ぶチェック、概要とネットワークは常に出す行） */
  function kindsField({ kinds, counts, on }: SettingsPanelProps): HTMLElement {
    const shownCount = KIND_KEYS.filter((kind) => kinds.has(kind)).length;
    const allBox = h({
      tag: "input",
      attrs: {
        type: "checkbox",
        checked: shownCount === KIND_KEYS.length,
        "data-focus": "kinds-all",
        // 全て選んでいるときは全て外し、そうでなければ全て選ぶ
        onchange: () => on.kinds(shownCount === KIND_KEYS.length ? [] : [...KIND_KEYS]),
      },
    });
    // 一部だけを選んでいる途中の状態は、属性で持てないため要素に付ける
    allBox.indeterminate = shownCount > 0 && shownCount < KIND_KEYS.length;
    return h({
      tag: "fieldset",
      attrs: { class: "st-sec" },
      children: [
        h({ tag: "legend", children: ["表示する種類"] }),
        h({
          tag: "ul",
          attrs: { class: "st-kinds" },
          children: [
            h({
              tag: "li",
              attrs: { class: "st-all" },
              children: [
                h({
                  tag: "label",
                  children: [
                    allBox,
                    h({ tag: "span", attrs: { class: "st-k-label" }, children: ["すべて"] }),
                    h({ tag: "span", attrs: { class: "n mono" }, children: [`${shownCount}/${KIND_KEYS.length}`] }),
                  ],
                }),
              ],
            }),
            alwaysRow({ iconName: "home", label: "概要" }),
            ...KIND_KEYS.map((kind) =>
              h({
                tag: "li",
                children: [
                  h({
                    tag: "label",
                    children: [
                      h({
                        tag: "input",
                        attrs: {
                          type: "checkbox",
                          value: kind,
                          checked: kinds.has(kind),
                          "data-focus": `kind:${kind}`,
                          // 押した種類だけを入れ替えた、変えた後の並びを知らせる
                          onchange: () => {
                            const next = new Set(kinds);
                            if (next.has(kind)) next.delete(kind);
                            else next.add(kind);
                            on.kinds(orderedKinds(next));
                          },
                        },
                      }),
                      icon(KIND_ICON[kind]),
                      h({ tag: "span", attrs: { class: "st-k-label" }, children: [KIND_LABEL[kind]] }),
                      h({ tag: "span", attrs: { class: "n mono" }, children: [counts[kind] ?? ""] }),
                    ],
                  }),
                ],
              }),
            ),
            alwaysRow({ iconName: "network", label: "ネットワーク" }),
          ],
        }),
      ],
    });
  }

  /** この端末で変えている項目と「既定に戻す」。上書きが無いときはボタンを出さず、その旨を出す */
  function resetBlock({ overrides, on }: SettingsPanelProps): HTMLElement {
    if (overrides.length === 0) {
      return h({
        tag: "div",
        attrs: { class: "st-reset" },
        children: [
          h({
            tag: "p",
            attrs: { class: "st-over st-none", tabindex: "-1", "data-focus": "over" },
            children: ["ワークスペースの既定のまま表示しています。"],
          }),
        ],
      });
    }
    return h({
      tag: "div",
      attrs: { class: "st-reset" },
      children: [
        h({
          tag: "p",
          attrs: { class: "st-over" },
          children: [
            h({ tag: "span", attrs: { class: "st-over-h" }, children: ["この端末で変えている項目"] }),
            h({ tag: "span", children: [overrides.join("・")] }),
          ],
        }),
        h({
          tag: "button",
          attrs: { class: "btn", type: "button", "data-focus": "reset", onclick: () => on.reset() },
          children: [icon("undo"), "既定に戻す"],
        }),
      ],
    });
  }

  /** 「ワークスペースの既定にする」。選びが既定と同じときはボタンの代わりにその旨を出す */
  function saveBlock({ look, defaultLook, kinds, defaultKinds, on }: SettingsPanelProps): HTMLElement {
    const differs = look !== defaultLook || !sameSet(kinds, defaultKinds);
    return h({
      tag: "div",
      attrs: { class: "st-save" },
      children: [
        differs
          ? h({
            tag: "button",
            attrs: {
              class: "btn",
              type: "button",
              "aria-haspopup": "dialog",
              "data-focus": "save",
              onclick: () => on.save(),
            },
            children: [icon("save"), "ワークスペースの既定にする"],
          })
          : h({
            tag: "p",
            attrs: { class: "st-same", tabindex: "-1", "data-focus": "same" },
            children: ["今の選びはワークスペースの既定と同じです。"],
          }),
      ],
    });
  }

  /** 下端に残す知らせ（`role="status"`） */
  function messageLine(message: SettingsMessage | null): HTMLElement {
    return h({
      tag: "p",
      attrs: { class: `st-msg${message === null ? "" : ` ${message.kind}`}`, role: "status" },
      children: message === null ? [] : [icon(message.kind === "ok" ? "check" : "sliders"), h({ tag: "span", children: [message.text] })],
    });
  }

  /** 表示の設定の中身を返す */
  export function settingsPanel(props: SettingsPanelProps): HTMLElement {
    const { canSave, message = null, storageOk = true } = props;
    return h({
      tag: "div",
      attrs: { class: "st-wrap" },
      children: [
        storageOk ? null : storageNote(),
        kindsField(props),
        resetBlock(props),
        canSave ? saveBlock(props) : null,
        messageLine(message),
      ],
    });
  }
}
