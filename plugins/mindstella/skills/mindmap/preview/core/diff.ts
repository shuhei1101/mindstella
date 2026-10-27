// 差分の表示の計算。変更履歴で選んだ時点から印を付ける項目を決め、項目の `history` から前の版を組み立て、本文・記法の行と図の要素を比べる。DOM は描かず、描くのは画面が持つ。

namespace MindmapPreview {
  /** 変更履歴で選んだ時点と、その時点で印を付ける項目 */
  export type DiffPoint = {
    /** `since`・`pending`・まとまりの ID */
    sel: string;
    /** 札と詳細パネルに出す名前 */
    name: string;
    /** 日時（JST）。「前回開いてから」は `{日時} より後` */
    sub: string;
    /** 新規の印を付ける ID（`removed` にある ID は入れない） */
    added: Set<string>;
    /** 変更の印を付ける ID（`added`・`removed` にある ID は入れない） */
    changed: Set<string>;
    /** この時点の変更履歴の始まりの `seq`（これより大きい `seq` を戻す） */
    fromSeq: number;
    /** この時点の終わりの `seq`。null は今まで（`since`・`pending`） */
    untilSeq: number | null;
    /** 消した項目（ID → 消した項目）。まとまり・`pending` の `removed` を合わせたもの */
    removed: Map<string, RemovedItem>;
  };

  /** 選んだ時点で消した項目 1 件 */
  export type RemovedItem = {
    id: string;
    /** 消した項目の種類（サーバーの種類の名前） */
    kind: "decision" | "task" | "research" | "doc" | "term" | "note" | "log";
    /** 消したときのタイトル */
    title: string;
  };

  /** 選んだ時点の前と後の項目・本文と、組み立てられなかったこと */
  export type VersionPair = {
    /** 前の版の項目。組み立てられないとき null */
    before: Item | null;
    /** 後の版の項目（古いまとまりなら、そのまとまりの直後の形） */
    after: Item;
    /** 前の本文。本文を持たなければ空文字列、組み立てられないとき null */
    beforeBody: string | null;
    /** 後の本文 */
    afterBody: string;
    /** その時点の変更履歴が、保持する回数を超えて消えている */
    trimmed: boolean;
    /** `body_diff` の `now` が当てる先の行と合わなかった */
    bodyUnavailable: boolean;
  };

  /** 行の差分の 1 つ（同じ・足した・消した行のまとまり） */
  export type LinePart = {
    kind: "same" | "added" | "removed";
    /** 行（改行を含まない） */
    lines: string[];
  };

  /** 消した行のかたまりと、差し込む場所 */
  export type RemovedBlock = {
    lines: string[];
    /** 直後に来る今の本文の 1 始まりの行。本文の最後なら null */
    beforeLine: number | null;
    /** かたまりが表の本体の行だけのとき、前の版のその表の見出しの行と区切りの行 */
    tableHeader: string[] | null;
  };

  /** 語の差分の 1 つ（変えた行の対の片方の文字の、同じ・足した・消した部分）。前の側は `same`・`removed`、今の側は `same`・`added` だけを持つ */
  export type InlinePart = {
    kind: "same" | "added" | "removed";
    /** 部分の文字 */
    text: string;
  };

  /** 語の差分。変えた行の対の前と今を、それぞれの文字の頭からの部分の並びにしたもの */
  export type InlineDiff = {
    /** 前の文字の部分。`text` をつなぐと前の文字に戻る */
    before: InlinePart[];
    /** 今の文字の部分。`text` をつなぐと今の文字に戻る */
    after: InlinePart[];
  };

  /** 図の差分。今の版の図で色を付ける要素と、消したものの名前 */
  export type DiagramDiff = {
    /** 足したノード・辺の要素（sequenceDiagram はメッセージの文字の要素） */
    added: Element[];
    /** 文字が変わったノード・辺の要素 */
    changed: Element[];
    /** 前にだけあるノード・辺の文字（「消したもの」に並べる） */
    removed: string[];
  };

  /** `Diff.diffLines` に渡す `timeout`（ミリ秒）。切り替えの 200ms のうち、図の描画に使った残りを本文 1 つの差分に充てる */
  export const LINE_DIFF_TIMEOUT_MS = 40;

  /** 変えた行の対で、同じ部分の文字数を 2 つのうち短い方の文字数で割った値がこれに満たないとき、語の面を付けない（ほとんど書き換えた行は、語の面が行のほぼ全体に付いて行の面と見分けられない） */
  export const WORD_PAIR_MIN_SAME_RATIO = 0.5;

  /** `Diff.diffArrays`（sequenceDiagram のメッセージの並び）に渡す `timeout`（ミリ秒） */
  export const ARRAY_DIFF_TIMEOUT_MS = 20;

  /** ノード・辺に色を付ける mermaid の図の種類（記法の 1 行目の語）。それ以外は図の枠に色を付ける */
  export const COLORED_DIAGRAM_TYPES: readonly string[] = [
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "erDiagram",
    "stateDiagram-v2",
  ];

  /** 消した項目の種類（`RemovedItem.kind`）から、その項目を出す画面の種類を引く */
  export const REMOVED_KIND_TAB: Record<RemovedItem["kind"], Kind> = {
    decision: "decisions",
    task: "tasks",
    research: "research",
    doc: "docs",
    term: "terms",
    note: "notes",
    log: "logs",
  };

  /** 「まだまとめていない変更」の名前と補足 */
  const PENDING_NAME = "まだまとめていない変更";
  const PENDING_SUB = "AI がまだ区切っていない書き換え";

  /** 「前回開いてから」の名前 */
  const SINCE_NAME = "前回開いてから";

  /** 選んだ時点の名前・補足・印・範囲から、時点を組み立てる */
  function buildPoint({
    sel,
    name,
    sub,
    groups,
    fromSeq,
    untilSeq,
  }: {
    sel: string;
    name: string;
    sub: string;
    groups: { added: string[]; changed: string[]; removed?: RemovedItem[] }[];
    fromSeq: number;
    untilSeq: number | null;
  }): DiffPoint {
    // `removed` を持たないまとまりは、何も足さない
    const removed = new Map(groups.flatMap((group) => group.removed ?? []).map((item) => [item.id, item]));
    // 合わせた範囲で足して消した項目は、消した項目としてだけ出す
    const added = new Set(groups.flatMap((group) => group.added).filter((id) => !removed.has(id)));
    // 足した項目は、変えても変更の印にしない
    const changed = new Set(
      groups.flatMap((group) => group.changed).filter((id) => !added.has(id) && !removed.has(id)),
    );
    return { sel, name, sub, added, changed, fromSeq, untilSeq, removed };
  }

  /** 選んだ時点で消した項目のうち、その画面の種類のものを ID の順に返す。時点が null のときは空 */
  export function removedOf({ point, kind }: { point: DiffPoint | null; kind: Kind }): RemovedItem[] {
    if (point === null) return [];
    return [...point.removed.values()]
      .filter((item) => REMOVED_KIND_TAB[item.kind] === kind)
      .sort((a, b) => compareIds(a.id, b.id));
  }

  /** 選んだ時点の識別子から、印を付ける項目と変更履歴の範囲を決める。差分を出さないときは null */
  export function resolveDiffPoint(changes: Changes, sel: string | null, since: OpenedPoint): DiffPoint | null {
    if (sel === null) return null;
    const sets = changes.sets;
    // 先頭のまとまりまでの変更履歴（それより後がまだまとめていない分）
    const latestSeq = sets[0]?.until_seq ?? 0;
    if (sel === "pending") {
      // まだまとめていない変更が無い
      const pending = changes.pending;
      if (pending.added.length === 0 && pending.changed.length === 0 && (pending.removed ?? []).length === 0) return null;
      return buildPoint({ sel, name: PENDING_NAME, sub: PENDING_SUB, groups: [changes.pending], fromSeq: latestSeq, untilSeq: null });
    }
    if (sel === "since") {
      // 日時は比べず、開いた時点の通し番号より大きいまとまりを範囲にする
      const inRange = sets.filter((set) => set.until_seq > since.seq);
      const oldest = inRange.at(-1);
      // 範囲で一番古いまとまりの 1 つ前の `until_seq` から。範囲にまとまりが無ければ、先頭のまとまりの `until_seq` から
      const fromSeq = oldest === undefined ? latestSeq : (sets[sets.indexOf(oldest) + 1]?.until_seq ?? 0);
      return buildPoint({
        sel,
        name: SINCE_NAME,
        sub: `${formatJst(since.at)} より後`,
        groups: [...inRange, changes.pending],
        fromSeq,
        untilSeq: null,
      });
    }
    const position = sets.findIndex((set) => set.id === sel);
    // 記録に無いまとまり
    if (position < 0) return null;
    const set = sets[position];
    if (set === undefined) return null;
    return buildPoint({
      sel,
      name: set.summary,
      sub: formatJst(set.at),
      groups: [set],
      fromSeq: sets[position + 1]?.until_seq ?? 0,
      untilSeq: set.until_seq,
    });
  }

  /** サーバーが本文を行に分けるのと同じ分け方（Python の `splitlines`）で、本文を行の並びにする */
  function bodyLines(text: string): string[] {
    const lines = text.split(/\r\n|[\n\r\v\f\u001c\u001d\u001e\u0085\u2028\u2029]/);
    // 末尾の改行で出る空の最後の要素は、行ではない
    if (lines.at(-1) === "") lines.pop();
    return lines;
  }

  /** 本文に差分を後ろの箇所から当てて前の本文にする。`now` が当てる先の行と合わなければ null */
  function applyBodyDiff(text: string, hunks: BodyDiffHunk[]): string | null {
    const lines = bodyLines(text);
    for (const hunk of [...hunks].sort((a, b) => b.line - a.line)) {
      const start = hunk.line - 1;
      const end = start + hunk.now.length;
      // 当てる先が本文の範囲を出るか、`now` と違う
      if (end > lines.length || hunk.now.some((line, offset) => lines[start + offset] !== line)) return null;
      lines.splice(start, hunk.now.length, ...hunk.before);
    }
    return lines.length > 0 ? `${lines.join("\n")}\n` : "";
  }

  /** 項目の版（キーと本文）。変更履歴を当てる途中の形 */
  type Version = { item: Item; body: string | null };

  /** 変更履歴の 1 回分を版に当てる（前に無かったキーは消し、本文は差分で戻す）。本文を戻せなかったら本文を null にする */
  function undoEntry(version: Version, entry: HistoryEntry): Version {
    const item: Record<string, unknown> = { ...version.item };
    let body = version.body;
    for (const [key, value] of Object.entries(entry.before)) {
      // 本文の名前は項目に残し、本文は差分で戻す
      if (key === "body") {
        // 本文を初めて足した回: 前は本文が無い
        if (value === null) body = "";
        // 資料の本文の形式を替えた回: 前の形式のファイル名に戻す
        else if (typeof value === "string") item["body"] = value;
        continue;
      }
      if (value === null) delete item[key];
      else item[key] = value;
    }
    if (entry.body_diff !== undefined && body !== null) body = applyBodyDiff(body, entry.body_diff);
    return { item: item as Item, body };
  }

  /** 今の項目と本文に `history` を新しいものから当て、選んだ時点の前後の版を作る */
  export function buildVersions(item: Item, body: string, point: DiffPoint): VersionPair {
    const history = [...(item.history ?? [])].sort((a, b) => b.seq - a.seq);
    let after: Version = { item, body };
    let before: Version = { item, body };
    let inRange = false;
    for (const entry of history) {
      // 後の版: 選んだ時点の終わりより後の変更履歴を戻した形
      if (point.untilSeq !== null && entry.seq > point.untilSeq) after = undoEntry(after, entry);
      if (entry.seq <= point.fromSeq) continue;
      before = undoEntry(before, entry);
      if (point.untilSeq === null || entry.seq <= point.untilSeq) inRange = true;
    }
    // 選んだ時点の範囲に変更履歴が 1 回も無いか、範囲の中の回が消えている（消した回の最大の `seq` が範囲の始まりより大きい）: 保持する回数を超えて消えた
    if (!inRange || (item.history_dropped_seq ?? 0) > point.fromSeq) {
      return { before: null, after: after.item, beforeBody: null, afterBody: after.body ?? body, trimmed: true, bodyUnavailable: false };
    }
    const bodyUnavailable = before.body === null || after.body === null;
    return {
      before: before.item,
      after: after.item,
      beforeBody: before.body,
      afterBody: after.body ?? body,
      trimmed: false,
      bodyUnavailable,
    };
  }

  /** jsdiff が返した値（行の並びを `\n` でつないだもの）を、行の並びにする */
  function splitLines(value: string): string[] {
    return (value.endsWith("\n") ? value.slice(0, -1) : value).split("\n");
  }

  /** 前後の文字列を行ごとに比べる。jsdiff が読めていないときと、打ち切ったときは null */
  export function diffLineParts(before: string, after: string): LinePart[] | null {
    if (missingLibraries(["jsdiff"]).length > 0) return null;
    const parts = Diff.diffLines(before, after, { timeout: LINE_DIFF_TIMEOUT_MS });
    // 時間内に終わらなかった
    if (parts === undefined) return null;
    return parts.map((part) => ({
      kind: part.added ? "added" : part.removed ? "removed" : "same",
      lines: splitLines(part.value),
    }));
  }

  /** 本文を marked の最上位の token ごとに分けた 1 つの塊 */
  export type SideBlock = {
    /** 塊の最初の行（1 始まり） */
    start: number;
    /** 塊の最後の行（1 始まり） */
    end: number;
    /** 塊の原文（末尾の改行を除く） */
    raw: string;
    /** 塊の中で、左の列は消した行、右の列は足した行のうち空行でない行の番号。空なら変えていない塊 */
    changed: Set<number>;
  };

  /** 左右の列で同じ高さに揃える 1 行。片側が空ならその側は縞の空きになる */
  export type SideRow = {
    /** 変えた行か。変えていない塊の対の行は偽 */
    changed: boolean;
    /** 左の列（選んだ時点）の塊 */
    left: SideBlock[];
    /** 右の列（今）の塊 */
    right: SideBlock[];
  };

  /** 本文を、marked の最上位の token（空行の token を除く）ごとの塊に分ける。塊の変えた行は空で返す */
  function topBlocks(source: string): SideBlock[] {
    const blocks: SideBlock[] = [];
    let line = 0;
    for (const token of marked.lexer(source)) {
      if (token.type !== "space") {
        const raw = token.raw.replace(/\n+$/, "");
        blocks.push({ start: line + 1, end: line + raw.split("\n").length, raw, changed: new Set() });
      }
      line += token.raw.split("\n").length - 1;
    }
    return blocks;
  }

  /** 行の差分の各行の種類（前の版・今の版の 1 始まりの行）と、変えていない行の前の版 → 今の版の行の対応 */
  type SideLineKinds = {
    before: (LinePart["kind"] | null)[];
    after: (LinePart["kind"] | null)[];
    map: (number | null)[];
  };

  /** 行の差分から、前の版と今の版の各行の種類と、変えていない行の前の版 → 今の版の行の対応を作る */
  function sideLineKinds(parts: LinePart[]): SideLineKinds {
    const before: SideLineKinds["before"] = [null];
    const after: SideLineKinds["after"] = [null];
    const map: SideLineKinds["map"] = [null];
    for (const part of parts) {
      for (const _ of part.lines) {
        if (part.kind !== "added") {
          before.push(part.kind);
          map.push(part.kind === "same" ? after.length : null);
        }
        if (part.kind !== "removed") after.push(part.kind);
      }
    }
    return { before, after, map };
  }

  /** 塊の範囲の行のうち、その種類（消した・足した）で空行でない行を塊の変えた行に入れる */
  function markChangedLines({
    blocks,
    kinds,
    lines,
    kind,
  }: {
    blocks: SideBlock[];
    kinds: (LinePart["kind"] | null)[];
    lines: string[];
    kind: "removed" | "added";
  }): void {
    for (const block of blocks) {
      for (let line = block.start; line <= block.end; line += 1) {
        if (kinds[line] === kind && (lines[line - 1] ?? "").trim() !== "") block.changed.add(line);
      }
    }
  }

  /** 本文を行の並びにする（末尾の改行で出る空の最後の要素は行ではない） */
  export function linesOfText(text: string): string[] {
    const lines = text.split("\n");
    if (lines.at(-1) === "") lines.pop();
    return lines;
  }

  /** 前後の Markdown の本文を塊に分け、変えていない塊を向かい合わせた左右の列の行にする。行の差分を打ち切ったら null */
  export function sideBySideRows({ before, after }: { before: string; after: string }): SideRow[] | null {
    const parts = diffLineParts(before, after);
    if (parts === null) return null;
    const kinds = sideLineKinds(parts);
    const beforeBlocks = topBlocks(before);
    const afterBlocks = topBlocks(after);
    markChangedLines({ blocks: beforeBlocks, kinds: kinds.before, lines: linesOfText(before), kind: "removed" });
    markChangedLines({ blocks: afterBlocks, kinds: kinds.after, lines: linesOfText(after), kind: "added" });
    /** 前の版の x 番目の塊と対になる、今の版の from 番目以降の変えていない同じ塊の番号。無ければ -1 */
    const anchorOf = (x: number, from: number): number => {
      const block = beforeBlocks[x];
      if (block === undefined || block.changed.size > 0) return -1;
      const target = kinds.map[block.start];
      for (let k = from; k < afterBlocks.length; k += 1) {
        const other = afterBlocks[k];
        if (other === undefined || target === null || target === undefined) return -1;
        // 対応する行から始まる塊で、変えておらず原文が同じときだけ対にする
        if (other.start === target) return other.changed.size === 0 && other.raw === block.raw ? k : -1;
        if (other.start > target) return -1;
      }
      return -1;
    };
    const rows: SideRow[] = [];
    let i = 0;
    let j = 0;
    while (i < beforeBlocks.length || j < afterBlocks.length) {
      // 次の区切り（変えていない塊の対）を探す。無ければ末尾まで
      let ai = beforeBlocks.length;
      let aj = afterBlocks.length;
      for (let x = i; x < beforeBlocks.length; x += 1) {
        const k = anchorOf(x, j);
        if (k >= 0) {
          ai = x;
          aj = k;
          break;
        }
      }
      const left = beforeBlocks.slice(i, ai);
      const right = afterBlocks.slice(j, aj);
      // 区切りの間の変えた塊: 数が両側で同じなら 1 つずつ、違えばまとめて 1 つの行にする
      if (left.length === right.length) {
        left.forEach((block, offset) => {
          const opposite = right[offset];
          if (opposite !== undefined) rows.push({ changed: true, left: [block], right: [opposite] });
        });
      } else {
        rows.push({ changed: true, left, right });
      }
      const anchorLeft = beforeBlocks[ai];
      const anchorRight = afterBlocks[aj];
      if (anchorLeft !== undefined && anchorRight !== undefined) rows.push({ changed: false, left: [anchorLeft], right: [anchorRight] });
      i = ai + 1;
      j = aj + 1;
    }
    return rows;
  }

  /** HTML の本文の差分: 今の本文で足した行と変えた行（今の本文の 1 始まりの行）と、消しただけの箇所があるか */
  export type HtmlChangedLines = { added: number[]; changed: number[]; removedOnly: boolean };

  /** 前後の HTML の原文を行ごとに比べ、足した行・変えた行（消した行と入れ替えた行）と、足した行と隣り合わない消した行があるかを返す。差分を打ち切ったら null */
  export function htmlChangedLines(before: string, after: string): HtmlChangedLines | null {
    const parts = diffLineParts(before, after);
    if (parts === null) return null;
    const added: number[] = [];
    const changed: number[] = [];
    let removedOnly = false;
    let nowLine = 0;
    parts.forEach((part, position) => {
      const neighbors = [parts[position - 1]?.kind, parts[position + 1]?.kind];
      if (part.kind === "removed") {
        // 足した並びに隣らない消した並びは、描いた結果に印を付けられない
        if (!neighbors.includes("added")) removedOnly = true;
        return;
      }
      if (part.kind === "added") {
        // 消した並びに隣る足した並びは変えた行、それ以外は足した行（空白だけの行は入れない）
        const target = neighbors.includes("removed") ? changed : added;
        part.lines.forEach((line, offset) => {
          if (line.trim() !== "") target.push(nowLine + offset + 1);
        });
      }
      nowLine += part.lines.length;
    });
    return { added, changed, removedOnly };
  }

  /** 行の差分のうち、消した行のすぐ後に同じ行の数の足した行が続くところを、変えた行の対にして返す（`parts` の添え字の並び。前から 1 行ずつが対になる） */
  export function pairedParts(parts: LinePart[]): { removed: number; added: number }[] {
    const pairs: { removed: number; added: number }[] = [];
    parts.forEach((part, position) => {
      const next = parts[position + 1];
      // 消した行のすぐ後に、同じ行の数の足した行が続く（間に変えない行を挟まない）
      if (part.kind === "removed" && next?.kind === "added" && next.lines.length === part.lines.length) {
        pairs.push({ removed: position, added: position + 1 });
      }
    });
    return pairs;
  }

  /** 語の区切りに使う分け方。ブラウザが `Intl.Segmenter` を持たなければ null（jsdiff の既定の区切りで比べる） */
  let wordSegmenter: Intl.Segmenter | null | undefined;

  /** 語の区切りに使う分け方を、最初に呼んだときに 1 つ作って使い回す */
  function segmenterOf(): Intl.Segmenter | null {
    if (wordSegmenter === undefined) {
      wordSegmenter = typeof Intl.Segmenter === "function" ? new Intl.Segmenter("ja", { granularity: "word" }) : null;
    }
    return wordSegmenter;
  }

  /** 部分の文字をつないだもの */
  function joinText(parts: InlinePart[]): string {
    return parts.map((part) => part.text).join("");
  }

  /** 変えた行の対の前と今の文字を語の単位で比べる。jsdiff を読めていない・時刻を過ぎた・打ち切った・同じ部分が少ない・部分をつないでも元の文字に戻らないときは null */
  export function diffInline(before: string, after: string, deadline: number): InlineDiff | null {
    if (missingLibraries(["jsdiff"]).length > 0) return null;
    const remaining = deadline - performance.now();
    if (remaining <= 0) return null;
    const segmenter = segmenterOf();
    const parts = Diff.diffWords(before, after, { timeout: remaining, ...(segmenter === null ? {} : { intlSegmenter: segmenter }) });
    // 時間内に終わらなかった
    if (parts === undefined) return null;
    const sameLength = parts.filter((part) => !part.added && !part.removed).reduce((total, part) => total + part.value.length, 0);
    const shorter = Math.min(before.length, after.length);
    // ほとんど書き換えた対には面を付けない
    if (shorter === 0 || sameLength / shorter < WORD_PAIR_MIN_SAME_RATIO) return null;
    const inline: InlineDiff = {
      before: parts.filter((part) => !part.added).map((part) => ({ kind: part.removed ? "removed" : "same", text: part.value })),
      after: parts.filter((part) => !part.removed).map((part) => ({ kind: part.added ? "added" : "same", text: part.value })),
    };
    // 同じ部分の文字が空白の違いで片側の文字とずれたとき、範囲を元の文字に当てられない
    if (joinText(inline.before) !== before || joinText(inline.after) !== after) return null;
    return inline;
  }

  /** 行の差分の並びから、消した行のかたまりごとに、今の本文のどの行の前へ差し込むかを返す */
  export function placeRemovedBlocks(parts: LinePart[]): RemovedBlock[] {
    const blocks: RemovedBlock[] = [];
    // 前の版の行を前から並べておく（表の見出しをさかのぼって引くため）
    const beforeLines: string[] = [];
    let nowCount = 0;
    parts.forEach((part, position) => {
      if (part.kind === "removed") {
        const start = beforeLines.length;
        const followsNowLine = parts.slice(position + 1).some((next) => next.kind !== "removed");
        const tableBody =
          part.lines.every((line) => line.startsWith("|")) && (beforeLines[start - 1] ?? "").startsWith("|");
        blocks.push({
          lines: part.lines,
          // 次に来る今の本文の行（無ければ本文の最後）
          beforeLine: followsNowLine ? nowCount + 1 : null,
          tableHeader: tableBody ? tableHeaderOf(beforeLines, start) : null,
        });
        beforeLines.push(...part.lines);
        return;
      }
      // 同じ・足した行は今の本文の行を、同じ行は前の版の行も数え進める
      nowCount += part.lines.length;
      if (part.kind === "same") beforeLines.push(...part.lines);
    });
    return blocks;
  }

  /** 前の版の `start` 行目（0 始まり）から続く表の、頭までさかのぼった見出しの行と区切りの行 */
  function tableHeaderOf(beforeLines: string[], start: number): string[] | null {
    let top = start;
    while (top > 0 && (beforeLines[top - 1] ?? "").startsWith("|")) top -= 1;
    const header = beforeLines[top];
    const separator = beforeLines[top + 1];
    if (header === undefined || separator === undefined) return null;
    return [header, separator];
  }

  /** 図の種類（記法の 1 行目の語）→ 突き合わせの方式 */
  type DiagramFlavor = "flowchart" | "sequence" | "class" | "er" | "state";

  /** 図の種類（記法の 1 行目の語）から、突き合わせの方式を決める。色を付けない種類は null */
  function flavorOf(type: string): DiagramFlavor | null {
    if (!COLORED_DIAGRAM_TYPES.includes(type)) return null;
    const flavors: Record<string, DiagramFlavor> = {
      flowchart: "flowchart",
      graph: "flowchart",
      sequenceDiagram: "sequence",
      classDiagram: "class",
      erDiagram: "er",
      "stateDiagram-v2": "state",
    };
    return flavors[type] ?? null;
  }

  /** 図のノード 1 つ・辺 1 本の、突き合わせの材料。`name` は消したものの一覧に出す名前（無ければ `text`） */
  type DiagramPart = { key: string; text: string; name?: string; element: Element; box?: DOMRect };

  /** 前の版の材料。色を付ける要素は今の版だけが持つ */
  type PreviousPart = Pick<DiagramPart, "key" | "text" | "name">;

  /** 図 1 枚のノードと辺 */
  type DiagramParts<Part> = { nodes: Map<string, Part>; edges: Part[] };

  /** 空白を 1 つにして前後を除く */
  function normalized(text: string | null | undefined): string {
    return (text ?? "").replace(/\s+/g, " ").trim();
  }

  /** ノードの要素の id から「{描画の id}-」と末尾の「-{連番}」を外したものを、ノードの鍵にする */
  function nodeKey(element: Element, prefix: string): string {
    const id = element.id.startsWith(`${prefix}-`) ? element.id.slice(prefix.length + 1) : element.id;
    return id.replace(/-\d+$/, "");
  }

  /** ノードの要素の、図の座標での枠 */
  function boxOf(element: SVGGraphicsElement): DOMRect {
    const box = element.getBBox();
    const matrix = element.transform.baseVal.consolidate()?.matrix;
    return new DOMRect(box.x + (matrix?.e ?? 0), box.y + (matrix?.f ?? 0), box.width, box.height);
  }

  /** 点に一番近い枠のノードの鍵 */
  function nearestKey(nodes: DiagramPart[], point: DOMPoint): string {
    let best = "?";
    let bestDistance = Number.POSITIVE_INFINITY;
    for (const node of nodes) {
      const box = node.box;
      if (box === undefined) continue;
      const dx = Math.max(box.x - point.x, 0, point.x - (box.x + box.width));
      const dy = Math.max(box.y - point.y, 0, point.y - (box.y + box.height));
      const distance = dx * dx + dy * dy;
      if (distance < bestDistance) {
        bestDistance = distance;
        best = node.key;
      }
    }
    return best;
  }

  /** 辺の `data-id` から端点の鍵を引く。端点はノードの鍵の一覧と突き合わせて決める（ノードの id に `_` を含んでも取り違えない） */
  function edgeEnds(dataId: string, nodeKeys: Set<string>): string {
    const rest = dataId.replace(/^(L_|id_)/, "").replace(/_\d+$/, "").replace(/-\d+(?=_|$)/g, "");
    const cuts = [...rest.matchAll(/_/g)].map((found) => found.index ?? 0);
    const matched = cuts.find((cut) => nodeKeys.has(rest.slice(0, cut)) && nodeKeys.has(rest.slice(cut + 1)));
    const cut = matched ?? cuts[0];
    return cut === undefined ? rest : `${rest.slice(0, cut)}>${rest.slice(cut + 1)}`;
  }

  /** 1 枚の SVG から、ノードと辺の材料を取り出す。同じ端点の辺は出てきた順の番号で分ける */
  function extractDiagram(root: SVGElement, flavor: DiagramFlavor): DiagramParts<DiagramPart> {
    const prefix = root.id;
    const nodeList: DiagramPart[] = [];
    const edges: { base: string; text: string; element: Element }[] = [];
    if (flavor === "sequence") {
      for (const participant of root.querySelectorAll('[data-et="participant"]')) {
        nodeList.push({ key: participant.getAttribute("data-id") ?? "", text: normalized(participant.textContent), element: participant });
      }
      // 参加者は上下 2 つ描かれる。生命線の x を、メッセージの端点の判定に使う
      const lifelines = [...root.querySelectorAll('[data-et="life-line"]')].map((line) => ({
        key: line.getAttribute("data-id") ?? "",
        x: Number(line.getAttribute("x1")),
      }));
      const nearestLifeline = (x: number): string =>
        lifelines.reduce((best, line) => (Math.abs(line.x - x) < Math.abs(best.x - x) ? line : best), lifelines[0] ?? { key: "?", x }).key;
      const texts = [...root.querySelectorAll("text.messageText")];
      root.querySelectorAll<SVGGeometryElement>('[data-et="message"]').forEach((line, position) => {
        const length = line.getTotalLength();
        const label = texts[position];
        // 色を付けるのはメッセージの文字（線は文字の直後の兄弟）
        if (label === undefined) return;
        edges.push({
          base: `${nearestLifeline(line.getPointAtLength(0).x)}>${nearestLifeline(line.getPointAtLength(length).x)}`,
          text: normalized(label.textContent),
          element: label,
        });
      });
    } else {
      for (const node of root.querySelectorAll<SVGGraphicsElement>("g.node")) {
        // 枠は端点を座標で決める stateDiagram-v2 だけが使う
        nodeList.push({ key: nodeKey(node, prefix), text: normalized(node.textContent), element: node, box: flavor === "state" ? boxOf(node) : undefined });
      }
      const nodeKeys = new Set(nodeList.map((node) => node.key));
      const labels = new Map<string, Element>();
      for (const label of root.querySelectorAll("g.label[data-id], g.edgeLabel [data-id]")) {
        labels.set(label.getAttribute("data-id") ?? "", label);
      }
      for (const path of root.querySelectorAll<SVGGeometryElement>('path[data-et="edge"]')) {
        const dataId = path.getAttribute("data-id") ?? "";
        const base =
          flavor === "state"
            ? // 遷移の id は並び順の番号だけのため、線の端の座標に一番近い状態を端点にする
              `${nearestKey(nodeList, path.getPointAtLength(0))}>${nearestKey(nodeList, path.getPointAtLength(path.getTotalLength()))}`
            : edgeEnds(dataId, nodeKeys);
        edges.push({ base, text: normalized(labels.get(dataId)?.textContent), element: path });
      }
    }
    const counts = new Map<string, number>();
    const keyedEdges = edges.map((edge) => {
      const number = counts.get(edge.base) ?? 0;
      counts.set(edge.base, number + 1);
      return { key: `${edge.base}#${number}`, text: edge.text, element: edge.element };
    });
    // 参加者のように同じ鍵が複数あるノードは、先に出たものにまとめる
    const nodes = new Map<string, DiagramPart>();
    for (const node of nodeList) if (!nodes.has(node.key)) nodes.set(node.key, node);
    return { nodes, edges: keyedEdges };
  }

  /** 辺の鍵 `{元}>{先}#{番号}` を、消したものの一覧に出す名前にする */
  function edgeName(edge: PreviousPart): string {
    const name = edge.name ?? edge.text;
    return name !== "" ? name : edge.key.replace(/#\d+$/, "").replace(">", " → ");
  }

  /** 前後の版で描いた SVG のノード・辺を鍵で突き合わせる。色を付けない種類と、突き合わせを打ち切ったときは null */
  export function diffDiagram(type: string, beforeSvg: SVGElement, afterSvg: SVGElement): DiagramDiff | null {
    const flavor = flavorOf(type);
    if (flavor === null) return null;
    return compareDiagrams({ flavor, previous: extractDiagram(beforeSvg, flavor), current: extractDiagram(afterSvg, flavor) });
  }

  /** 前後の版のノード・辺の材料を鍵で突き合わせて、足した・変えた・消したものに分ける。並びの突き合わせを打ち切ったときは null */
  function compareDiagrams({
    flavor,
    previous,
    current,
  }: {
    flavor: DiagramFlavor;
    previous: DiagramParts<PreviousPart>;
    current: DiagramParts<DiagramPart>;
  }): DiagramDiff | null {
    const result: DiagramDiff = { added: [], changed: [], removed: [] };
    for (const [key, node] of current.nodes) {
      const old = previous.nodes.get(key);
      if (old === undefined) result.added.push(node.element);
      else if (old.text !== node.text) result.changed.push(node.element);
    }
    for (const [key, node] of previous.nodes) {
      if (!current.nodes.has(key)) result.removed.push((node.name ?? node.text) !== "" ? (node.name ?? node.text) : key);
    }
    if (flavor === "sequence") {
      // メッセージは並び順で番号が振られるため、端点と文字の並びを行の差分と同じ要領で揃える
      const signature = (edge: { key: string; text: string }): string => `${edge.key.replace(/#\d+$/, "")}:${edge.text}`;
      const parts = Diff.diffArrays(previous.edges.map(signature), current.edges.map(signature), { timeout: ARRAY_DIFF_TIMEOUT_MS });
      // 並びの突き合わせを打ち切った
      if (parts === undefined) return null;
      let nowPosition = 0;
      parts.forEach((part, position) => {
        if (part.added) {
          const removedBefore = parts[position - 1];
          part.value.forEach((_, offset) => {
            const edge = current.edges[nowPosition + offset];
            if (edge === undefined) return;
            const paired = removedBefore?.removed === true && (removedBefore.value[offset] ?? "").split(":")[0] === edge.key.replace(/#\d+$/, "");
            (paired ? result.changed : result.added).push(edge.element);
          });
          nowPosition += part.count ?? part.value.length;
        } else if (part.removed) {
          const addedAfter = parts[position + 1];
          part.value.forEach((signed, offset) => {
            const paired = addedAfter?.added === true && (addedAfter.value[offset] ?? "").split(":")[0] === signed.split(":")[0];
            if (!paired) result.removed.push(signed.slice(signed.indexOf(":") + 1) || signed);
          });
        } else {
          nowPosition += part.count ?? part.value.length;
        }
      });
      return result;
    }
    const previousEdges = new Map(previous.edges.map((edge) => [edge.key, edge]));
    const currentKeys = new Set(current.edges.map((edge) => edge.key));
    for (const edge of current.edges) {
      const old = previousEdges.get(edge.key);
      if (old === undefined) result.added.push(edge.element);
      else if (old.text !== edge.text) result.changed.push(edge.element);
    }
    for (const edge of previous.edges) if (!currentKeys.has(edge.key)) result.removed.push(edgeName(edge));
    return result;
  }

  /** 解析した flowchart の db のうち、図の差分に使う形（`mermaidAPI` は mermaid の型定義で `@internal` のため、使う形だけを書く） */
  type ParsedFlowchart = {
    type: string;
    db: {
      getVertices: () => Map<string, { text?: string; labelType?: string }>;
      getEdges: () => { id: string; start: string; end: string; text?: string; labelType?: string }[];
    };
  };

  /** 解析した結果の種類（`Diagram.type`）のうち flowchart のもの */
  const PARSED_FLOWCHART_TYPES: readonly string[] = ["flowchart-v2", "flowchart-elk"];

  /** ラベルを画面に出る文字にそろえる（Markdown の記号と前後の `` ` ``・`<br>`・ほかのタグ・文字参照・`fa:fa-…` を外す） */
  function displayText({ text, labelType }: { text: string; labelType: string | undefined }): string {
    let shown = text;
    if (labelType === "markdown") {
      shown = shown
        .replace(/^`|`$/g, "")
        .replace(/(\*\*|__)(.+?)\1/g, "$2")
        .replace(/\*(.+?)\*/g, "$1")
        .replace(/(?<!\w)_(.+?)_(?!\w)/g, "$1");
    }
    shown = shown.replace(/<br\s*\/?>/gi, " ").replace(/<[^>]*>/g, "");
    // 文字参照（`&amp;` など）を戻す
    const decoder = document.createElement("textarea");
    decoder.innerHTML = shown;
    return normalized(decoder.value.replace(/\bfa[bsrl]?:fa-[\w-]+/g, ""));
  }

  /** 解析した結果から取り出したノードと辺。辺は SVG の辺の `data-id` と同じ値の `id` を持つ */
  type ParsedParts = { nodes: Map<string, PreviousPart>; edges: (PreviousPart & { id: string })[] };

  /** 記法を mermaid で解析して、flowchart のノードと辺の鍵・文字（と消したものに出す名前）を取り出す。flowchart でないときは null */
  async function parseFlowchart(source: string): Promise<ParsedParts | null> {
    const parser = mermaid as unknown as { mermaidAPI: { getDiagramFromText: (text: string) => Promise<ParsedFlowchart> } };
    const parsed = await parser.mermaidAPI.getDiagramFromText(source);
    if (!PARSED_FLOWCHART_TYPES.includes(parsed.type)) return null;
    const nodes = new Map<string, PreviousPart>();
    // SVG のノードの鍵は `flowchart-{id}`（`nodeKey` が描画の id と連番を外した残り）
    for (const [id, vertex] of parsed.db.getVertices()) {
      const text = vertex.text ?? id;
      nodes.set(`flowchart-${id}`, { key: `flowchart-${id}`, text: normalized(text), name: displayText({ text, labelType: vertex.labelType }) });
    }
    const counts = new Map<string, number>();
    const edges = parsed.db.getEdges().map((edge) => {
      // 辺の鍵は `flowchart-` を付けない `{始点}>{終点}` に、同じ端点の中の並びの番号を付ける
      const base = `${edge.start}>${edge.end}`;
      const number = counts.get(base) ?? 0;
      counts.set(base, number + 1);
      const text = edge.text ?? "";
      return { id: edge.id, key: `${base}#${number}`, text: normalized(text), name: displayText({ text, labelType: edge.labelType }) };
    });
    return { nodes, edges };
  }

  /** flowchart の図の差分を、前の版を SVG に描かず、前後の記法の解析で突き合わせる。flowchart でない種類と解析できなかったときは null */
  export async function diffDiagramFromSource(type: string, beforeSource: string, afterSource: string, afterSvg: SVGElement): Promise<DiagramDiff | null> {
    if (flavorOf(type) !== "flowchart") return null;
    let previous: ParsedParts | null;
    let parsedNow: ParsedParts | null;
    try {
      previous = await parseFlowchart(beforeSource);
      parsedNow = await parseFlowchart(afterSource);
    } catch {
      // 解析できない記法（書きかけ）と、版を上げて形が変わった `mermaidAPI`: 前の版を描いて突き合わせる側へ倒す
      return null;
    }
    if (previous === null || parsedNow === null) return null;
    // 色を付ける要素だけ今の版の SVG から引き、文字は前後とも解析した結果で比べる
    const drawn = extractDiagram(afterSvg, "flowchart");
    const nodes = new Map<string, DiagramPart>();
    for (const [key, node] of drawn.nodes) nodes.set(key, { ...node, text: parsedNow.nodes.get(key)?.text ?? node.text });
    // 辺は SVG の `data-id` を解析した辺の `id` と突き合わせ、解析した辺の鍵で引く（`edgeEnds` で `data-id` を切ると、id に `_` を含むノードや id を付けた辺で前後の鍵がずれる）
    const parsedEdges = new Map(parsedNow.edges.map((edge) => [edge.id, edge]));
    const edges: DiagramPart[] = [];
    for (const edge of drawn.edges) {
      const parsedEdge = parsedEdges.get(edge.element.getAttribute("data-id") ?? "");
      // 解析した結果に無い辺: 版を上げて `data-id` の作り方が変わった
      if (parsedEdge === undefined) return null;
      edges.push({ ...edge, key: parsedEdge.key, text: parsedEdge.text });
    }
    return compareDiagrams({ flavor: "flowchart", previous, current: { nodes, edges } });
  }

  /** 本文の中の並びの順で対にした、選んだ時点と今の埋め込んだ HTML の範囲の中身 */
  export type EmbeddedHtmlPair = {
    /** 今の本文の中で何番目の範囲か（0 始まり。描いた本文の n 番目の `.mdmark-html` に当たる） */
    order: number;
    /** 選んだ時点の範囲の中身（`<!-- html -->` と `<!-- /html -->` の行を除いた行） */
    before: string;
    /** 今の範囲の中身（同上） */
    after: string;
  };

  /** 範囲の印の行（1 始まり）の間にある行を、改行でつないだ文字列にする */
  function embeddedHtmlContent({ lines, open, close }: { lines: string[]; open: number; close: number }): string {
    return lines.slice(open, close - 1).join("\n");
  }

  /** 前後の Markdown の本文の埋め込んだ HTML の範囲を並びの順で対にし、中身が違う対だけを返す。選んだ時点に対になる範囲が無い今の範囲は入れない */
  export function pairEmbeddedHtml({ before, after }: { before: string; after: string }): EmbeddedHtmlPair[] {
    const beforeLines = before.split("\n");
    const afterLines = after.split("\n");
    const beforeRanges = embeddedHtmlRanges(before);
    const pairs: EmbeddedHtmlPair[] = [];
    embeddedHtmlRanges(after).forEach((range, order) => {
      const previous = beforeRanges[order];
      if (previous === undefined) return;
      const pair = {
        order,
        before: embeddedHtmlContent({ lines: beforeLines, ...previous }),
        after: embeddedHtmlContent({ lines: afterLines, ...range }),
      };
      if (pair.before !== pair.after) pairs.push(pair);
    });
    return pairs;
  }

  /** 描いた前後の範囲の直下の要素（`outerHTML`）を並びで比べ、今の要素ごとに足した・変わったのマーカーを返す。変えていない要素は null。比べるのを打ち切ったら null */
  export function childMarks({ before, after }: { before: string[]; after: string[] }): ("added" | "changed" | null)[] | null {
    const parts = Diff.diffArrays(before, after, { timeout: ARRAY_DIFF_TIMEOUT_MS });
    // 打ち切り
    if (parts === undefined) return null;
    const marks: ("added" | "changed" | null)[] = [];
    // 直前の消した並びのうち、足した要素と対にできる残りの数
    let removedLeft = 0;
    for (const part of parts) {
      if (part.removed) {
        removedLeft = part.count ?? part.value.length;
      } else if (part.added) {
        // 消した並びに続く足した並びは、前から 1 つずつ消した要素と対にして変わった、対にならない残りを足したにする
        for (let position = 0; position < (part.count ?? part.value.length); position += 1) {
          marks.push(removedLeft > 0 ? "changed" : "added");
          removedLeft = Math.max(0, removedLeft - 1);
        }
      } else {
        removedLeft = 0;
        for (let position = 0; position < (part.count ?? part.value.length); position += 1) marks.push(null);
      }
    }
    return marks;
  }
}
