// 開いた画面の URL のパスから、配っているワークスペースのパスの頭と、端末の保存領域のキーを求める

/** パスの先頭の `/w/{workspace}`（`{workspace}` は `/` を含まない 1 つ以上の文字） */
export const WORKSPACE_PATH_PATTERN = /^\/w\/([^/]+)/;

/** パスの先頭の `/w/{workspace}`（パーセントエンコードのまま）。該当しなければ空文字 */
export const workspacePath = (pathname: string = location.pathname): string => WORKSPACE_PATH_PATTERN.exec(pathname)?.[0] ?? "";

/** サーバーの配信では `{key}:{ワークスペースの ID}`、該当しなければ key のまま */
export const workspaceKey = (key: string, pathname: string = location.pathname): string => {
  const encoded = WORKSPACE_PATH_PATTERN.exec(pathname)?.[1];
  return encoded === undefined ? key : `${key}:${decodeURIComponent(encoded)}`;
};

/** サーバーの配信ではワークスペースの ID、該当しなければ空文字 */
export const workspaceIdOf = (pathname: string = location.pathname): string => {
  const encoded = WORKSPACE_PATH_PATTERN.exec(pathname)?.[1];
  return encoded === undefined ? "" : decodeURIComponent(encoded);
};
