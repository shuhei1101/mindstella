"use strict";
// タグの並び。主題のタグは名前の前に二重丸のマーカーを置く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 主題のタグの読み上げと `title` に出す文字 */
    const MAIN_TAG_LABEL = "主題";
    /** タグを記録の順のまま `span.tag` で並べる。文字列の要素は主題でないタグとして出す */
    function tagList(values) {
        const fragment = document.createDocumentFragment();
        for (const value of values ?? []) {
            const name = typeof value === "string" ? value : value.name;
            const isMain = typeof value !== "string" && value.main === true;
            if (!isMain) {
                fragment.append(MindmapPreview.h({ tag: "span", attrs: { class: "tag" }, children: [name] }));
                continue;
            }
            // 主題: マーカーは装飾として隠し、「主題」の文字は読み上げだけに出す
            const spoken = MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: [MAIN_TAG_LABEL] });
            fragment.append(MindmapPreview.h({ tag: "span", attrs: { class: "tag is-main", title: MAIN_TAG_LABEL }, children: [MindmapPreview.icon("main"), spoken, name] }));
        }
        return fragment;
    }
    MindmapPreview.tagList = tagList;
})(MindmapPreview || (MindmapPreview = {}));
