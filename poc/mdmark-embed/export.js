// PoC: 開いている資料 1 件を、mdmark の CSS と JavaScript・用語の索引・本文を中に持つ 1 枚の HTML にする（ブラウザだけで組み立てる）

/** 書き出した HTML の mdmark に渡す機能（プレビューと重なる機能と、外の CDN から highlight.js を読むコードの色付けを止め、用語のツールチップは mdmark が描く） */
const EXPORT_FEATURES = { backlinks: false, comments: false, print: false, views: false, syntax: false };

/** script・style の要素を閉じる・開くタグを含むと、中に持たせた要素が壊れる */
function rejectTags({ text, tags, what }) {
  const lower = text.toLowerCase();
  const found = tags.find((tag) => lower.includes(tag));
  if (found !== undefined) throw new Error(`${what} が ${found} を含むため、1 枚の HTML に入れられません`);
}

/** 雛形が読む mdmark の CSS と JavaScript の URL と integrity */
function mdmarkSources() {
  const link = document.querySelector('link[rel="stylesheet"][href*="/mdmark@"]');
  const map = JSON.parse(document.querySelector('script[type="importmap"]').textContent);
  const [jsUrl, jsIntegrity] = Object.entries(map.integrity)[0];
  return { cssUrl: link.href, cssIntegrity: link.integrity, jsUrl, jsIntegrity };
}

/** 記録から mdmark の索引を作る。開いている資料自身と取り下げた資料・調査は入れない */
function mdmarkIndex({ data, selfId }) {
  const usable = (item) => item.id !== selfId && item.withdrawn !== true;
  const docs = [...data.docs, ...data.research].filter(usable).map((item) => ({
    id: item.id,
    path: `${item.id}.md`,
    title: item.title,
    description: item.description ?? "",
    aliases: item.aliases ?? [],
  }));
  const terms = data.terms.map((item) => ({ id: item.id, term: item.title, aliases: item.aliases ?? [], meaning: item.meaning ?? "" }));
  return { docs: [{ id: selfId, path: `${selfId}.md`, title: selfId }, ...docs], terms };
}

window.pocExportDocument = async ({ id }) => {
  const data = await (await fetch("api/records")).json();
  const item = data.docs.find((doc) => doc.id === id);
  const markdown = data.bodies[item.body];
  const { cssUrl, cssIntegrity, jsUrl, jsIntegrity } = mdmarkSources();
  // 雛形と同じ integrity で中身を確かめて取る
  const css = await (await fetch(cssUrl, { integrity: cssIntegrity })).text();
  const js = await (await fetch(jsUrl, { integrity: jsIntegrity })).text();
  rejectTags({ text: js, tags: ["</script", "<script"], what: "mdmark の JavaScript" });
  rejectTags({ text: css, tags: ["</style"], what: "mdmark の CSS" });
  // 本文と索引は JSON で持たせ、`<` を逃がして要素を閉じられないようにする
  const payload = JSON.stringify({ markdown, docId: id, index: mdmarkIndex({ data, selfId: id }), features: EXPORT_FEATURES }).replaceAll("<", "\\u003c");
  const title = item.title.replaceAll("&", "&amp;").replaceAll("<", "&lt;");
  return `<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title}</title>
<style>${css}</style>
<style>body { margin: 0; padding: 24px 16px; } main { max-width: 860px; margin: 0 auto; }</style>
</head><body><main id="doc"></main>
<script type="application/json" id="doc-data">${payload}</script>
<script type="text/plain" id="doc-mdmark">${js}</script>
<script type="module">
const source = document.getElementById("doc-mdmark").textContent;
const url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
const mdmark = await import(url);
const { markdown, docId, index, features } = JSON.parse(document.getElementById("doc-data").textContent);
mdmark.mount(document.getElementById("doc"), { markdown, index, docId, config: { features } });
window.docReady = true;
</script>
</body></html>
`;
};
