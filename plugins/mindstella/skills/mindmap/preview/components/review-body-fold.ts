// レビュー中の書き込みの本文の折りたたみ。折り返した後の見た目の行で一定の行数までに本文を畳み、超えるときだけ開閉のボタンを出す。本文の要素と開閉のボタンを別々に返し、ボタンの置き場所は使う側が決める。

namespace MindmapPreview {
  /** 畳んだときに出す、折り返した後の見た目の行の数 */
  export const REVIEW_FOLD_LINES = 5;

  /** 本文の折りたたみの引数 */
  export type ReviewBodyFoldProps = {
    /** レビュー中の書き込みの ID（本文の `id` と開閉のボタンの `data-focus` に使う） */
    id: string;
    /** 行の読み上げの名前の頭（開閉のボタンの読み上げの名前に使う） */
    label: string;
    /** 書き込みの本文 */
    body: string;
    /** まとまりの説明（記録に無ければ null） */
    changeSets?: (id: string) => string | null;
    /** 本文を開いているか */
    open?: boolean;
    /** 畳んだときに出す行の数 */
    lines?: number;
    on: {
      /** 開閉した（書き込みの ID と、開いたか） */
      toggle: (id: string, open: boolean) => void;
      /** 本文の中のまとまりのリンクを押した（まとまりの ID） */
      changeSet: (id: string) => void;
    };
  };

  /** 本文の要素と開閉のボタン */
  export type ReviewBodyFold = { body: HTMLElement; more: HTMLButtonElement };

  /** 全文の高さが、行の高さ × 行数を超えたとみなす余裕（小数の丸め） */
  const FOLD_TOLERANCE_PX = 1;

  /** 開閉のボタンの文言・矢印・読み上げの名前を、開いているかに合わせる */
  function setToggle({ more, open, label }: { more: HTMLButtonElement; open: boolean; label: string }): void {
    more.setAttribute("aria-expanded", String(open));
    more.setAttribute("aria-label", open ? `${label}の本文を折りたたむ` : `${label}の続きを読む`);
    more.replaceChildren(icon("chev"), h({ tag: "span", children: [open ? "折りたたむ" : "続きを読む"] }));
  }

  /** 全文が畳む行の数を超えるか */
  function exceedsLines({ body, lines }: { body: HTMLElement; lines: number }): boolean {
    const lineHeight = parseFloat(getComputedStyle(body).lineHeight);
    // 畳んでいても scrollHeight は全文の高さを返す
    return body.scrollHeight > lineHeight * lines + FOLD_TOLERANCE_PX;
  }

  /** 本文を畳み、開閉のボタンを添えて返す */
  export function reviewBodyFold({ id, label, body, changeSets = () => null, open = false, lines = REVIEW_FOLD_LINES, on }: ReviewBodyFoldProps): ReviewBodyFold {
    const bodyId = `review-body-${id}`;
    const text = postBody({
      body,
      titles: () => null,
      changeSets,
      className: "review-body",
      // 項目の ID は文字のまま出すので、押されることは無い
      on: { openId: () => undefined, changeSet: on.changeSet },
    });
    text.id = bodyId;
    text.style.setProperty("--fold-lines", String(lines));

    let opened = open;
    const more = h({
      tag: "button",
      attrs: {
        class: "btn ghost review-more",
        type: "button",
        // 測るまでは出さない
        hidden: true,
        "aria-controls": bodyId,
        "data-focus": `more:${id}`,
        onclick: () => {
          opened = !opened;
          text.classList.toggle("folded", !opened);
          setToggle({ more, open: opened, label });
          // 折りたたんだ行が画面から外れないように寄せる
          if (!opened) text.closest("li")?.scrollIntoView({ block: "nearest" });
          on.toggle(id, opened);
        },
      },
    }) as HTMLButtonElement;
    setToggle({ more, open: opened, label });

    // 描いた直後と本文の幅が変わったとき（折り返しが変わる）に測り、超えるときだけ畳んで開閉のボタンを出す
    new ResizeObserver(() => {
      const exceeds = exceedsLines({ body: text, lines });
      text.classList.toggle("folded", exceeds && !opened);
      more.hidden = !exceeds;
    }).observe(text);
    return { body: text, more };
  }
}
