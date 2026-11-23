package com.mike.metatron.whatsapp;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/**
 * Which of the user's own messages count as a reply — the one place this is decided (Phase 2 plan
 * § 2 item 2; decision 5, ruled by Mike 2026-11-23). Platform-free.
 *
 * A message is a reply only when it is from the user and: its type is known and in {@link #ALLOWED};
 * or its type is unknown (a row new in an increment, which carries no type) and its content block
 * was present. The set comes from counts on Mike's backup — each of these types is both sent and
 * received and carries content — not from any meaning given to the numbers. **A type not in the set
 * is not a reply**: an unfamiliar kind errs toward asking again, never toward silence.
 */
public final class ReplyRule {
    public static final Set<Integer> ALLOWED =
            Collections.unmodifiableSet(new HashSet<>(Arrays.asList(0, 1, 2, 3, 4, 9)));

    private ReplyRule() {}

    public static boolean isReply(WaMessage m) {
        if (m == null || !m.fromMe) return false;
        if (m.type >= 0) return ALLOWED.contains(m.type);
        return Boolean.TRUE.equals(m.hasContent);
    }
}
