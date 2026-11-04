// 失敗した応答から作るエラー。`detail` を画面に出す

/** RFC 9457 の problem+json の本文 */
type Problem = { type: string; title: string; status: number; detail: string };

/** 本文が problem+json の形か */
const isProblem = (data: unknown): data is Problem =>
  typeof data === "object" &&
  data !== null &&
  typeof (data as Partial<Problem>).type === "string" &&
  typeof (data as Partial<Problem>).detail === "string";

export class AppError extends Error {
  /** HTTP のステータス */
  readonly statusCode: number;
  /** problem+json の `type` の値（problem+json でない本文は空） */
  readonly code: string;

  constructor({ message, statusCode, code }: { message: string; statusCode: number; code: string }) {
    super(message);
    this.name = "AppError";
    this.statusCode = statusCode;
    this.code = code;
  }

  /** problem+json の本文とステータスから作る。problem+json でない本文はステータスの文言にする */
  static fromResponse(data: unknown, statusCode: number): AppError {
    if (isProblem(data)) {
      return new AppError({ message: data.detail, statusCode, code: data.type });
    }
    return new AppError({ message: `HTTP ${String(statusCode)}`, statusCode, code: "" });
  }
}
