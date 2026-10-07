// ロック。注目の起点を 1 つの項目に留める。押下の判定・2 回押しの読み替え・鍵の震えの量は、ネットワークと検討事項のマップで共通。

namespace MindmapPreview {
  /** 2 回押しとみなす間隔（ms）。前に押してからこの時間未満に押した 2 回目を、前に押した項目への 2 回押しとみなす */
  export const DOUBLE_TAP_MS = 450;

  /** 2 回押しとみなす位置のずれ（px）。前に押した位置からの距離がこの値未満の 2 回目を 2 回押しとみなす */
  export const DOUBLE_TAP_PX = 24;

  /** 鍵が震え始めてから収まるまでの時間（ms） */
  export const SHAKE_MS = 1000;

  /** 震えの往復の回数 */
  const SHAKE_WAVES = 5;

  /** 鍵の左右の振れ幅（px） */
  export const SHAKE_SHIFT = 6;

  /** 鍵が上を軸に傾く角度（rad） */
  export const SHAKE_SWING = 0.45;

  /** 震え始めに鍵を大きくする割合 */
  export const SHAKE_GROW = 0.45;

  /** 赤い光のにじみの半径（px） */
  const SHAKE_GLOW = 4;

  /** ロックの判定をする幅（幅 900px 以下では詳細が全面に出るため、ネットワークも検討事項のマップもロックしない） */
  export const LOCK_QUERY = "(min-width: 901px)";

  /** 要素が文字を入力する欄か（`input`・`textarea`・`select`・編集できる要素。`L` キーを受けない判定に使う） */
  export function isTyping(element: Element | null): boolean {
    return element instanceof HTMLElement && (element.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName));
  }

  /** 押したときにすること（`lock`: ロックする / `unlock`: ロックを外す / `open`: 詳細を切り替える / `shake`: 鍵を震わせる / `blank`: 全体の表示へ戻す） */
  export type LockAction = "lock" | "unlock" | "open" | "shake" | "blank";

  /** 押した時刻（`performance.now()`）・位置（画面の px）・押した位置の項目（余白は `null`） */
  export type Press = { time: number; x: number; y: number; id: string | null };

  /** 押した項目・詳細を開いている項目・ロックしている項目から、すること（と押した後のロック）を返す。余白を押したときは `pressed` が `null`。`L` キーは `pressed` に詳細を開いている項目を渡す */
  export function lockTap({
    locked,
    pressed,
    open,
  }: {
    /** ロックしている項目 */
    locked: string | null;
    /** 押した項目（`resolvePress` で読み替えた後） */
    pressed: string | null;
    /** 詳細パネルで開いている項目 */
    open: string | null;
  }): { action: LockAction; locked: string | null } {
    if (locked !== null) {
      if (pressed === locked) {
        // ロックした項目は、詳細を開いている状態でもう一度押したときだけ外す。開いていなければ詳細を戻すだけ
        return open === pressed ? { action: "unlock", locked: null } : { action: "open", locked };
      }
      // 詳細を開いている別の項目をもう一度押した・余白を押したときは、ロック・詳細・表示を変えずに知らせる
      return { action: pressed === null || pressed === open ? "shake" : "open", locked };
    }
    if (pressed === null) return { action: "blank", locked: null };
    // ロックしていないとき: 詳細を開いている項目をもう一度押したらロックする
    return pressed === open ? { action: "lock", locked: pressed } : { action: "open", locked: null };
  }

  /** 今の押下が前の押下から `DOUBLE_TAP_MS` 未満かつ `DOUBLE_TAP_PX` 未満の位置なら、前に押した項目を押したものとして返す（詳細が開いて枠がずれても 2 回押しにする）。それ以外は今押した項目を返す */
  export function resolvePress({ last, press }: { last: Press | null; press: Press }): string | null {
    if (last === null) return press.id;
    const second =
      press.time - last.time < DOUBLE_TAP_MS && Math.hypot(press.x - last.x, press.y - last.y) < DOUBLE_TAP_PX;
    return second ? last.id : press.id;
  }

  /** 震え始めてからの時間（ms）から、収まり具合 `decay`（1 → 0）と振れ `wave`（-1〜1）を返す */
  export function shakeAt(elapsed: number): { decay: number; wave: number } {
    return { decay: 1 - elapsed / SHAKE_MS, wave: Math.sin((elapsed / SHAKE_MS) * Math.PI * 2 * SHAKE_WAVES) };
  }

  /** 震える鍵の赤（ライトは `--red-700`、ダークは `--red-300`） */
  export function shakeColor(): string {
    const dark = document.documentElement.dataset["theme"] === "dark";
    return getComputedStyle(document.documentElement).getPropertyValue(dark ? "--red-300" : "--red-700").trim();
  }

  /** 震え始めた時刻（要素の鍵の震えが共有する。描き直しで鍵の要素が作り直されても続きから震わせる） */
  let elementShakeStart = Number.NEGATIVE_INFINITY;

  /** 要素の鍵を震わせる。毎コマ `find` が返す今の鍵へ `shakeAt` の量を当て、`SHAKE_MS` を過ぎたら外す。CSS のアニメーションを使わないので `prefers-reduced-motion` でも止まらない */
  export function shakeKeyElement(find: () => HTMLElement | null): void {
    const running = performance.now() - elementShakeStart < SHAKE_MS;
    elementShakeStart = performance.now();
    // 震えている間に呼ばれたら、始まりを今にして続きから震わせる（毎コマの処理は 1 つだけにする）
    if (running) return;
    const step = (now: number): void => {
      const key = find();
      const elapsed = Math.max(0, now - elementShakeStart);
      if (elapsed >= SHAKE_MS) {
        key?.removeAttribute("style");
        return;
      }
      if (key !== null) {
        const { decay, wave } = shakeAt(elapsed);
        // 南京錠のように上を軸に振れ、大きくなって赤く光り、だんだん収まる
        key.style.cssText = `transform-origin: 50% 0; transform: translateX(${wave * SHAKE_SHIFT * decay}px) rotate(${wave * SHAKE_SWING * decay}rad) scale(${1 + SHAKE_GROW * decay}); color: ${shakeColor()}; filter: drop-shadow(0 0 ${SHAKE_GLOW * decay}px ${shakeColor()})`;
      }
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}
