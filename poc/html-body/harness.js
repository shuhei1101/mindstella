// PoC: 親の画面が sandbox の iframe に HTML の本文を描き、選択・位置・高さを読む仕掛け
"use strict";

const LINE_ATTR = "data-line";

// 受け手が呼ばれた回数
window.__events = { pointerup: 0, selectionchange: 0 };

/** 改行の数を返す */
function countNewlines(text) {
  return text.split("\n").length - 1;
}

/** 選択の端から、行の印を持つ最も近い要素を返す */
function lineBlock(node) {
  const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
  return element ? element.closest(`[${LINE_ATTR}]`) : null;
}

/** 印を持つ要素の先頭から選択の端までの改行（文とコメントの中の改行）の数を返す */
function linesBefore(block, node, offset) {
  const doc = block.ownerDocument;
  const range = doc.createRange();
  range.setStart(block, 0);
  range.setEnd(node, offset);
  const fragment = range.cloneContents();
  let count = countNewlines(fragment.textContent || "");
  // コメントは textContent に入らないので、中の改行を足す
  const walker = doc.createTreeWalker(fragment, NodeFilter.SHOW_COMMENT);
  while (walker.nextNode()) count += countNewlines(walker.currentNode.data);
  return count;
}

/** iframe の中の選択を、原文の行の範囲の箇所にする */
function locate(frame) {
  const selection = frame.contentWindow.getSelection();
  if (!selection || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  const text = range.toString().trim();
  if (range.collapsed || text === "") return null;
  const startBlock = lineBlock(range.startContainer);
  const endBlock = lineBlock(range.endContainer);
  if (!startBlock || !endBlock) return null;
  return {
    start: Number(startBlock.getAttribute(LINE_ATTR)) + linesBefore(startBlock, range.startContainer, range.startOffset),
    end: Number(endBlock.getAttribute(LINE_ATTR)) + linesBefore(endBlock, range.endContainer, range.endOffset),
    text,
  };
}

/** 選択の最初の矩形を、親の画面の座標にして返す */
function selectionRect(frame) {
  const range = frame.contentWindow.getSelection().getRangeAt(0);
  const inner = range.getClientRects()[0];
  const outer = frame.getBoundingClientRect();
  return { left: outer.left + frame.clientLeft + inner.left, top: outer.top + frame.clientTop + inner.top };
}

/** iframe の高さを中身に合わせる */
function fitHeight(frame) {
  const doc = frame.contentDocument;
  frame.style.height = `${doc.documentElement.scrollHeight}px`;
}

/** 本文を描いた iframe を holder に置き、読み込み後に受け手と高さの合わせを付ける */
function mount(holder, html) {
  return new Promise((resolve) => {
    const frame = document.createElement("iframe");
    frame.setAttribute("sandbox", "allow-same-origin");
    frame.style.width = "100%";
    frame.style.border = "0";
    frame.addEventListener("load", () => {
      const doc = frame.contentDocument;
      doc.addEventListener("pointerup", () => { window.__events.pointerup += 1; });
      doc.addEventListener("selectionchange", () => { window.__events.selectionchange += 1; });
      new ResizeObserver(() => fitHeight(frame)).observe(doc.documentElement);
      fitHeight(frame);
      resolve(frame);
    });
    frame.srcdoc = html;
    holder.append(frame);
  });
}

window.poc = { mount, locate, selectionRect, fitHeight };
