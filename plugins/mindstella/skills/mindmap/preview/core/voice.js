"use strict";
// コメント・返信の入力の録音（マイクを使えるか・録音の開始と止め方）・カーソルの位置への挿入・文字起こしの結果の組み立て。
var MindmapPreview;
(function (MindmapPreview) {
    /** `MediaRecorder.isTypeSupported` が真の最初の形で録る（どれも偽ならブラウザの既定） */
    MindmapPreview.VOICE_MIME_TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"];
    /** サーバーが返さない理由の文 */
    MindmapPreview.VOICE_TEXT = {
        noMicrophone: "このページではマイクを使用できません。HTTPS か localhost の URL で開いてください。",
        denied: "マイクを使用できませんでした。ブラウザの設定でこのページのマイクを許可してください。",
        failed: "文字起こしできませんでした。もう一度お試しください。",
        sendFailed: "送信できませんでした。文字起こしの結果は入力欄に残しています。",
    };
    /** ブラウザが getUserMedia と MediaRecorder を持つかを返す（HTTPS でも localhost でもない経路では持たない） */
    function micSupported(win = window) {
        return typeof win.navigator.mediaDevices?.getUserMedia === "function" && typeof win.MediaRecorder === "function";
    }
    MindmapPreview.micSupported = micSupported;
    /** マイクの許可を得て録音を始め、録音を返す。許可が得られなければ理由で断る */
    async function startRecording(win = window) {
        const getUserMedia = win.navigator.mediaDevices?.getUserMedia;
        const Recorder = win.MediaRecorder;
        if (getUserMedia === undefined || Recorder === undefined)
            throw "no-microphone";
        let stream;
        try {
            stream = await getUserMedia.call(win.navigator.mediaDevices, { audio: true });
        }
        catch (error) {
            // 許可を拒否した: 許可が要る旨を出す。それ以外（マイクが無いなど）は使えない旨を出す
            const name = error instanceof DOMException ? error.name : "";
            throw (name === "NotAllowedError" || name === "SecurityError" ? "denied" : "no-microphone");
        }
        const mimeType = MindmapPreview.VOICE_MIME_TYPES.find((type) => Recorder.isTypeSupported(type));
        const recorder = new Recorder(stream, mimeType === undefined ? undefined : { mimeType });
        const chunks = [];
        let keep = true;
        recorder.addEventListener("dataavailable", (event) => {
            if (keep)
                chunks.push(event.data);
        });
        const release = () => {
            for (const track of stream.getTracks())
                track.stop();
        };
        recorder.start();
        return {
            stop: () => new Promise((resolve) => {
                recorder.addEventListener("stop", () => {
                    release();
                    resolve(new Blob(chunks, { type: recorder.mimeType }));
                });
                recorder.stop();
            }),
            cancel: () => {
                keep = false;
                recorder.stop();
                release();
            },
        };
    }
    MindmapPreview.startRecording = startRecording;
    /** 入力欄の中身の選んだ範囲を文字で置き換え、置き換えた後の中身と、挿入した文字の後ろの位置を返す */
    function insertAtCursor(value, start, end, text) {
        // 範囲を超える位置は末尾にそろえる
        const from = Math.min(start, value.length);
        const to = Math.min(Math.max(end, from), value.length);
        return { value: `${value.slice(0, from)}${text}${value.slice(to)}`, caret: from + text.length };
    }
    MindmapPreview.insertAtCursor = insertAtCursor;
    /** 録音を始めてからの秒数を `m:ss` にする */
    function formatElapsed(seconds) {
        const minutes = Math.floor(seconds / 60);
        const rest = Math.floor(seconds % 60);
        return `${minutes}:${String(rest).padStart(2, "0")}`;
    }
    MindmapPreview.formatElapsed = formatElapsed;
    /** 録音を止めて文字起こしし、結果を入力欄の中身のカーソルの位置へ挿入して、挙動が send なら全文をすぐ送る */
    async function finishVoice(recording, input, api = MindmapPreview.voiceApi()) {
        const kept = { body: input.body, caret: null, entered: false, reason: null };
        const audio = await recording.stop();
        const result = await api.transcribe(audio);
        if (!result.ok) {
            // サービスが使えない: マイクのボタンを押せなくする
            if (result.status === 503) {
                return { ...kept, kind: "unavailable", detail: result.detail, reason: result.reason ?? "stopped" };
            }
            // 断られた・届かない: 入力欄の中身を残す
            return { ...kept, kind: "failed", detail: result.status === null ? MindmapPreview.VOICE_TEXT.failed : (result.detail ?? MindmapPreview.VOICE_TEXT.failed) };
        }
        const text = result.data?.text ?? "";
        // 話し声が無かった: 送信も挿入もしない
        if (text.trim() === "")
            return { ...kept, kind: "failed", detail: MindmapPreview.VOICE_TEXT.failed };
        const inserted = insertAtCursor(input.body, input.start, input.end, text);
        if (input.action === "insert") {
            return { kind: "inserted", body: inserted.value, caret: inserted.caret, entered: false, detail: null, reason: null };
        }
        const sent = await api.sendNow({ ...input.destination, body: inserted.value });
        if (!sent.ok) {
            return { kind: "failed", body: inserted.value, caret: inserted.caret, entered: false, detail: MindmapPreview.VOICE_TEXT.sendFailed, reason: null };
        }
        return { kind: "sent", body: "", caret: null, entered: sent.data?.entered ?? false, detail: null, reason: null };
    }
    MindmapPreview.finishVoice = finishVoice;
})(MindmapPreview || (MindmapPreview = {}));
