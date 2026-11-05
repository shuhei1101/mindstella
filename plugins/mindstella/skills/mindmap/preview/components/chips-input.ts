// チップの入力。値のチップと、値を追加する入力欄。項目のタグは主題のトグルを持つ。

namespace MindmapPreview {
  /** チップの入力の引数 */
  export type ChipsInputProps = {
    /** 入力欄の `id` */
    controlId: string;
    /** キーの表示名 */
    name: string;
    /** 入力欄のプレースホルダ */
    hint: string;
    /** 今の値の並び（`mainToggle` が真のときは `Tag[]`） */
    values: readonly (Tag | string)[];
    /** 入力欄に出す候補（記録で使われているタグ。候補に無い値も入れられる） */
    suggestions: readonly string[] | null;
    monospace: boolean;
    /** 主題のトグルを置くか（項目のタグだけ真） */
    mainToggle?: boolean;
    disabled: boolean;
    /** 値を追加した・外した・主題を付け外ししたときに新しい並びを渡す（外したときは外した値の名前も） */
    onChange: (values: (Tag | string)[], removed: string | null) => void;
  };

  /** 値を並べるキーの入力（チップと、追加する入力欄）。`mainToggle` が真のときは値を `{name, main?}` で持ち、チップに主題のトグルを置く */
  export function chipsInput({
    controlId,
    name,
    hint,
    values,
    suggestions,
    monospace,
    mainToggle = false,
    disabled,
    onChange,
  }: ChipsInputProps): HTMLElement {
    let current: Tag[] = values.map((value) =>
      typeof value === "string" ? { name: value } : value.main === true ? { name: value.name, main: true } : { name: value.name },
    );
    /** `onChange` に渡す並び（トグルを持たないときは名前の文字列の並び） */
    const output = (): (Tag | string)[] => (mainToggle ? current.map((tag) => ({ ...tag })) : current.map((tag) => tag.name));
    const box = h({ tag: "div", attrs: { class: "pe-chips", role: "group", "aria-label": name } });
    const listId = `${controlId}-list`;
    const field = h({
      tag: "input",
      attrs: {
        id: controlId,
        class: "input pe-chip-input",
        type: "text",
        list: suggestions === null ? null : listId,
        placeholder: hint,
        "aria-label": `${name}を追加`,
        autocomplete: "off",
        disabled,
      },
    });
    /** 入力した値を並びに追加する（空と、もうある値は追加しない。追加したタグは主題でない） */
    const addValue = (): void => {
      const text = field.value.trim();
      field.value = "";
      if (text === "" || current.some((tag) => tag.name === text)) return;
      current = [...current, { name: text }];
      draw();
      onChange(output(), null);
      box.querySelector<HTMLInputElement>(".pe-chip-input")?.focus();
    };
    field.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.isComposing) return;
      event.preventDefault();
      addValue();
    });
    field.addEventListener("change", addValue);
    /** そのタグの主題のトグル */
    const toggleButton = (entry: Tag, index: number): HTMLElement => {
      const isMain = entry.main === true;
      return h({
        tag: "button",
        attrs: {
          class: "pe-chip-main",
          type: "button",
          "aria-label": `${entry.name} を主題`,
          "aria-pressed": isMain ? "true" : "false",
          title: isMain ? "主題を外す" : "主題にする",
          "data-index": index,
          disabled,
          onclick: () => {
            current = current.map((tag, position) =>
              position !== index ? tag : tag.main === true ? { name: tag.name } : { name: tag.name, main: true },
            );
            draw();
            onChange(output(), null);
            // 押した後も同じタグのトグルにフォーカスを残す
            box.querySelector<HTMLButtonElement>(`.pe-chip-main[data-index="${index}"]`)?.focus();
          },
        },
        children: [icon(isMain ? "main" : "mainOff"), h({ tag: "span", attrs: { class: "tag-main-text" }, children: ["主題"] })],
      });
    };
    /** チップを描き直す */
    const draw = (): void => {
      box.replaceChildren(
        ...current.map((entry, index) =>
          h({
            tag: "span",
            attrs: {
              class: `tag pe-chip${monospace ? " mono" : ""}${mainToggle ? " has-main" : ""}${mainToggle && entry.main === true ? " is-main" : ""}`,
            },
            children: [
              mainToggle ? toggleButton(entry, index) : null,
              entry.name,
              h({
                tag: "button",
                attrs: {
                  class: "pe-chip-x",
                  type: "button",
                  "aria-label": `${entry.name} を外す`,
                  disabled,
                  onclick: () => {
                    current = current.filter((_, position) => position !== index);
                    draw();
                    onChange(output(), entry.name);
                  },
                },
                children: [icon("x")],
              }),
            ],
          }),
        ),
        field,
        ...(suggestions === null
          ? []
          : [
              h({
                tag: "datalist",
                attrs: { id: listId },
                children: suggestions.map((tag) => h({ tag: "option", attrs: { value: tag } })),
              }),
            ]),
      );
    };
    draw();
    return box;
  }
}
