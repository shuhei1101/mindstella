// 部品のモックの見本。app.js（起動はしない）が出すスレッドの部品へ、状態ごとの引数を渡して台に置く
const Catalog = (() => {
  /** 見本の日時（UTC。画面は JST で出す） */
  const at = (hhmm) => `2026-10-12T${hhmm}:00+00:00`;

  /** 見本の項目のタイトル（記録に無い ID は null） */
  const TITLES = {
    "D-12": "移し替えが途中で失敗したときの扱い",
    "D-16": "版の範囲を渡して、当てる手順を返すコマンド",
    "D-15": "手順の YAML で使える操作の種類",
    "D-6": "破壊的な操作の確認",
    "D-5": "移し替えの前に写しを取る",
    "D-2": "版を記録する場所",
    "A-1": "#43 ワークスペースに版を記録し、プラグインを上げたときに移し替える",
    "A-9": "#50 スキルの手順（プロンプト）を、使いながら見えた動きに合わせて直す",
    "T-14": "移し替えの失敗の扱いを書く",
    "T-6": "移し替えの手順の YAML を点検する",
  };

  /** 見本のスレッド */
  const THREADS = {
    replied: {
      id: "TH-1", status: "open", tags: ["画面"], target: "D-12", events: [],
      summary: "D-12 の失敗時の扱いの相談。案 B（写しから戻す）で決まった",
      posts: [
        { id: "TH-1-1", author: "user", body: "D-12 は案 B にしたい。失敗したら写しから戻せるなら十分", created: at("01:20") },
        { id: "TH-1-2", author: "ai", body: "D-12 を案 B（写しから戻す）で決定にしました。戻す手順を書くタスクを T-14 に足しています。", created: at("01:24") },
      ],
    },
    asking: {
      id: "TH-2", status: "open", tags: ["起票"], target: "D-16", events: [],
      summary: "D-16 の比べた結果を Issue に起票してよいかの確認。返事待ち",
      posts: [
        { id: "TH-2-1", author: "ai", body: "D-16 の比べた結果を Issue に起票してよいですか。\n起票先は shuhei1101/mindstella、題は「版の範囲を渡して、当てる手順を返すコマンド」です。", created: at("04:02") },
      ],
    },
    noSummary: {
      id: "TH-3", status: "open", tags: ["資料"], target: "A-1", events: [],
      summary: null,
      posts: [
        { id: "TH-3-1", author: "user", body: "A-1 の背景の節が長いので、3 行にまとめてほしい。経緯は会話ログへのリンクで足りる", created: at("05:01") },
      ],
    },
    long: {
      id: "TH-4", status: "open", tags: ["調査", "画面"], target: null,
      events: [
        { kind: "closed", author: "user", reason: "手順は画面に出さないと分かった", created: at("00:20") },
        { kind: "reopened", author: "user", reason: null, created: at("00:29") },
      ],
      summary: "移し替えの手順を画面で見られるかの質問。今は見られず、T-6 の点検の結果を、版ごとの操作の一覧にした資料 A-9 にまとめることになった",
      posts: [
        { id: "TH-4-1", author: "user", body: "移し替えの手順（版ごとの YAML）は、プレビューのどこかで見られる？", created: at("00:10") },
        { id: "TH-4-2", author: "ai", body: "今のプレビューには手順を出す画面がありません。手順の YAML はプラグインの migrations/ の下にあり、ワークスペースの記録ではないためです。", created: at("00:12") },
        { id: "TH-4-3", author: "user", body: "それなら、手順の点検（T-6）の結果だけでも資料で読めるようにしてほしい。版ごとに、どの操作を当てるかが一覧で見たい", created: at("00:30") },
        { id: "TH-4-4", author: "ai", body: "T-6 の点検の結果を、版ごとの一覧にした資料 A-9 を足しました。操作の種類は D-15 で決めた 5 つに揃えています。\n確認が要る操作（消す・名前を変える）は D-6 のとおり印を付けました。", created: at("00:41") },
      ],
    },
    closed: {
      id: "TH-5", status: "closed", tags: ["画面"], target: "D-2",
      events: [{ kind: "closed", author: "user", reason: "config.yaml に書くと分かった", created: at("02:10") }],
      summary: "D-2 の版の置き場所の質問。config.yaml に書くと回答",
      posts: [
        { id: "TH-5-1", author: "user", body: "版はどこに書く？", created: at("02:00") },
        { id: "TH-5-2", author: "ai", body: "D-2 で決めたとおり、ワークスペースの config.yaml の version に書きます。", created: at("02:03") },
      ],
    },
    closedNoReason: {
      id: "TH-6", status: "closed", tags: [], target: "D-99",
      events: [{ kind: "closed", author: "user", reason: null, created: at("03:14") }],
      summary: "D-99 を取り下げてよいかの確認。消すことになった",
      posts: [
        { id: "TH-6-1", author: "ai", body: "D-99 は D-12 と重なっているので消してよいですか。", created: at("03:10") },
        { id: "TH-6-2", author: "user", body: "消してよい", created: at("03:12") },
      ],
    },
    aiClosed: {
      id: "TH-7", status: "closed", tags: ["画面"], target: "D-6",
      events: [{ kind: "closed", author: "ai", reason: "了解を受けた", created: at("04:36") }],
      summary: "D-6 の確認を出す操作の質問。消す・名前を変えるの 2 つと回答し、了解を受けた",
      posts: [
        { id: "TH-7-1", author: "user", body: "D-6 の確認は、どの操作で出る？", created: at("04:30") },
        { id: "TH-7-2", author: "ai", body: "D-6 で決めたとおり、消す・名前を変えるの 2 つで出ます。", created: at("04:32") },
        { id: "TH-7-3", author: "user", body: "了解", created: at("04:35") },
      ],
    },
    aiReopened: {
      id: "TH-9", status: "open", tags: ["資料"], target: "A-9",
      events: [
        { kind: "closed", author: "user", reason: null, created: at("02:42") },
        { kind: "reopened", author: "ai", reason: "質問に答えるため", created: at("02:50") },
      ],
      summary: "A-9 の一覧に確認の要否の列があるかの質問。あると回答",
      posts: [
        { id: "TH-9-1", author: "user", body: "A-9 の一覧に、確認の要否の列はある？", created: at("02:40") },
        { id: "TH-9-2", author: "ai", body: "A-9 の一覧の右端に、確認の要否の列があります。確認が要るのは D-6 で決めた 2 つの操作です。", created: at("02:51") },
      ],
    },
  };

  /** 見本のレビュー中の書き込み */
  const REVIEW = {
    newToItem: { id: "C-41", target: "D-5", target_title: null, loc: null, thread: null, body: "写しは git のコミットで取るほうが戻しやすいと思う", created: at("05:10") },
    newFree: { id: "C-42", target: null, target_title: null, loc: null, thread: null, body: "移し替えの手順の名前は版の番号だけでよい？", created: at("05:12") },
    reply: { id: "C-43", target: null, target_title: null, loc: null, thread: "TH-1", body: "了解。T-14 は今週中に書いてほしい", created: at("05:14") },
    replyToClosed: { id: "C-44", target: null, target_title: null, loc: null, thread: "TH-5", body: "version は文字列で持つ？", created: at("05:16") },
  };

  /** 何もしない操作 */
  const noop = () => {};

  /** コメントの一覧の引数（上書きを重ねる。talk はスレッドの画面の状態で、こちらも上書きを重ねる） */
  const propsOf = (over = {}) => {
    const { talk = {}, ...rest } = over;
    const items = rest.items ?? [];
    return {
      items,
      removed: [],
      checked: new Set(items.map((item) => item.id)),
      editing: null,
      editingIn: "list",
      editError: null,
      editBody: null,
      stale: new Map(),
      result: null,
      selected: null,
      titleOf: (id) => TITLES[id] ?? null,
      free: { target: null, body: "", status: "idle", count: null, detail: null, collapsed: false, on: { input: noop, save: noop, unquote: noop, copy: noop, focus: noop, blur: noop } },
      on: { close: noop, check: noop, checkAll: noop, send: noop, open: noop, edit: noop, saveEdit: noop, cancelEdit: noop, remove: noop, restore: noop, unloc: noop },
      ...rest,
      talk: {
        view: "list",
        reviewFrom: "list",
        reviewFocus: null,
        threads: Object.values(THREADS),
        filter: "open",
        tag: null,
        opened: null,
        composing: false,
        reasonOpen: false,
        reasonBody: "",
        titleOf: (id) => TITLES[id] ?? null,
        on: { filter: noop, tag: noop, clearTag: noop, compose: noop, open: noop, review: noop, back: noop, input: noop, reply: noop, reasonOpen: noop, reasonInput: noop, setStatus: noop, openId: noop },
        ...talk,
        reply: { body: "", status: "idle", count: 0, detail: null, ...talk.reply },
        action: { status: "idle", detail: null, ...talk.action },
      },
    };
  };

  /** パネルと同じ幅の枠に入れる */
  const pane = (nodes) => MindmapPreview.h({ tag: "div", attrs: { class: "pane" }, children: [nodes].flat().filter(Boolean) });

  /** 台（id）に要素を置く。並びを受けたときは順に置く */
  const place = (id, nodes) => {
    document.getElementById(id).append(...[nodes].flat().filter(Boolean));
  };

  /** 置いた要素の中で、セレクタに当たる要素へ見本の状態のクラスを付ける */
  const mark = (id, selector, className) => {
    document.getElementById(id).querySelector(selector)?.classList.add(className);
  };

  return { at, THREADS, REVIEW, propsOf, pane, place, mark };
})();
