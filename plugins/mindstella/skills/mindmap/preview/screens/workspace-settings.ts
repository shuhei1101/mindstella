// 設定の画面。ワークスペースの設定を、キーごとの入力で書き換える別の画面。

namespace MindmapPreview {
  /** 設定の画面の引数 */
  export type WorkspaceSettingsProps = {
    /** 保存待ちの編集を当てた設定 */
    settings: Settings;
    /** 設定のキー → 印の種類 */
    marks: Record<string, PendingMarkKind>;
    /** 設定のキー → 溜められなかった理由 */
    errors: Record<string, string>;
    /** 開いたときに読んだ文字起こしの可否（読めない・まだ読んでいなければ null） */
    transcription?: TranscriptionStatus | null;
    on: {
      /** 設定のキーを溜める */
      change: (input: { key: string; value: unknown }) => void;
      close: () => void;
    };
  };

  /** 1 行ずつの表の列（キー・見出し・入力の種類） */
  type TableColumn = { key: string; title: string; type: "text" | "url" };

  /** 1 行ずつの表で書き換える設定のキーと、列 */
  const TABLES: Record<"links", { label: string; columns: TableColumn[] }> = {
    links: {
      label: "関連する場所",
      columns: [
        { key: "title", title: "表示名", type: "text" },
        { key: "url", title: "URL", type: "url" },
      ],
    },
  };

  /** 設定のまとまり（見出しとキー） */
  const GROUPS: { title: string; keys: string[] }[] = [
    { title: "話し合い", keys: ["summary", "description"] },
    { title: "関連", keys: ["links"] },
    { title: "変更履歴", keys: ["history_limit"] },
    { title: "音声入力", keys: ["transcription"] },
  ];

  /** 文字起こし後の挙動の選択肢 */
  const TRANSCRIPTION_ACTIONS = [
    { value: "review", label: "レビュー中に追加する" },
    { value: "insert", label: "入力欄へ挿入する" },
    { value: "send", label: "送信する" },
  ] as const;

  /** 用語集のプリセットの「サービスの既定」（プリセットを指定しない） */
  const SERVICE_DEFAULT_PRESET = "サービスの既定";

  /** 用語集のプリセットの候補を読めないときの、理由ごとの文 */
  const PRESET_UNAVAILABLE_TEXT = {
    stopped: "文字起こしのサービスが起動していないため、候補を取得できません。サービスを起動してから設定の画面を開き直してください。",
    unsupported: "文字起こしのサービスが音声の受け付けに対応していないため、候補を取得できません。",
  } as const;

  /** 設定のキーの入力欄の名前 */
  const SETTING_NAMES: Record<string, string> = {
    summary: "題名",
    description: "説明",
    links: "関連する場所",
    history_limit: "保持する回数",
  };

  /** 設定の画面（見出しの帯と、まとまりごとの入力）を返す */
  export function workspaceSettings(props: WorkspaceSettingsProps): HTMLElement {
    const form = h({
      tag: "form",
      attrs: {
        class: "pe-form pe-ws-form",
        novalidate: true,
        "aria-label": "ワークスペースの設定",
        onsubmit: (event: Event) => event.preventDefault(),
      },
      children: GROUPS.map((group) =>
        h({
          tag: "fieldset",
          attrs: { class: "pe-ws-group" },
          children: [
            h({ tag: "legend", children: [group.title] }),
            ...group.keys.flatMap((key) => (key === "transcription" ? transcriptionFields(props) : [settingField({ props, key })])),
          ],
        }),
      ),
    });
    form.append(h({ tag: "p", attrs: { class: "pe-form-msg", role: "status" } }));
    return h({
      tag: "main",
      attrs: { class: "content pe-ws pe-screen" },
      children: [
        h({
          tag: "div",
          attrs: { class: "pe-screen-head" },
          children: [
            h({ tag: "h1", attrs: { tabindex: "-1" }, children: ["設定"] }),
            h({ tag: "span", attrs: { class: "spacer" } }),
            h({
              tag: "button",
              attrs: { class: "btn", type: "button", onclick: () => props.on.close() },
              children: [icon("x"), "閉じる"],
            }),
          ],
        }),
        form,
      ],
    });
  }

  /** 設定のキー 1 つの入力欄（名前の行・入力・誤り） */
  function settingField({ props, key }: { props: WorkspaceSettingsProps; key: string }): HTMLElement {
    const { settings, marks, errors, on } = props;
    const name = SETTING_NAMES[key] ?? key;
    const controlId = `pe-ws-${key}`;
    const mark = marks[key];
    const wrap = h({
      tag: "div",
      attrs: {
        class: `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}`,
        "data-key": key,
      },
    });
    const record = settings as unknown as Record<string, unknown>;
    const value = record[key];
    wrap.append(
      h({
        tag: "div",
        attrs: { class: "pe-label-row" },
        children: [
          key in TABLES
            ? h({ tag: "span", attrs: { class: "pe-label", id: `${controlId}-label` }, children: [name] })
            : h({ tag: "label", attrs: { for: controlId, id: `${controlId}-label` }, children: [name] }),
          mark === undefined ? null : pendingEditMark({ kind: mark, compact: true }),
        ],
      }),
    );
    /** 設定のキーを溜める */
    const commit = (next: unknown): void => on.change({ key, value: next });

    if (key === "summary") {
      const input = h({
        tag: "input",
        attrs: { id: controlId, class: "input", type: "text", value: typeof value === "string" ? value : "", autocomplete: "off" },
      });
      input.addEventListener("change", () => commit(input.value));
      wrap.append(input);
    } else if (key === "description") {
      const area = h({ tag: "textarea", attrs: { id: controlId, class: "input pe-text", rows: 2 } });
      area.value = typeof value === "string" ? value : "";
      // 空にして離れたら、説明を消す
      area.addEventListener("change", () => commit(area.value === "" ? null : area.value));
      wrap.append(area);
    } else if (key === "history_limit") {
      const input = h({
        tag: "input",
        attrs: {
          id: controlId,
          class: "input pe-num",
          type: "number",
          min: 1,
          step: 1,
          inputmode: "numeric",
          value: typeof value === "number" ? value : "",
        },
      });
      input.addEventListener("change", () => {
        const next = Number(input.value);
        if (input.value.trim() === "" || !Number.isInteger(next) || next < 1) return;
        commit(next);
      });
      wrap.append(input, h({ tag: "p", attrs: { class: "pe-hint" }, children: ["変更履歴に残す書き換えのまとまりの数"] }));
    } else if (key in TABLES) {
      wrap.append(...tableInputs({ props, key: key as keyof typeof TABLES, controlId, commit }));
    }

    const failure = errors[key];
    if (failure !== undefined) {
      wrap.append(h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [icon("alert"), failure] }));
    }
    return wrap;
  }

  /** 音声入力のまとまり（文字起こし後の挙動のラジオと、用語集のプリセットのセレクト）。どちらも `transcription` を 1 件溜める */
  function transcriptionFields(props: WorkspaceSettingsProps): HTMLElement[] {
    const { marks, errors, on } = props;
    const record = props.settings as unknown as Record<string, unknown>;
    const current = (typeof record.transcription === "object" && record.transcription !== null ? record.transcription : {}) as {
      action?: string;
      preset?: string | null;
    };
    // 描き直す前に続けて選んでも、もう一方の値は最後に選んだものを保つ
    let action: string = current.action === "send" || current.action === "insert" ? current.action : "review";
    let preset: string | null = typeof current.preset === "string" ? current.preset : null;
    const mark = marks.transcription;
    const fieldClass = `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}`;
    const markNode = (): HTMLElement | null => (mark === undefined ? null : pendingEditMark({ kind: mark, compact: true }));
    /** もう一方の値を保ったオブジェクトで溜める */
    const commit = (next: { action: string; preset: string | null }): void => on.change({ key: "transcription", value: next });

    // 文字起こし後の挙動
    const actionId = "pe-ws-transcription-action";
    const actionField = h({
      tag: "div",
      attrs: { class: fieldClass, "data-key": "transcription.action" },
      children: [
        h({
          tag: "div",
          attrs: { class: "pe-label-row" },
          children: [h({ tag: "span", attrs: { class: "pe-label", id: `${actionId}-label` }, children: ["文字起こし後の挙動"] }), markNode()],
        }),
        h({
          tag: "div",
          attrs: { class: "pe-radios", role: "radiogroup", "aria-labelledby": `${actionId}-label` },
          children: TRANSCRIPTION_ACTIONS.map((choice) => {
            const radio = h({
              tag: "input",
              attrs: { type: "radio", name: actionId, value: choice.value, checked: choice.value === action },
            });
            radio.addEventListener("change", () => {
              if (!radio.checked) return;
              action = choice.value;
              commit({ action, preset });
            });
            return h({ tag: "label", attrs: { class: "pe-radio" }, children: [radio, choice.label] });
          }),
        }),
        h({
          tag: "p",
          attrs: { class: "pe-hint" },
          children: ["「レビュー中に追加する」は文字起こしの結果を挿入した全文をレビュー中に追加し、送信しません。「入力欄へ挿入する」はカーソルの位置に挿入するだけです。「送信する」はその書き込みだけで Claude Code へ送信します。"],
        }),
      ],
    });

    // 用語集のプリセット
    const presetId = "pe-ws-transcription-preset";
    const status = props.transcription ?? null;
    const usable = status !== null && status.available;
    const select = h({
      tag: "select",
      attrs: { id: presetId, class: "input", "aria-describedby": `${presetId}-hint`, disabled: !usable },
    }) as HTMLSelectElement;
    if (usable) {
      // 候補は「サービスの既定」と、サービスが返した並び（今の値が候補に無ければ末尾に足す）
      const names = preset !== null && !status.presets.includes(preset) ? [...status.presets, preset] : status.presets;
      select.append(h({ tag: "option", attrs: { value: "" }, children: [SERVICE_DEFAULT_PRESET] }));
      for (const name of names) select.append(h({ tag: "option", attrs: { value: name }, children: [name] }));
    } else {
      // 使えない: 今の値だけを並べて押せなくする
      select.append(h({ tag: "option", attrs: { value: preset ?? "" }, children: [preset ?? SERVICE_DEFAULT_PRESET] }));
    }
    select.value = preset ?? "";
    select.addEventListener("change", () => {
      preset = select.value === "" ? null : select.value;
      commit({ action, preset });
    });
    const unavailableText = status !== null && !status.available && status.reason !== null ? PRESET_UNAVAILABLE_TEXT[status.reason] : null;
    const presetField = h({
      tag: "div",
      attrs: { class: fieldClass, "data-key": "transcription.preset" },
      children: [
        h({
          tag: "div",
          attrs: { class: "pe-label-row" },
          children: [h({ tag: "label", attrs: { for: presetId, id: `${presetId}-label` }, children: ["用語集のプリセット"] }), markNode()],
        }),
        select,
        h({
          tag: "p",
          attrs: { class: "pe-hint", id: `${presetId}-hint` },
          children:
            unavailableText === null
              ? ["文字起こしの補正に使用する用語集です。候補は文字起こしのサービスから取得します。"]
              : [icon("alert"), unavailableText],
        }),
      ],
    });
    const failure = errors.transcription;
    if (failure !== undefined) {
      presetField.append(h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [icon("alert"), failure] }));
    }
    return [actionField, presetField];
  }

  /** 関連する場所（1 行ずつの表） */
  function tableInputs({
    props,
    key,
    controlId,
    commit,
  }: {
    props: WorkspaceSettingsProps;
    key: keyof typeof TABLES;
    controlId: string;
    commit: (next: unknown) => void;
  }): HTMLElement[] {
    const { label, columns } = TABLES[key];
    const rows = ((props.settings as unknown as Record<string, unknown>)[key] ?? []) as Record<string, string>[];
    const wrap = h({ tag: "div", attrs: { class: "pe-mini-wrap" } });
    const body = h({ tag: "tbody" });
    rows.forEach((row, at) => {
      const cells = columns.map((column) => {
        const input = h({
          tag: "input",
          attrs: {
            id: `${controlId}-${at}-${column.key}`,
            class: "input",
            type: column.type,
            value: row[column.key] ?? "",
            "aria-label": `${at + 1} 行目の${column.title}`,
          },
        });
        input.addEventListener("change", () => {
          commit(rows.map((entry, position) => (position === at ? { ...entry, [column.key]: input.value } : entry)));
        });
        return h({ tag: "td", children: [input] });
      });
      const remove = h({
        tag: "button",
        attrs: {
          class: "icon-btn",
          type: "button",
          "aria-label": `${at + 1} 行目を削除`,
          onclick: () => commit(rows.filter((_, position) => position !== at)),
        },
        children: [icon("trash")],
      });
      body.append(h({ tag: "tr", children: [...cells, h({ tag: "td", children: [remove] })] }));
    });
    wrap.append(
      h({
        tag: "table",
        attrs: { class: "pe-mini", "aria-labelledby": `${controlId}-label` },
        children: [
          h({
            tag: "thead",
            children: [
              h({
                tag: "tr",
                children: [
                  ...columns.map((column) => h({ tag: "th", attrs: { scope: "col" }, children: [column.title] })),
                  h({ tag: "th", children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["操作"] })] }),
                ],
              }),
            ],
          }),
          body,
        ],
      }),
    );
    return [
      wrap,
      h({
        tag: "button",
        attrs: {
          class: "btn pe-row-add",
          type: "button",
          onclick: () => commit([...rows, Object.fromEntries(columns.map((column) => [column.key, ""]))]),
        },
        children: [icon("plus"), `${label}を追加`],
      }),
    ];
  }
}
