// orval の mutator。fetch を呼ぶ場所を 1 か所にし、失敗を AppError にする
import { AppError } from "@/shared/core/app-error";
import { embeddedResponse, isEmbedded } from "@/shared/core/embedded";
import { workspacePath } from "@/shared/core/workspace-path";

/** 本文を JSON として読む。JSON でなければ null */
const readJson = async (response: Response): Promise<unknown> => {
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
};

/** 開いた画面のワークスペースのパスの頭を付けて fetch で呼び、成功は本文と status と headers を返し、2xx でなければ AppError を投げる。配る書き出しは埋め込みから応答を作り fetch を呼ばない */
export const apiClient = async <T>(url: string, options?: RequestInit): Promise<T> => {
  if (isEmbedded()) {
    const embedded = embeddedResponse({ url, method: options?.method ?? "GET" });
    if (embedded === null) throw new AppError({ message: "配る書き出しでは使えません", statusCode: 404, code: "" });
    return embedded as T;
  }
  const response = await fetch(`${workspacePath()}${url}`, options);
  const data = await readJson(response);
  if (!response.ok) {
    throw AppError.fromResponse(data, response.status);
  }
  return { data, status: response.status, headers: response.headers } as T;
};
