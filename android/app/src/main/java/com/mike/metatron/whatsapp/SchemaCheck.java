package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The tables and columns the app reads, checked against a decrypted database at run time
 * (format description § 6.7). Platform-free: the caller reads the schema (names only) and
 * passes it in, so the check is unit-testable without SQLite.
 *
 * {@link #REQUIRED} holds what § 9 confirms on Mike's real backup, plus the names the Phase 0
 * probe confirmed on it 2026-10-30 (message.text_data, chat.subject, jid.raw_string/user,
 * lid_display_name's columns), plus message._id and key_id, which combining with the nightly
 * increments keys on (§ 12, P3 11-23). message_media is not required: W4 is text only.
 */
public final class SchemaCheck {
    public static final Map<String, List<String>> REQUIRED;

    static {
        Map<String, List<String>> m = new LinkedHashMap<>();
        m.put("message", list("_id", "key_id", "timestamp", "from_me", "chat_row_id", "sender_jid_row_id", "text_data"));
        m.put("chat", list("jid_row_id", "subject"));
        m.put("jid", list("_id", "server", "user", "raw_string"));
        m.put("jid_map", list("lid_row_id", "jid_row_id"));
        m.put("lid_display_name", list("lid_row_id", "display_name"));
        REQUIRED = Collections.unmodifiableMap(m);
    }

    private SchemaCheck() {}

    /** Missing names, as "table" or "table.column". Empty when everything is present. */
    public static List<String> missing(Map<String, Set<String>> actual) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, List<String>> e : REQUIRED.entrySet()) {
            Set<String> cols = actual.get(e.getKey());
            if (cols == null) {
                out.add(e.getKey());
                continue;
            }
            for (String c : e.getValue()) {
                if (!cols.contains(c)) out.add(e.getKey() + "." + c);
            }
        }
        return out;
    }

    /** Refuses loudly, naming what is gone — schema names only, never content. */
    public static void require(Map<String, Set<String>> actual) throws BackupException {
        List<String> gone = missing(actual);
        if (gone.isEmpty()) return;
        StringBuilder sb = new StringBuilder(); // String.join is API 26; minSdk is 24
        for (String g : gone) sb.append(sb.length() == 0 ? "" : ", ").append(g);
        throw new BackupException(BackupError.SCHEMA_CHANGED, sb.toString());
    }

    private static List<String> list(String... names) {
        List<String> l = new ArrayList<>();
        Collections.addAll(l, names);
        return Collections.unmodifiableList(l);
    }
}
