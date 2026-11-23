package com.mike.metatron.whatsapp;

/**
 * One WhatsApp message as the reader returns it — from a full backup's message row or an
 * increment's messages.bin (format description § 12). Platform-free and immutable.
 *
 * {@code chatJid} and {@code senderJid} are raw strings as read; {@link BackupCombiner} returns
 * them canonicalised. {@code senderJid} is set only on group messages not sent by the user;
 * {@code text} is null for a message with no text (media without a caption, a reaction, …).
 */
public final class WaMessage {
    public final String chatJid;
    public final String keyId;
    public final boolean fromMe;
    /** Milliseconds since the epoch. An increment carries seconds, so its times end in 000. */
    public final long timeMs;
    public final String senderJid;
    public final String text;
    /** message._id — the full backup's row id; increments share its id space. */
    public final long rowId;
    /**
     * 0-based position among the same canonical chat's messages in the same whole second, by row
     * id, counted separately for received and for from-me rows — the contract's {@code ordinal}
     * (Phase 1 build plan § 2.2). Assigned only by {@link BackupCombiner#combine}; 0 as read.
     */
    public final int ordinal;

    public WaMessage(String chatJid, String keyId, boolean fromMe, long timeMs, String senderJid, String text, long rowId) {
        this(chatJid, keyId, fromMe, timeMs, senderJid, text, rowId, 0);
    }

    private WaMessage(String chatJid, String keyId, boolean fromMe, long timeMs, String senderJid, String text, long rowId,
                      int ordinal) {
        this.chatJid = chatJid;
        this.keyId = keyId;
        this.fromMe = fromMe;
        this.timeMs = timeMs;
        this.senderJid = senderJid;
        this.text = text;
        this.rowId = rowId;
        this.ordinal = ordinal;
    }

    WaMessage with(String chat, String sender, long time) {
        return new WaMessage(chat, keyId, fromMe, time, sender, text, rowId, ordinal);
    }

    WaMessage withOrdinal(int n) {
        return new WaMessage(chatJid, keyId, fromMe, timeMs, senderJid, text, rowId, n);
    }

    /** Deliberately no content: a message must never reach a log by accident. */
    @Override
    public String toString() {
        return "WaMessage(row " + rowId + ")";
    }
}
