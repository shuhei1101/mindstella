"use strict";
// チップの入力。値のチップと、値を追加する入力欄。項目のタグは主題のトグルを持つ。
var MindmapPreview;
(function (MindmapPreview) {
    /** 値を並べるキーの入力（チップと、追加する入力欄）。`mainToggle` が真のときは値を `{name, main?}` で持ち、チップに主題のトグルを置く */
    function chipsInput({ controlId, name, hint, values, suggestions, monospace, mainToggle = false, disabled, validate, onChange, }) {
        let current = values.map((value) => typeof value === "string" ? { name: value } : value.main === true ? { name: value.name, main: true } : { name: value.name });
        /** `onChange` に渡す並び（トグルを持たないときは名前の文字列の並び） */
        const output = () => (mainToggle ? current.map((tag) => ({ ...tag })) : current.map((tag) => tag.name));
        const box = MindmapPreview.h({ tag: "div", attrs: { class: "pe-chips", role: "group", "aria-label": name } });
        const listId = `${controlId}-list`;
        const field = MindmapPreview.h({
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
        const errorId = `${controlId}-error`;
        const error = MindmapPreview.h({ tag: "p", attrs: { class: "pe-chip-error", id: errorId, hidden: true } });
        /** 入力の誤りを出す（null で消す）。誤りの間は入力欄が誤りの文を指す */
        const showError = (message) => {
            error.hidden = message === null;
            error.textContent = message === null ? "" : `入力の誤り: ${message}`;
            if (message === null) {
                field.removeAttribute("aria-invalid");
                field.removeAttribute("aria-describedby");
            }
            else {
                field.setAttribute("aria-invalid", "true");
                field.setAttribute("aria-describedby", errorId);
            }
        };
        field.addEventListener("input", () => showError(null));
        /** 入力した値を並びに追加する（空と、もうある値は追加しない。追加したタグは主題でない） */
        const addValue = () => {
            const entered = field.value.trim();
            if (entered === "")
                return;
            const checked = validate === undefined ? { value: entered } : validate(entered);
            // 誤り: 追加せず、入れた値を入力欄に残して直下に誤りを出す
            if ("error" in checked) {
                showError(checked.error);
                return;
            }
            showError(null);
            field.value = "";
            const text = checked.value;
            if (current.some((tag) => tag.name === text))
                return;
            current = [...current, { name: text }];
            draw();
            onChange(output(), null);
            box.querySelector(".pe-chip-input")?.focus();
        };
        field.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" || event.isComposing)
                return;
            event.preventDefault();
            addValue();
        });
        field.addEventListener("change", addValue);
        /** そのタグの主題のトグル */
        const toggleButton = (entry, index) => {
            const isMain = entry.main === true;
            return MindmapPreview.h({
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
                        current = current.map((tag, position) => position !== index ? tag : tag.main === true ? { name: tag.name } : { name: tag.name, main: true });
                        draw();
                        onChange(output(), null);
                        // 押した後も同じタグのトグルにフォーカスを残す
                        box.querySelector(`.pe-chip-main[data-index="${index}"]`)?.focus();
                    },
                },
                children: [MindmapPreview.icon(isMain ? "main" : "mainOff"), MindmapPreview.h({ tag: "span", attrs: { class: "tag-main-text" }, children: ["主題"] })],
            });
        };
        /** チップを描き直す */
        const draw = () => {
            box.replaceChildren(...current.map((entry, index) => MindmapPreview.h({
                tag: "span",
                attrs: {
                    class: `tag pe-chip${monospace ? " mono" : ""}${mainToggle ? " has-main" : ""}${mainToggle && entry.main === true ? " is-main" : ""}`,
                },
                children: [
                    mainToggle ? toggleButton(entry, index) : null,
                    entry.name,
                    MindmapPreview.h({
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
                        children: [MindmapPreview.icon("x")],
                    }),
                ],
            })), field, error, ...(suggestions === null
                ? []
                : [
                    MindmapPreview.h({
                        tag: "datalist",
                        attrs: { id: listId },
                        children: suggestions.map((tag) => MindmapPreview.h({ tag: "option", attrs: { value: tag } })),
                    }),
                ]));
        };
        draw();
        return box;
    }
    MindmapPreview.chipsInput = chipsInput;
})(MindmapPreview || (MindmapPreview = {}));
