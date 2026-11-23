package com.mike.metatron.whatsapp;

import java.util.HashSet;
import java.util.Set;

/**
 * A tiny platform-free JSON writer — the counterpart of {@link Json}, which reads. Every Phase 2
 * body (events, the run report, the share list, the sent-hash file) is built with it, because
 * Android's org.json is a stub under the JVM unit tests.
 *
 * Strings are escaped so that any Java string — including a lone surrogate, which has no UTF-8
 * form — comes out as valid JSON in plain ASCII-safe escapes: {@code "} and {@code \\}, every
 * control character below U+0020, U+2028 / U+2029 and every unpaired surrogate as
 * {@code \\uXXXX}. A correctly paired surrogate is written as is. The output parses with
 * {@link Json} back to the same string.
 *
 * Builders keep insertion order and refuse a repeated key ({@link Json} refuses one on read).
 */
public final class JsonOut {
    private JsonOut() {}

    public static Obj obj() {
        return new Obj();
    }

    public static Arr arr() {
        return new Arr();
    }

    /** {@code s} as a JSON string literal, quotes included; {@code null} as {@code null}. */
    public static String quote(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder(s.length() + 2);
        appendQuoted(b, s);
        return b.toString();
    }

    static void appendQuoted(StringBuilder b, String s) {
        b.append('"');
        int n = s.length();
        for (int i = 0; i < n; i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); continue;
                case '\\': b.append("\\\\"); continue;
                case '\n': b.append("\\n"); continue;
                case '\r': b.append("\\r"); continue;
                case '\t': b.append("\\t"); continue;
                case '\b': b.append("\\b"); continue;
                case '\f': b.append("\\f"); continue;
                default: break;
            }
            if (c < 0x20 || c == ' ' || c == ' ') {
                hex(b, c);
            } else if (Character.isHighSurrogate(c)) {
                if (i + 1 < n && Character.isLowSurrogate(s.charAt(i + 1))) {
                    b.append(c).append(s.charAt(++i));
                } else {
                    hex(b, c);
                }
            } else if (Character.isLowSurrogate(c)) {
                hex(b, c);   // a low surrogate not preceded by a high one
            } else {
                b.append(c);
            }
        }
        b.append('"');
    }

    private static void hex(StringBuilder b, char c) {
        String h = Integer.toHexString(c);
        b.append("\\u");
        for (int k = h.length(); k < 4; k++) b.append('0');
        b.append(h);
    }

    /** A JSON object, in insertion order. */
    public static final class Obj {
        private final StringBuilder b = new StringBuilder("{");
        private final Set<String> keys = new HashSet<>();

        private StringBuilder key(String k) {
            if (k == null) throw new IllegalArgumentException("null key");
            if (!keys.add(k)) throw new IllegalArgumentException("repeated key");
            if (b.length() > 1) b.append(',');
            appendQuoted(b, k);
            return b.append(':');
        }

        /** A string value; {@code null} writes JSON null. */
        public Obj put(String k, String v) {
            StringBuilder s = key(k);
            if (v == null) s.append("null");
            else appendQuoted(s, v);
            return this;
        }

        public Obj put(String k, long v) {
            key(k).append(v);
            return this;
        }

        public Obj put(String k, boolean v) {
            key(k).append(v);
            return this;
        }

        public Obj put(String k, Obj v) {
            key(k).append(v.toString());
            return this;
        }

        public Obj put(String k, Arr v) {
            key(k).append(v.toString());
            return this;
        }

        public Obj putNull(String k) {
            key(k).append("null");
            return this;
        }

        public int size() {
            return keys.size();
        }

        @Override
        public String toString() {
            return b.toString() + "}";
        }
    }

    /** A JSON array. */
    public static final class Arr {
        private final StringBuilder b = new StringBuilder("[");
        private int n;

        private StringBuilder next() {
            if (n++ > 0) b.append(',');
            return b;
        }

        public Arr add(String v) {
            StringBuilder s = next();
            if (v == null) s.append("null");
            else appendQuoted(s, v);
            return this;
        }

        public Arr add(long v) {
            next().append(v);
            return this;
        }

        public Arr add(boolean v) {
            next().append(v);
            return this;
        }

        public Arr add(Obj v) {
            next().append(v.toString());
            return this;
        }

        public Arr add(Arr v) {
            next().append(v.toString());
            return this;
        }

        /** An already-written JSON value (e.g. {@link EventPlan.Event#toJson()}), appended verbatim. */
        public Arr addRaw(String json) {
            next().append(json);
            return this;
        }

        public int size() {
            return n;
        }

        @Override
        public String toString() {
            return b.toString() + "]";
        }
    }
}
