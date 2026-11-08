# display-settings

`frontend/src/features/settings/display-settings/` の React のプレビューのモジュール

## 目次

| ページ | 概要 |
| --- | --- |
| [components](./components/) | `frontend/src/features/settings/display-settings/components/` の React のプレビューのモジュール |
| [display-settings-panel.tsx](./display-settings-panel.tsx.yaml) | 画面設計『表示の設定.tsx』の要素と操作を描く。上書きを端末の保存領域に書き、既定にするで確かめのモーダルを開く |
| [settings-confirm-dialog.tsx](./settings-confirm-dialog.tsx.yaml) | 画面設計『既定の保存の確かめ.tsx』の要素と操作を描く。shadcn/ui の Dialog に部品『既定の保存の確かめ』を置き、`open`・`onOpenChange` は親が持つ |
| [use-save-display-default.ts](./use-save-display-default.ts.yaml) | ワークスペースの既定の書き換えの mutation |
