// fetch を呼ぶ場所を 1 か所にする mutator
export const apiClient = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`HTTP ${String(response.status)}: ${url}`);
  }
  const data: unknown = await response.json();
  return { data, status: response.status, headers: response.headers } as T;
};
