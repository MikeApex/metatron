package com.mike.metatron.whatsapp;

import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Posts one night's events to {@code POST /device/whatsapp/events} in batches (plan § 3.2; review 1
 * and 3, verify new 4). Plain Java over {@link DeviceApi}, so every rule below is unit-tested.
 *
 * <ul>
 * <li><b>Batches:</b> events oldest first, at most {@value #MAX_EVENTS} events and
 *     {@value #MAX_BODY_BYTES} bytes of body per post, {@value #READ_TIMEOUT_MS} ms read timeout —
 *     the VM translates and screens every event before its duplicate check.</li>
 * <li><b>A 413 or a timeout halves the batch</b> (and every later one) and retries once; any other
 *     failure retries once at the same size; <b>a second failure in a row ends the run</b> for
 *     tonight with {@link RunReport#POST_FAILED}, the batch's keys unrecorded, so tomorrow sends
 *     them.</li>
 * <li><b>Nothing is recorded as sent unless the VM took it</b> (review 1): a reply with
 *     {@code dropped_not_shared > 0} records <b>none</b> of the batch's keys, re-posts the share
 *     list and retries the batch once; if the re-post is not accepted, or the drop repeats, the run
 *     ends, {@code SHARE_OUT_OF_STEP} is raised and the error is {@link RunReport#SHARE_OUT_OF_STEP}.</li>
 * <li><b>A per-event {@code rejected}</b> is recorded as sent — never retried — and counted.</li>
 * <li><b>The cursor</b> each accepted batch carries is the newest second in it, never earlier than
 *     the cursor the run started from, and is <b>sent only while every earlier post of the run was
 *     accepted</b>: after any post that was not, no later post carries one — after a timeout the VM
 *     may already hold a later cursor, and the phone must never send it backwards.</li>
 * <li><b>Every reply goes through the gate</b>; a 401 or 403 ends the run.</li>
 * </ul>
 */
final class Poster {
    static final int MAX_EVENTS = 100;
    static final int MAX_BODY_BYTES = 256 * 1024;
    static final int READ_TIMEOUT_MS = 120_000;
    static final String PATH = "/device/whatsapp/events";
    /** {@code {"events":[` … `],"cursor":NNNNNNNNNNN}} — rounded up. */
    private static final int ENVELOPE_BYTES = 64;

    /** What posting needs from outside plain Java. */
    interface Host {
        DeviceApi api();

        /** {@link Gate#observe} on the phone. */
        Gate.State observe(DeviceApi.Result r);

        /** {@link ShareList#repost} on the phone. */
        ShareList.Post repostShareList();

        /** {@code Notices.raise(SHARE_OUT_OF_STEP)} on the phone. */
        void raiseShareOutOfStep();

        boolean cancelled();
    }

    /** How the posting went. Counts only. */
    static final class Outcome {
        /** "" when every event was posted (or there were none); else a {@link RunReport} code. */
        String error = "";
        /** Stopped at a cancel check between batches. */
        boolean stopped;
        /** A 401 or 403 ended the run: the channel is closed or the pairing refused. */
        boolean authEnded;
        /** Accepted by kind (rejected events not counted here). */
        long messages, updates, replyMarkers;
        long rejected, droppedNotShared;
        int posts;
        /** The newest cursor a post the VM accepted carried; 0 when none did. */
        long cursorSent;

        @Override
        public String toString() {
            return "Poster.Outcome(" + (error.isEmpty() ? "ok" : error) + ", " + posts + " posts, "
                    + messages + "/" + updates + "/" + replyMarkers + " accepted, " + rejected + " rejected, "
                    + droppedNotShared + " dropped" + (stopped ? ", stopped" : "") + (authEnded ? ", refused" : "") + ")";
        }
    }

    private Poster() {}

    /**
     * Posts {@code events} (already oldest first — {@link EventPlan#events}) and records each batch
     * the VM accepted in {@code sent}.
     *
     * @param startCursor the VM's cursor at the start of the run; null when it has none
     */
    static Outcome post(Host h, SentHashes sent, List<EventPlan.Event> events, Long startCursor) {
        Outcome out = new Outcome();
        int n = events.size();
        String[] json = new String[n];
        int[] bytes = new int[n];
        for (int k = 0; k < n; k++) {
            json[k] = events.get(k).toJson();
            bytes[k] = json[k].getBytes(StandardCharsets.UTF_8).length;
        }
        long floor = startCursor == null ? 0 : startCursor;
        int limit = MAX_EVENTS;
        boolean allAccepted = true, failRetried = false, dropRetried = false;
        int i = 0;
        while (i < n) {
            if (h.cancelled()) {
                out.stopped = true;
                return out;
            }
            int size = batchSize(bytes, i, limit);
            List<EventPlan.Event> batch = events.subList(i, i + size);
            long cursor = allAccepted ? Math.max(floor, batch.get(size - 1).second) : 0;
            DeviceApi.Result r = h.api().post(PATH, body(json, i, size, cursor), READ_TIMEOUT_MS);
            out.posts++;
            h.observe(r);
            if (r.status == 401 || r.status == 403) {
                out.authEnded = true;
                out.error = RunReport.POST_FAILED;
                return out;
            }
            Reply reply = r.status == 200 ? Reply.parse(r.body, size) : null;
            if (reply != null && reply.dropped > 0) {
                // Nothing of this batch is recorded: the VM's share list is not the phone's (review 1).
                out.droppedNotShared += reply.dropped;
                allAccepted = false;
                if (dropRetried || h.repostShareList() != ShareList.Post.ACCEPTED) {
                    h.raiseShareOutOfStep();
                    out.error = RunReport.SHARE_OUT_OF_STEP;
                    return out;
                }
                dropRetried = true;
                continue;
            }
            if (reply != null) {
                try {
                    sent.recordAll(batch);
                } catch (UncheckedIOException e) {
                    out.error = RunReport.IO_ERROR;
                    return out;
                }
                for (int k = 0; k < size; k++) {
                    if (reply.rejected.contains(k)) continue;
                    String kind = batch.get(k).kind;
                    if (EventPlan.MESSAGE.equals(kind)) out.messages++;
                    else if (EventPlan.UPDATE.equals(kind)) out.updates++;
                    else if (EventPlan.REPLY_MARKER.equals(kind)) out.replyMarkers++;
                }
                out.rejected += reply.rejected.size();
                if (cursor > 0) {
                    out.cursorSent = cursor;
                    floor = cursor;
                }
                i += size;
                failRetried = false;
                dropRetried = false;
                continue;
            }
            // Not taken: a 413, a timeout, any other status, no answer, or a reply that does not read.
            allAccepted = false;
            if (failRetried) {
                out.error = RunReport.POST_FAILED;
                return out;
            }
            failRetried = true;
            if (r.status == 413 || isTimeout(r)) limit = Math.max(1, size / 2);
        }
        return out;
    }

    /** How many events from {@code from} fit one post: at least one, at most {@code limit}, within the byte cap. */
    static int batchSize(int[] bytes, int from, int limit) {
        int total = ENVELOPE_BYTES, k = from;
        while (k < bytes.length && k - from < limit) {
            int add = bytes[k] + (k > from ? 1 : 0);
            if (k > from && total + add > MAX_BODY_BYTES) break;
            total += add;
            k++;
        }
        return Math.max(1, k - from);
    }

    /** {@code {"events":[…]}} with {@code "cursor"} when it is positive. */
    static String body(String[] json, int from, int size, long cursor) {
        StringBuilder b = new StringBuilder("{\"events\":[");
        for (int k = from; k < from + size; k++) {
            if (k > from) b.append(',');
            b.append(json[k]);
        }
        b.append(']');
        if (cursor > 0) b.append(",\"cursor\":").append(cursor);
        return b.append('}').toString();
    }

    static boolean isTimeout(DeviceApi.Result r) {
        return r.status == DeviceApi.NETWORK && "SocketTimeoutException".equals(r.detail);
    }

    /** The parts of the VM's reply the phone acts on. */
    static final class Reply {
        final long dropped;
        /** Batch indexes the VM rejected. */
        final Set<Integer> rejected;

        private Reply(long dropped, Set<Integer> rejected) {
            this.dropped = dropped;
            this.rejected = rejected;
        }

        /** Null when the body is not the VM's reply shape — then the batch is treated as not taken. */
        static Reply parse(String body, int batchSize) {
            Object v;
            try {
                v = Json.parse(body);
            } catch (Json.Malformed e) {
                return null;
            }
            if (!(v instanceof Map)) return null;
            Map<?, ?> m = (Map<?, ?>) v;
            Object d = m.get("dropped_not_shared");
            if (!(d instanceof Long) || (Long) d < 0) return null;
            Set<Integer> rejected = new HashSet<>();
            Object rj = m.get("rejected");
            if (rj != null) {
                if (!(rj instanceof List)) return null;
                for (Object o : (List<?>) rj) {
                    if (!(o instanceof Map)) continue;
                    Object idx = ((Map<?, ?>) o).get("index");
                    if (idx instanceof Long && (Long) idx >= 0 && (Long) idx < batchSize) rejected.add(((Long) idx).intValue());
                }
            }
            return new Reply((Long) d, rejected);
        }
    }
}
