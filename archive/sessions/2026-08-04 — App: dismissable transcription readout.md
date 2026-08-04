# 2026-08-04 — App: dismissable transcription readout

Short single-feature session. One file touched: [static/index.html](../../static/index.html).

---

## The request

The app displays the Whisper transcription, but on longer messages it overwhelms the screen.
It should stay visible but gain a close button or a timeout so the app remains usable.

---

## What was found

- `#transcript` was a bare div in the `<footer>`, above the mic controls
  ([index.html:429](../../static/index.html#L429)).
- It carried `min-height: 18px` — so it reserved footer space permanently, even when empty.
- No height cap. A long dictation grew the footer until it pushed `#conversation` off screen.
- It was only ever cleared by starting a *new* recording
  (`transcript.textContent = ''` at the top of `startRecording`). No other way to dismiss it.
- The same text is already added to the conversation as a user bubble — `sendToServer()` →
  `addMessage('user', input)`. The footer readout is a *pre-send* confirmation of what Whisper
  heard, not the only copy of the words.

---

## What was built

| # | Change | Location |
|---|---|---|
| 1 | Wrapped the div in `#transcript-wrap` — text + a `✕` dismiss button | [index.html:429-432](../../static/index.html#L429-L432) |
| 2 | Hidden entirely when empty (`display:none`, was `min-height:18px`); text capped at `max-height: 4.5em` with `overflow-y: auto`; card background + border; left-aligned | [index.html:99-138](../../static/index.html#L99-L138) |
| 3 | `showTranscript()` / `hideTranscript()` replace the direct `textContent` writes; auto-hide at `TRANSCRIPT_TIMEOUT_MS = 12000`; timer cleared by `✕` and by starting a new recording | [index.html:588-609](../../static/index.html#L588-L609) |

Both call sites updated: `startRecording` now calls `hideTranscript()`, and the `/transcribe`
success path calls `showTranscript(text)`.

---

## Decisions

1. **Both the close button and the timeout**, though the request offered them as alternatives.
   The timeout clears the screen with no action; the `✕` handles "12s is too long." No conflict
   between them.
2. **Rejected — removing the readout entirely.** It duplicates the user bubble, but it is the
   only *pre-send* check that Whisper heard correctly, and the user asked for it to stay
   visible. That duplication is what makes auto-hide safe, though: nothing is lost when it goes.
3. **Rejected — ellipsis truncation.** Scroll-inside-a-cap keeps the full text readable, which
   is the point of a transcription check.
4. **Left-aligned, was centred.** Centred italic reads fine at one line and badly at three; the
   height cap makes ~3 lines the normal long-dictation case.
5. **12 seconds** as the timeout, in a named constant so it is one edit to tune.

---

## Deployment

- `./deploy.sh` — required (`static/` is served by the VM).
- **APK rebuild — required.** This changes UI *structure*, one of the named rebuild triggers in
  `CLAUDE.md`; pure server-side changes are not. `SESSION.md` already carried a pending rebuild
  for the password-reveal toggle, so the two ship in one build.

Neither was done this session.

---

## Deferred / not done

- **Not tested.** No server was started; the change is reasoned from the code, not observed
  running. Filed in `DEV_BACKLOG.md`.
- Test procedure: start the server, dictate 30+ seconds of speech.
  **Pass** — readout appears in a bordered box no taller than ~3 lines, scrolls internally, mic
  and text field do not move, disappears after 12s or on `✕`, footer height unchanged when no
  transcript is showing. **Fail** — footer grows, or the box outlives 12s.
