package com.mike.metatron.whatsapp;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * One night's counts (build plan § 3.5) — code-written, counts and codes only, never text, a name
 * or a number. Posted to {@code POST /device/whatsapp/run} and kept on the phone as the last report;
 * the VM validates exactly the key set {@link #KEYS}.
 *
 * Every field is a whole number except {@link #error}; times are whole seconds since the epoch,
 * 0 when unknown. Fields are {@code long} so any int or long count assigns without a cast.
 */
public final class RunReport {
    public static final int VERSION = 1;

    /** The JSON keys, in the order {@link #toJson()} writes them. Nothing else is ever written. */
    public static final List<String> KEYS = Collections.unmodifiableList(Arrays.asList(
            "v", "run_at", "dry_run", "backup_written", "full_backup_written",
            "base_received", "base_received_text", "inc_received", "inc_received_text",
            "without_key_id", "without_chat", "text_undecodable", "base_key_collisions", "deletions_listed",
            "posted_messages", "posted_updates", "posted_reply_markers", "skipped_unchanged",
            "rejected", "dropped_not_shared", "same_second_groups", "error"));

    /** Codes this class itself names, besides every {@link BackupError#code}. */
    public static final String IO_ERROR = "io_error";
    public static final String SHARE_OUT_OF_STEP = "share_out_of_step";
    public static final String POST_FAILED = "post_failed";

    private static final int MAX_CODE = 64;

    public long v = VERSION;
    /** When this run started. */
    public long runAt;
    /** 1 for a dry run (§ 3.2: read and counted, nothing posted, nothing recorded), else 0. */
    public long dryRun;
    /** When WhatsApp wrote the live set — {@code IncrementSet.newestWriteMs() / 1000}. */
    public long backupWritten;
    /** When WhatsApp wrote the full backup. */
    public long fullBackupWritten;
    /** Received rows read from the full backup's window, across all chats, and how many had text. */
    public long baseReceived, baseReceivedText;
    /** Received rows read from the increments, across all chats, and how many had text. */
    public long incReceived, incReceivedText;
    public long withoutKeyId, withoutChat, textUndecodable, baseKeyCollisions, deletionsListed;
    /** What the VM accepted from this run, by kind, and what the sent-hash list skipped. */
    public long postedMessages, postedUpdates, postedReplyMarkers, skippedUnchanged;
    public long rejected, droppedNotShared;
    /** (chat, second) groups with two or more received rows in shared chats — § 1's ordinal limit. */
    public long sameSecondGroups;
    /**
     * "" or a code: a {@link BackupError#code}, {@link #IO_ERROR}, {@link #SHARE_OUT_OF_STEP} or
     * {@link #POST_FAILED}. Never an exception's message (§ 3.7) — {@link #toJson()} refuses
     * anything not shaped like a code.
     */
    public String error = "";

    /** True when {@code s} has the shape of a code: "" or lowercase letters, digits and '_'. */
    public static boolean isCode(String s) {
        if (s == null || s.length() > MAX_CODE) return false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_')) return false;
        }
        return true;
    }

    /**
     * Exactly {@link #KEYS}, in order.
     *
     * @throws IllegalStateException if {@link #error} is not a code — free text must never leave
     *                               the phone, so a bug here fails loudly rather than posting it
     */
    public String toJson() {
        if (!isCode(error)) throw new IllegalStateException("error is not a code");
        long[] n = numbers();
        JsonOut.Obj o = JsonOut.obj();
        for (int i = 0; i < n.length; i++) o.put(KEYS.get(i), n[i]);
        o.put("error", error);
        return o.toString();
    }

    /**
     * The report in {@code json}, or null if it is not exactly this shape: an object with every key
     * of {@link #KEYS} and no other, {@code v} = {@value #VERSION}, every number a non-negative
     * integer, {@code dry_run} 0 or 1, {@code error} a code.
     */
    public static RunReport fromJson(String json) {
        if (json == null) return null;
        Object parsed;
        try {
            parsed = Json.parse(json);
        } catch (Json.Malformed e) {
            return null;
        }
        if (!(parsed instanceof Map)) return null;
        Map<?, ?> m = (Map<?, ?>) parsed;
        Set<String> want = new LinkedHashSet<>(KEYS);
        if (!m.keySet().equals(want)) return null;
        long[] n = new long[KEYS.size() - 1];
        for (int i = 0; i < n.length; i++) {
            Object x = m.get(KEYS.get(i));
            if (!(x instanceof Long) || (Long) x < 0) return null;
            n[i] = (Long) x;
        }
        Object e = m.get("error");
        if (!(e instanceof String) || !isCode((String) e)) return null;
        RunReport r = new RunReport();
        r.setNumbers(n);
        r.error = (String) e;
        if (r.v != VERSION || (r.dryRun != 0 && r.dryRun != 1)) return null;
        return r;
    }

    private long[] numbers() {
        return new long[]{v, runAt, dryRun, backupWritten, fullBackupWritten,
                baseReceived, baseReceivedText, incReceived, incReceivedText,
                withoutKeyId, withoutChat, textUndecodable, baseKeyCollisions, deletionsListed,
                postedMessages, postedUpdates, postedReplyMarkers, skippedUnchanged,
                rejected, droppedNotShared, sameSecondGroups};
    }

    private void setNumbers(long[] n) {
        int i = 0;
        v = n[i++]; runAt = n[i++]; dryRun = n[i++]; backupWritten = n[i++]; fullBackupWritten = n[i++];
        baseReceived = n[i++]; baseReceivedText = n[i++]; incReceived = n[i++]; incReceivedText = n[i++];
        withoutKeyId = n[i++]; withoutChat = n[i++]; textUndecodable = n[i++]; baseKeyCollisions = n[i++];
        deletionsListed = n[i++];
        postedMessages = n[i++]; postedUpdates = n[i++]; postedReplyMarkers = n[i++]; skippedUnchanged = n[i++];
        rejected = n[i++]; droppedNotShared = n[i++]; sameSecondGroups = n[i];
    }

    /** Counts only — the same content as {@link #toJson()}, which carries no message content. */
    @Override
    public String toString() {
        return "RunReport" + (isCode(error) ? toJson() : "(error not a code)");
    }
}
