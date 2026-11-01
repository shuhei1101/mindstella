// ストーリーの画面の設定。ストーリーを描く前に mdmark を読み終える。

/** @type {import("@storybook/html-vite").Preview} */
const preview = {
  loaders: [
    async () => {
      // 雛形の import map を head に差し込んであるので、プレビューの起動と同じ読み方で読める
      await MindmapPreview.loadMdmark();
    },
  ],
};

export default preview;
