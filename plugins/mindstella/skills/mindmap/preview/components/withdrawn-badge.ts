// 取り下げの札。取り下げた調査・資料・用語集・メモ・会話ログのタイトルの右に、差分の表示によらず置く。検討事項の状態「取り下げ」と同じ × の印と文言に枠を付け、状態の札（枠なし）と見分ける。

namespace MindmapPreview {
  /** 取り下げの札の引数 */
  export type WithdrawnBadgeProps = {
    /** 真のとき、詳細パネルの題の大きさに合わせて札を一回り大きくする */
    large?: boolean;
  };

  /** 取り下げの札。× の印は読み上げに出さず、「取り下げ」の文字で伝える */
  export function withdrawnBadge({ large = false }: WithdrawnBadgeProps = {}): HTMLElement {
    return h({
      tag: "span",
      attrs: { class: large ? "wd-badge wd-large" : "wd-badge" },
      children: [statusMark("取り下げ"), "取り下げ"],
    });
  }
}
