"use strict";
// 保存待ちの編集を記録に当てた表示の値と、項目・キー・案の保存待ちの印の種類。
var MindmapPreview;
(function (MindmapPreview) {
    /** 追加する項目の仮の ID の頭 */
    MindmapPreview.NEW_ID_PREFIX = "new-";
    /** 設定の編集の向け先 */
    MindmapPreview.SETTINGS_TARGET = "settings";
    /** 値の入った案（記号と中身）を作る */
    function optionOf(key, value) {
        return { key, content: "", ...value };
    }
    /** 記録の写しに保存待ちの編集を溜めた順に当て、画面に出す値を返す（元の記録は変えない） */
    function applyEdits(data, edits) {
        const applied = structuredClone(data);
        const find = (id) => {
            for (const kind of MindmapPreview.KIND_KEYS) {
                const found = applied[kind].find((item) => item.id === id);
                if (found !== undefined)
                    return found;
            }
            return undefined;
        };
        for (const edit of edits) {
            const key = edit.key ?? "";
            if (edit.op === "setting") {
                applied.settings[key] = edit.value;
            }
            else if (edit.op === "item-add") {
                const kind = key;
                if (!MindmapPreview.KIND_KEYS.includes(kind))
                    continue;
                const values = { ...edit.value };
                const item = { id: edit.target, created: edit.created, updated: edit.created, ...values };
                // 本文の文字列は、本文の置き場所に移す
                if (typeof values["body"] === "string") {
                    item.body = `${edit.target}.md`;
                    applied.bodies[item.body] = values["body"];
                }
                applied[kind].push(item);
            }
            else {
                const item = find(edit.target);
                if (item === undefined)
                    continue;
                if (edit.op === "set") {
                    if (key === "body") {
                        const name = item.body ?? `${item.id}.md`;
                        item.body = name;
                        applied.bodies[name] = String(edit.value ?? "");
                    }
                    else if (edit.value === null) {
                        delete item[key];
                    }
                    else {
                        item[key] = edit.value;
                    }
                }
                else if (edit.op === "option-add") {
                    item.options = [...(item.options ?? []), optionOf(key, edit.value)];
                }
                else if (edit.op === "option-edit") {
                    item.options = (item.options ?? []).map((option) => option.key === key ? { ...option, ...edit.value } : option);
                }
                else if (edit.op === "adopt") {
                    item.options = (item.options ?? []).map((option) => ({ ...option, adopted: option.key === edit.value }));
                }
            }
        }
        return applied;
    }
    MindmapPreview.applyEdits = applyEdits;
    /** 項目（`key` を渡せばそのキーか案）に付ける保存待ちの印の種類。当たる編集が無ければ null */
    function pendingMarkOf({ edits, blocked, target, key, }) {
        const hits = edits.filter((edit) => {
            if (edit.target !== target)
                return false;
            // キーを渡さないときは、その項目への編集の全て
            if (key === undefined)
                return true;
            return edit.key === key || (edit.op === "adopt" && edit.value === key);
        });
        if (hits.length === 0)
            return null;
        if (hits.some((edit) => blocked.has(edit.id)))
            return "blocked";
        if (key === undefined && hits.some((edit) => edit.op === "item-remove"))
            return "remove";
        return "pending";
    }
    MindmapPreview.pendingMarkOf = pendingMarkOf;
})(MindmapPreview || (MindmapPreview = {}));
