// 切り替えボタン（表示形式の切り替え・スレッドの状態の絞り込み・詳細の本文の切り替え）が共有する見た目のクラス

/** ボタンを 1 つの枠線と `--muted` の面の中につなげて並べる組 */
export const SEGMENTED_GROUP_CLASS = "inline-flex rounded-control border border-border bg-muted p-0.5";

/** 選んでいないボタン。高さ・幅は使う側が加える */
export const SEGMENTED_ITEM_CLASS = "cursor-pointer rounded-sm text-small text-muted-foreground hover:bg-card hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring";

/** 選んだボタンにだけ加える */
export const SEGMENTED_SELECTED_CLASS = "bg-tab-selected font-medium text-foreground ring-1 ring-inset ring-mark/50 hover:bg-tab-selected";
