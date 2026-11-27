// 直前の操作が指で押したものかを、文書の pointerdown・pointerover・keydown から保持する

/** 直前の入力の種類（`pointerType` の値か `keyboard`）。まだ何も操作していなければ null */
let lastInput: string | null = null;

const rememberPointer = (event: Event): void => {
  lastInput = (event as PointerEvent).pointerType;
};

document.addEventListener("pointerdown", rememberPointer, true);
document.addEventListener("pointerover", rememberPointer, true);
document.addEventListener(
  "keydown",
  () => {
    lastInput = "keyboard";
  },
  true,
);

/** 直前の操作が指で押したものか（指で押した後の互換の mouseover・focus・click から呼んで判定する） */
export const isTouchInput = (): boolean => lastInput === "touch";
