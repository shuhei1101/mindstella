// 見本の記録: #127 の見本（../../127/assets/data.js が埋め込み先へ入れたもの）を、単一 UC『項目の詳細を読む』の『正常シナリオ（本文の語に一致した資料・調査へ移る）』の記録に書き換える
// 用語 G-1「特殊効果」。資料 A-1 はエイリアスを持たず、本文に「特殊効果」「エフェクト」「ワークスペース」（用語 G-2）を持つ
// 資料 A-2～A-7 と調査 R-1 はエイリアス「特殊効果」と説明を持ち、A-2 だけがエイリアス「エフェクト」も持つ。取り下げた資料 A-8 もエイリアス「特殊効果」を持つ
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);
  /** 種類の中の ID の項目 */
  const find = (kind, id) => data[kind].find((item) => item.id === id);

  const term = find("terms", "G-1");
  term.title = "特殊効果";
  term.meaning = "画面に重ねる演出";
  term.aliases = [];

  /** 資料の書き換え: タイトル・エイリアス・説明・本文 */
  const doc = (id, { title, aliases, description, body, ...rest }) => {
    const item = find("docs", id);
    Object.assign(item, { title, kind: "文書", deliverable: false, status: "下書き", tags: ["演出"], related: [], links: [] }, rest);
    if (aliases !== undefined) item.aliases = aliases;
    if (description !== undefined) item.description = description;
    data.bodies[item.body] = body;
  };

  doc("A-1", {
    title: "配信の演出の組み立て",
    status: "確認中",
    body: "配信の画面に重ねる特殊効果を、ノードをつないで組み立てる案。\n\n## やりたいこと\n\n- 特殊効果は、炎・煙・光の粒などのノードを重ねて作る\n- エフェクトの設定は 1 つのファイルにまとめ、ワークスペースに置く\n- 配信の途中でも、重ねる順と強さを変えられる\n",
  });
  doc("A-2", {
    title: "特殊効果のスキーマ",
    aliases: ["特殊効果", "エフェクト"],
    description: "特殊効果の設定ファイルのキーと型",
    body: "特殊効果の設定ファイル（`effects.yaml`）の形。\n\n| キー | 型 | 中身 |\n| --- | --- | --- |\n| `nodes` | 配列 | 重ねるノード |\n| `order` | 配列 | 重ねる順 |\n",
  });
  doc("A-3", { title: "炎ノード", aliases: ["特殊効果"], description: "炎を揺らしながら画面の下から重ねるノード", body: "炎の高さと揺れの速さを受け取り、画面の下から重ねる。\n" });
  doc("A-4", { title: "煙ノード", aliases: ["特殊効果"], description: "薄い煙を流して奥行きを出すノード", body: "煙の濃さと流れる向きを受け取る。\n" });
  doc("A-5", { title: "光の粒ノード", aliases: ["特殊効果"], description: "光の粒を散らして画面を明るく見せるノード", body: "粒の数と散らばる範囲を受け取る。\n" });
  doc("A-6", { title: "画面の揺れノード", aliases: ["特殊効果"], description: "大きな出来事のときに画面全体を短く揺らすノード", body: "揺れの強さと長さを受け取る。\n" });
  doc("A-7", { title: "特殊効果の重ね順の決め方", aliases: ["特殊効果"], description: "複数のノードを重ねるときの前後の決め方と、同じ順のときの扱い", body: "後から足したノードを手前に重ねる。\n" });
  doc("A-8", { title: "雷ノード", aliases: ["特殊効果"], description: "稲光を走らせるノード", withdrawn: true, reason: "光の粒ノードの強さで足りるため", body: "取り下げた案。\n" });

  data.research.push({
    id: "R-1",
    title: "特殊効果を重ねたときの描画の負荷",
    question: "特殊効果のノードを重ねたとき、配信の画面の描画がどこまで落ちるか",
    aliases: ["特殊効果"],
    description: "ノードを 1～8 個重ねたときの、OBS のブラウザソースのフレームレートの測り方と結果",
    conclusion: "6 個までは 60fps を保ち、8 個で 48fps まで落ちる",
    angles: ["重ねる数", "解像度"],
    created: "2026-10-03T09:54:53+00:00",
    updated: "2026-10-03T09:54:53+00:00",
  });

  element.textContent = JSON.stringify(data);
})();
