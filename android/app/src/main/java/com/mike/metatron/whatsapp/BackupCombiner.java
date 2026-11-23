package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The full backup plus its increments, combined (format description § 12). Platform-free.
 *
 * Start from the full backup's messages and its jid / jid_map tables; fold each increment's table
 * changes in N order; then apply each increment's messages in N order, keyed by (canonical chat,
 * from-me, key_id) — a later version replaces an earlier one, which is how an edit, or a re-sent
 * copy without text, arrives. **Deletion lists are counted, never applied** (Mike, 11-23: every
 * listed id observed was still in the newest full backup). The output is filtered by a
 * caller-supplied allowlist of canonical chat ids and a since-time — the cursor's shape.
 *
 * Canonical id: a hidden (@lid) id that jid_map links to a phone-number id becomes that id;
 * anything else stays as it is (plan P1). On Mike's data 31 of 605 increment messages named their
 * chat by the other id from the full backup's, every one linked by jid_map.
 */
public final class BackupCombiner {
    /** jid._id → raw_string, and jid_map lid_row_id → jid_row_id. Mutable while deltas are folded in. */
    public static final class JidTables {
        final Map<Long, String> raw = new HashMap<>();
        final Map<Long, Long> lidToJid = new HashMap<>();

        public void putJid(long id, String rawString) { raw.put(id, rawString); }
        public void putLink(long lidRowId, long jidRowId) { lidToJid.put(lidRowId, jidRowId); }

        JidTables copy() {
            JidTables t = new JidTables();
            t.raw.putAll(raw);
            t.lidToJid.putAll(lidToJid);
            return t;
        }

        /** One increment's jid and jid_map changes. */
        void fold(Increment inc) throws BackupException {
            Increment.TableDelta jid = inc.tables.get("jid");
            if (jid != null) {
                for (Long id : jid.deletedIds) raw.remove(id);
                for (Map<String, Object> row : jid.modified) {
                    long id = id(row, jid.idField, "jid");
                    Object rs = row.get("raw_string");
                    if (rs instanceof String) raw.put(id, (String) rs);
                    else raw.remove(id);
                }
            }
            Increment.TableDelta map = inc.tables.get("jid_map");
            if (map != null) {
                for (Long id : map.deletedIds) lidToJid.remove(id);
                for (Map<String, Object> row : map.modified) {
                    Object lid = row.get("lid_row_id"), j = row.get("jid_row_id");
                    if (!(lid instanceof Long) || !(j instanceof Long)) {
                        throw new BackupException(BackupError.INCREMENT_MISSING_PART, "jid_map row's lid_row_id or jid_row_id");
                    }
                    lidToJid.put((Long) lid, (Long) j);
                }
            }
        }

        private static long id(Map<String, Object> row, String field, String table) throws BackupException {
            Object v = row.get(field);
            if (!(v instanceof Long)) throw new BackupException(BackupError.INCREMENT_MISSING_PART, table + " row's " + field);
            return (Long) v;
        }
    }

    /** Raw id → canonical id, from folded tables. */
    static final class Canon {
        private final Map<String, String> map = new HashMap<>();

        Canon(JidTables t) {
            for (Map.Entry<Long, Long> e : t.lidToJid.entrySet()) {
                String lid = t.raw.get(e.getKey()), phone = t.raw.get(e.getValue());
                if (lid != null && phone != null && lid.endsWith("@lid")) map.put(lid, phone);
            }
        }

        String of(String raw) {
            if (raw == null) return null;
            String c = map.get(raw);
            return c == null ? raw : c;
        }
    }

    public static final class Combined {
        /** Allowed chats, since the since-time, oldest first; chat and sender ids canonical. */
        public final List<WaMessage> messages;
        public final int baseMessages, incrementsApplied, incrementMessages, added, replaced, textChanged, deletionsListed;

        Combined(List<WaMessage> messages, int baseMessages, int incrementsApplied, int incrementMessages,
                 int added, int replaced, int textChanged, int deletionsListed) {
            this.messages = Collections.unmodifiableList(messages);
            this.baseMessages = baseMessages;
            this.incrementsApplied = incrementsApplied;
            this.incrementMessages = incrementMessages;
            this.added = added;
            this.replaced = replaced;
            this.textChanged = textChanged;
            this.deletionsListed = deletionsListed;
        }
    }

    private BackupCombiner() {}

    /**
     * @param base         the full backup's messages (raw ids), any order
     * @param tables       the full backup's jid and jid_map tables; not modified
     * @param increments   the set's increments, N = 1..k in order
     * @param allowedChats canonical chat ids to return; empty returns nothing
     * @param sinceMs      return messages at or after this time
     */
    public static Combined combine(List<WaMessage> base, JidTables tables, List<Increment> increments,
                                   Set<String> allowedChats, long sinceMs) throws BackupException {
        for (int i = 0; i < increments.size(); i++) {
            if (increments.get(i).number != i + 1) {
                throw new BackupException(BackupError.INCREMENT_GAP, "increment " + (i + 1) + " missing; " + i + " readable before it");
            }
        }
        JidTables t = tables.copy();
        for (Increment inc : increments) t.fold(inc);
        Canon canon = new Canon(t);

        Map<String, WaMessage> byKey = new LinkedHashMap<>();
        for (WaMessage m : base) byKey.put(key(canon, m), m);
        int incMessages = 0, added = 0, replaced = 0, textChanged = 0, deletions = 0;
        for (Increment inc : increments) {
            deletions += inc.deletedMessageIds.size();
            for (WaMessage m : inc.messages) {
                incMessages++;
                String k = key(canon, m);
                WaMessage prev = byKey.get(k);
                WaMessage next = m;
                if (prev == null) {
                    added++;
                } else {
                    replaced++;
                    if (prev.text == null ? m.text != null : !prev.text.equals(m.text)) textChanged++;
                    // An increment carries seconds; keep the full backup's milliseconds for the same
                    // second, so the message's time (P2's dedup key) does not move.
                    if (prev.timeMs / 1000 == m.timeMs / 1000) next = m.with(m.chatJid, m.senderJid, prev.timeMs);
                }
                byKey.put(k, next);
            }
        }

        List<WaMessage> out = new ArrayList<>();
        for (WaMessage m : byKey.values()) {
            String chat = canon.of(m.chatJid);
            if (!allowedChats.contains(chat) || m.timeMs < sinceMs) continue;
            out.add(m.with(chat, canon.of(m.senderJid), m.timeMs));
        }
        Collections.sort(out, (a, b) -> a.timeMs != b.timeMs ? Long.compare(a.timeMs, b.timeMs) : Long.compare(a.rowId, b.rowId));
        return new Combined(out, base.size(), increments.size(), incMessages, added, replaced, textChanged, deletions);
    }

    private static String key(Canon canon, WaMessage m) {
        return canon.of(m.chatJid) + '\u0000' + (m.fromMe ? '1' : '0') + '\u0000' + m.keyId;
    }

    /** These messages with chat and sender canonicalised against these tables — for checks that compare sources. */
    static List<WaMessage> canonicalise(List<WaMessage> messages, JidTables tables) {
        Canon canon = new Canon(tables);
        List<WaMessage> out = new ArrayList<>(messages.size());
        for (WaMessage m : messages) out.add(m.with(canon.of(m.chatJid), canon.of(m.senderJid), m.timeMs));
        return out;
    }

    /** The combine key of an already-canonical message. */
    static String key(WaMessage canonical) {
        return canonical.chatJid + '\u0000' + (canonical.fromMe ? '1' : '0') + '\u0000' + canonical.keyId;
    }
}
