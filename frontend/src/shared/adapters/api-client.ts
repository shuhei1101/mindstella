// orval の mutator。fetch を呼ぶ場所を 1 か所にし、失敗を AppError にする
import { AppError } from "@/shared/core/app-error";

/** 本文を JSON として読む。JSON でなければ null */
const readJson = async (response: Response): Promise<unknown> => {
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
};

/** fetch で呼び、成功は本文と status と headers を返し、2xx でなければ AppError を投げる */
export const apiClient = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(url, options);
  const data = await readJson(response);
  if (!response.ok) {
    throw AppError.fromResponse(data, response.status);
  }
  return { data, status: response.status, headers: response.headers } as T;
};
