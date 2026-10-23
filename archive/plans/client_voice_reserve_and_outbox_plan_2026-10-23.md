# Metatron App + Webapp — dated timestamps, a voice reserve, and messages that survive a dropped connection

*Plan, 2026-10-23. **Approved and built the same day.** Mike's rulings: headset recordings never
wait in the tray — one that cannot be transcribed yet is kept and still sends itself, and they
are exempt from the 15-minute rule, stamped with when they were said if they go late; snippets are
stamped with when they were RECORDED; decisions 1 and 3 as recommended. Changes made during build,
from the Fable review: frames are keyed to the current exchange only; nothing is sent before a
socket signs in; a recording stuck on a server error is retried by timer, five times at most, then
waits for a tap.*

**Model: Opus 5.5 to build; Fable 5.1 to review the reconnect and outbox logic.** The split pays
for itself here: this file's WebSocket code has produced four live race bugs (doubled text, lost
replies, a reply spoken an hour late), and every one read correctly in review before it ran.

Both surfaces are one file. The App is a Capacitor wrapper whose `webDir` is `static/`, so
[static/index.html](../../static/index.html) is the App *and* the Webapp. The Webapp updates on
deploy. The App updates only when the APK is rebuilt and sideloaded.

---

## What changes for Mike

1. **Every message shows its date as well as its time**, e.g. *Fri 23 Oct, 15:41*. It follows the
   phone's locale, as the time already does. The year appears only on messages from a previous
   year.
2. **The on-screen mic no longer sends on its own.** Each recording becomes a snippet in a tray
   above the text box. A snippet shows what was heard and has a ✕ to delete it. Record as many as
   you like, add typed text or photos, then press Send once.
   - Several snippets go as **one message, one paragraph per snippet, each stamped with the time it
     was recorded**. That is the 10-15 ask: *"distinct by entry/time … but batch submitted"*. A
     single snippet goes exactly as it does today, with no stamp.
   - You can record the next snippet while the last one is still being transcribed.
   - The tray survives closing the app. You can capture through the day and send in the evening.
3. **A message is never lost to a dropped connection.** It is kept on the phone from the moment
   Send is pressed until its reply arrives.
   - Sent while offline, it shows *Waiting for connection* and goes by itself on reconnect.
   - If the server fails on it, it shows *Not delivered — Retry · Delete*.
   - Text typed but not yet sent also survives an app close.
   - A recording that could not be transcribed stays in the tray and is transcribed when the
     connection returns. It is no longer dropped with an error.
4. **The server no longer runs a message twice.** It confirms receipt of each message. If the same
   message arrives again (a resend after a drop), it is answered from the original run, not by a
   second one.

---

## Pushback

1. **Headset mode keeps one press = one turn, sent automatically.** With the screen dark there is
   nothing to press for "send the batch", and the bud's button stops emitting at all once the mic
   opens (measured 2026-09-24). A tray in headset mode would hold every turn forever. Exception:
   a headset recording that fails to transcribe now goes into the tray instead of vanishing.
2. **Item 3 needs a server change as well as the client one.** Today a resent message runs the
   whole pipeline again, at a median ~26k input tokens. The second reply is then dropped silently
   by `INSERT OR IGNORE` in `_save_exchange` (`core/server.py`). An auto-resend added on the
   client alone would pay for a duplicate turn on every reconnect, and nothing would report it.
   **Deploy order is therefore server first, APK second.** A new APK against the old server would
   do exactly that.
3. **A server error is never retried automatically, only by your tap.** If a message fails the
   same way every time, an automatic retry would pay for it on every reconnect, indefinitely. For
   the same reason, a message that has been sent automatically three times without a reply waits
   for a tap. That covers a turn that crashes the server.
4. **From item 4, these are left out of this change** — none is an app change. All four are
   already in the `DEV_BACKLOG.md` Inbox, captured from what you said:
   1. *Upload a long reflection as one audio file* (10-15) — **hold.** `/transcribe` runs one job
      at a time on a 2-vCPU VM. A 30-minute file would make every voice message 503 for many
      minutes. It needs chunked, background transcription, which is its own design. The tray
      covers the other half of that ask: intermittent thoughts captured through the day and sent
      together.
   2. *The Coordinator should allow for transcription errors* (10-22) — an agent-file change, which
      is Red tier, so it gets its own session. A cheaper fix sits upstream: give Whisper a
      vocabulary of the names it keeps mishearing.
   3. *An hourly schedule-checking agent* (10-22) — Build or scheduler work. It carries a standing
      run cost (24 checks a day) to price before anything is built.
   4. *Seeing a shared, non-primary calendar* (10-20) — integration work.

## Found, not mentioned

**Some dictated messages reach Metatron cut off.** The 10-22 message that listed these app
changes is stored ending *"…it should look for phonetic"*, and the rest never arrived. Your next
message, six minutes later, was about LinkedIn. A 10-15 message ends mid-word (*"…Greenwich and
Black"*). **Both were dictated, and the transcript the server saved for each recording
(`data/audio/2026-10-22/10-07-59.json`, `data/audio/2026-10-15/11-53-14.json`) ends at the same
word.** So the text was lost at capture or transcription, not anywhere later in the pipeline. The
cause is not established. A cut mid-word points away from the 2.5s silence stop, since nobody
pauses that long inside "Blackheath", and towards the end of the audio being lost. That is still
an inference, not a measurement.

The tray makes this visible: you see each snippet's text before anything is sent, so a cut-off
snippet can be re-recorded. It does not fix the cause. **Closing test, from daily use:** when a
snippet comes back cut off, note whether you had paused (the 2.5s silence stop fired) or were
mid-word (the tail of the audio was lost). One of each tells us which it is. The standing note in
`startRecording()` forbids widening the silence window without a cut-off turn to point at; this
would be that turn.

---

## Decisions — each has a default; overrule any

1. **How long an offline message auto-sends.** **Recommended: auto-send if it was written within
   the last 15 minutes; an older one waits for one tap (*Not sent — Send · Delete*).** The pipeline
   stamps a message with the time it *arrives* (`[This message received at: …]`). An hour-old
   *"remind me in 10 minutes"* would therefore count from arrival, and a stale question can land
   in a conversation that has moved on, perhaps on the laptop. Alternative: auto-send at any age.
   That is simpler and matches your 10-19 wording literally.
2. **When snippets are stamped.** **Recommended: stamp every snippet whenever two or more go
   together.** A batch recorded in a single minute carries some redundant stamps, and the model can
   ignore them. Alternative: stamp only when the batch spans more than a few minutes. That is
   quieter, but it is a threshold to tune.
3. **Timestamp format.** **Recommended: weekday, day, month, time, in the phone's locale** (*Thu
   23 Oct, 15:41*). Alternative: *Today* / *Yesterday* for recent messages. Not recommended, because
   you asked for the date.

---

## Build steps

1. **Timestamps:** `formatTime()` in `static/index.html`.
2. **Server:** a `send` frame gets an immediate `{type: "accepted"}`. A message id that is already
   running is acknowledged, not re-run. An id that has already been answered is replayed from
   storage as one chunk plus `done`, which reuses the client's existing paths. The in-flight set
   lives in memory only. It empties when each turn ends, and a restart empties it too, which is
   correct, since a restart kills the turn. New `tests/test_ws_send_idempotent.py`: the pipeline
   is stubbed, the database is a temp file, and no persona directory is written.
3. **Client outbox:** saved to `localStorage` per persona *before* the socket is tried. The bubble
   shows a status line. Sending is strictly one at a time. Entries are reconciled against history
   on reconnect, so anything already answered is cleared, not resent. The reply (`done` or
   `retract`) clears an entry; `error` marks it failed. Steps 1 and 3 of the pushback are
   enforced here, along with the draft-persistence piece.
4. **Client voice tray:** the tray UI, with ✕ per snippet. Transcription runs one snippet at a time,
   with a back-off retry on 503. Audio not yet transcribed is held in IndexedDB and deleted once
   transcribed. A startup sweep removes audio that has no tray entry. Send composes the batch. The
   headset path is unchanged apart from pushback 1's exception. `source: headsetMode ? 'headset' :
   'ui'` is captured when a message is composed, not when it is resent, and the literal
   expression is kept for `tests/test_turn_source_marker.py`.
5. **`tests/test_client_outbox.js`**: it runs the *real* extracted code against a fake socket, as
   `tests/test_ws_reconnect_race.js` does. It covers: an offline send kept; flushed on reconnect;
   cleared by its reply; already in history, so cleared without a resend; an error never
   auto-retried; the three-attempt cap; ✕ removes a snippet and its audio.
6. **Existing suites:** every `tests/*.js`, `test_turn_source_marker.py`, `test_server_auth.py`,
   and `bash scripts/qa_sweep.sh`.
7. **Browser check** against a local server on a test persona. This costs a few Vertex turns, a
   few cents. The tracked fixture-persona files are restored afterwards with
   `git checkout HEAD --`.
8. **Review** of the diff on Fable 5.1, then fixes.
9. **Commit** on your word. **You run `./deploy.sh`**, which is Denied tier for me. Then I build
   the APK on the Mac and you sideload it (below).

---

## Cost

- **Build:** one Opus 5.5 session on the subscription, roughly $8–15 API-equivalent. The Fable
  5.1 review is roughly $3–6 API-equivalent. The browser check is a few Vertex turns, a few cents.
- **Run:** no new standing cost, and a saving. Three snippets sent together are one pipeline turn
  instead of three, about 2 × 26k input tokens saved per batch. Whisper transcribes the same audio
  either way.
- **Ancillary:** storage on the phone only. Audio is held only until transcribed (~1 MB per
  minute), text until confirmed.
- **Unseen:** a resend loop, which no meter would report. It is closed by the cap of three
  automatic sends and by never auto-retrying an error.

**Things that persist between calls — the three questions:**

1. **Phone storage** (outbox, tray, draft, untranscribed audio). The unit is bytes on the phone;
   nothing is billed. It is deleted when the reply arrives (outbox), when transcription succeeds
   (audio), and on Send or ✕ (tray). It is meant to survive a restart. Orphaned audio is swept at
   startup. No meter is needed, because there is no money.
2. **The server's in-flight set.** Memory only, emptied per turn and by restart. Nothing outlives
   the process, so there is nothing to meter.

---

## (M) Sideload walkthrough — about 10 minutes, after deploy

I build the APK and serve it. On the phone you open the link, install over the old version, and
check the build stamp under 🔔. Then run these four checks, which close the work:

1. A message shows its date.
2. Turn on airplane mode, type a message, and Send. It reads *Waiting for connection*. Kill the
   app and reopen it: the message is still there. Turn airplane mode off: it sends and gets
   **one** reply.
3. Record "A", record "B", ✕ on A, then Send. One message arrives, containing only B.
4. Record while in airplane mode. The snippet waits. Reconnect and its text appears.
