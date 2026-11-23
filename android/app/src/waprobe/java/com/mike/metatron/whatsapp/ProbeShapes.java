package com.mike.metatron.whatsapp;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Probe only — the SHAPE of an increment's non-SQLite ZIP entries (Phase 0, 11-23, second round;
 * plan § 4 NEXT ROUND RULED). JSON entries are described by key path; any other entry is walked as
 * the generic protobuf wire format without a schema — tag varint, wire types 0/1/2/5, which is
 * public, general knowledge and nothing taken from any WhatsApp implementation (clean room, W9).
 * Plain Java, so it runs under testWaprobeUnitTest.
 *
 * NEVER A VALUE, with three exceptions, each decided in code:
 *  1. an integer whose magnitude is below {@link #PLAIN_LIMIT} (10^7) — row ids, counts, flags,
 *     versions; a phone number has 8+ digits, so it cannot pass;
 *  2. a number inside the 2015–2030 epoch range, shown as a date to the minute (message times are
 *     already reported by earlier probes);
 *  3. a string that is a table or column name of the full backup's own schema.
 * Only min/max are ever shown, never a list. Everything else is types, lengths and counts, and
 * comparisons with the full backup are counts only. A JSON key is shown only when it looks like an
 * identifier (lower-case letter or underscore first, then letters/digits/underscore) or is a schema name; any other key
 * is folded into {*}.
 */
final class ProbeShapes {
    /** What the newest full backup can answer. Implemented over SQLite in ProbeIncrement; faked in tests. */
    interface Full {
        Set<String> schemaNames();
        Set<String> messageKeyIds();
        /** jid.raw_string values — counted against, never shown. */
        Set<String> jidRawStrings();
        /** Newest message time in the full backup, ms; -1 when unknown. */
        long newestMessageTime();
        /** How many of these _id values the full backup's table holds: -1 no such table, -2 no _id column. */
        int idsPresent(String table, List<Long> ids);
    }

    static final Full NONE = new Full() {
        public Set<String> schemaNames() { return Collections.emptySet(); }
        public Set<String> messageKeyIds() { return Collections.emptySet(); }
        public Set<String> jidRawStrings() { return Collections.emptySet(); }
        public long newestMessageTime() { return -1; }
        public int idsPresent(String table, List<Long> ids) { return -1; }
    };

    static final long PLAIN_LIMIT = 10_000_000L;
    static final long MS_LO = 1_420_070_400_000L, MS_HI = 1_924_992_000_000L; // 2015-01-01 .. 2031-01-01 UTC
    static final int MAX_SHOWN_PATHS = 400, MAX_RECORDED_PATHS = 400, MAX_IDS = 5000, MAX_DEPTH = 12;
    static final int MAX_SCHEMA_SHOWN = 30;
    /** The phone's zone by default, as ProbeReport uses; tests pin it. */
    static TimeZone zone = TimeZone.getDefault();

    private static final Pattern TABLE_FILE = Pattern.compile("^([a-z][a-z0-9_]*?)_(modified|deleted)_\\d+\\.json$");
    private static final Pattern IDENT_KEY = Pattern.compile("[a-z_][A-Za-z0-9_]{0,47}");
    private static final Pattern HEX = Pattern.compile("[0-9A-Fa-f]{8,}");

    private ProbeShapes() {}

    /** One entry's shape block, appended to b. */
    static void entry(String name, byte[] data, Full full, StringBuilder b) {
        b.append(name).append("  (").append(data.length).append(" bytes)");
        if (looksJson(data)) {
            b.append(" — JSON\n");
            json(name, data, full, b);
        } else {
            b.append(" — not JSON; generic protobuf wire-format test\n");
            protobuf(data, full, b);
        }
    }

    // ---- JSON ------------------------------------------------------------------------------

    static void json(String name, byte[] data, Full full, StringBuilder b) {
        Collector c = new Collector(full);
        Json p = new Json(new String(data, StandardCharsets.UTF_8), c);
        try {
            p.ws();
            p.value("", 0);
            p.ws();
            if (p.i < p.s.length()) b.append("  note: ").append(p.s.length() - p.i).append(" characters after the JSON value\n");
        } catch (IllegalStateException e) {
            b.append("  JSON parse stopped at character ").append(p.i).append(": ").append(e.getMessage()).append('\n');
        }
        c.lines(b);
        Matcher m = TABLE_FILE.matcher(name);
        if (!c.ids.isEmpty()) {
            b.append("  _id values: ").append(c.ids.size()).append(c.idsCapped ? " (capped)" : "");
            if (m.matches()) {
                String table = m.group(1);
                int present = full.idsPresent(table, c.ids);
                if (present == -1) b.append(" — the full backup has no table ").append(table);
                else if (present == -2) b.append(" — the full backup's ").append(table).append(" has no _id column");
                else b.append(" — already in the full backup's ").append(table).append(": ").append(present)
                            .append(", not there: ").append(c.ids.size() - present);
            }
            b.append('\n');
        }
    }

    static boolean looksJson(byte[] d) {
        for (byte x : d) {
            if (x == ' ' || x == '\n' || x == '\r' || x == '\t') continue;
            return x == '{' || x == '[';
        }
        return false;
    }

    /** A small strict JSON reader that records shapes, never values. */
    private static final class Json {
        final String s;
        final Collector c;
        int i;

        Json(String s, Collector c) { this.s = s; this.c = c; }

        void value(String path, int depth) {
            if (depth > MAX_DEPTH * 4) throw new IllegalStateException("nested too deep");
            ws();
            if (i >= s.length()) throw new IllegalStateException("unexpected end");
            char ch = s.charAt(i);
            Stat st = c.stat(path.isEmpty() ? "(root)" : path);
            if (ch == '{') {
                i++;
                if (st != null) st.objects++;
                ws();
                if (peek('}')) { i++; return; }
                while (true) {
                    ws();
                    String key = string();
                    ws();
                    expect(':');
                    value(path + "." + keyLabel(key), depth + 1);
                    ws();
                    if (peek(',')) { i++; continue; }
                    expect('}');
                    return;
                }
            }
            if (ch == '[') {
                i++;
                int n = 0;
                ws();
                if (!peek(']')) {
                    while (true) {
                        value(path + "[]", depth + 1);
                        n++;
                        ws();
                        if (peek(',')) { i++; continue; }
                        expect(']');
                        break;
                    }
                } else {
                    i++;
                }
                if (st != null) {
                    st.arrays++;
                    st.arrMin = Math.min(st.arrMin, n);
                    st.arrMax = Math.max(st.arrMax, n);
                }
                return;
            }
            if (ch == '"') {
                String v = string();
                if (st != null) c.text(st, v, false);
                return;
            }
            if (s.startsWith("true", i) || s.startsWith("false", i)) {
                i += s.startsWith("true", i) ? 4 : 5;
                if (st != null) st.bools++;
                return;
            }
            if (s.startsWith("null", i)) {
                i += 4;
                if (st != null) st.nulls++;
                return;
            }
            int start = i;
            while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) i++;
            if (start == i) throw new IllegalStateException("unexpected character");
            String num = s.substring(start, i);
            if (st == null) return;
            if (num.indexOf('.') >= 0 || num.indexOf('e') >= 0 || num.indexOf('E') >= 0) {
                st.floats++;
                return;
            }
            try {
                long v = Long.parseLong(num);
                c.number(st, v);
                if (path.endsWith("._id")) c.id(v);
            } catch (NumberFormatException e) {
                st.bigN++;
                st.bigDigits = Math.max(st.bigDigits, num.replace("-", "").length());
            }
        }

        String string() {
            expect('"');
            StringBuilder out = new StringBuilder();
            while (true) {
                if (i >= s.length()) throw new IllegalStateException("unterminated string");
                char ch = s.charAt(i++);
                if (ch == '"') return out.toString();
                if (ch != '\\') { out.append(ch); continue; }
                if (i >= s.length()) throw new IllegalStateException("unterminated escape");
                char e = s.charAt(i++);
                switch (e) {
                    case 'n': out.append('\n'); break;
                    case 't': out.append('\t'); break;
                    case 'r': out.append('\r'); break;
                    case 'b': out.append('\b'); break;
                    case 'f': out.append('\f'); break;
                    case 'u':
                        if (i + 4 > s.length()) throw new IllegalStateException("short \\u escape");
                        out.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                        i += 4;
                        break;
                    default: out.append(e);
                }
            }
        }

        String keyLabel(String key) {
            if (IDENT_KEY.matcher(key).matches() || c.full.schemaNames().contains(key)) return key;
            return "{*}";
        }

        void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }
        boolean peek(char ch) { return i < s.length() && s.charAt(i) == ch; }
        void expect(char ch) {
            if (!peek(ch)) throw new IllegalStateException("expected '" + ch + "'");
            i++;
        }
    }

    // ---- protobuf wire format (generic) ------------------------------------------------------

    static void protobuf(byte[] d, Full full, StringBuilder b) {
        List<int[]> records = delimited(d);
        boolean whole = isMessage(d, 0, d.length);
        b.append("  varint-length-delimited records: ");
        if (records == null) {
            b.append("no\n");
        } else {
            int lo = Integer.MAX_VALUE, hi = 0;
            for (int[] r : records) { lo = Math.min(lo, r[1] - r[0]); hi = Math.max(hi, r[1] - r[0]); }
            b.append("YES — ").append(records.size()).append(" record(s), sizes ").append(lo).append("..").append(hi).append('\n');
        }
        b.append("  whole entry as one message: ").append(whole ? "YES" : "no").append('\n');
        Collector c = new Collector(full);
        if (records != null) {
            for (int[] r : records) walk(d, r[0], r[1], "rec", 0, c);
        } else if (whole) {
            walk(d, 0, d.length, "msg", 0, c);
        } else {
            int zeros = 0;
            for (byte x : d) if (x == 0) zeros++;
            b.append("  no protobuf structure found; zero bytes ").append(d.length == 0 ? 0 : (100L * zeros / d.length)).append("%\n");
            return;
        }
        b.append("  field paths (path = field numbers; wire type in words):\n");
        c.lines(b);
    }

    /** [start, end) of each record when the whole buffer is varint-length-prefixed messages; else null. */
    static List<int[]> delimited(byte[] d) {
        List<int[]> out = new ArrayList<>();
        int pos = 0;
        while (pos < d.length) {
            long[] v = varint(d, pos, d.length);
            if (v == null || v[0] <= 0 || v[0] > d.length - v[1]) return null;
            int s = (int) v[1], e = s + (int) v[0];
            if (!isMessage(d, s, e)) return null;
            out.add(new int[]{s, e});
            pos = e;
        }
        return out.isEmpty() ? null : out;
    }

    /** True when [off, end) tiles exactly into fields of wire type 0, 1, 2 or 5 with field numbers >= 1. */
    static boolean isMessage(byte[] d, int off, int end) {
        if (off >= end) return false;
        int pos = off;
        while (pos < end) {
            long[] t = varint(d, pos, end);
            if (t == null) return false;
            long field = t[0] >>> 3;
            int wt = (int) (t[0] & 7);
            if (field < 1 || field > 536_870_911L) return false;
            pos = (int) t[1];
            switch (wt) {
                case 0: {
                    long[] v = varint(d, pos, end);
                    if (v == null) return false;
                    pos = (int) v[1];
                    break;
                }
                case 1: pos += 8; break;
                case 5: pos += 4; break;
                case 2: {
                    long[] l = varint(d, pos, end);
                    if (l == null || l[0] < 0 || l[0] > end - l[1]) return false;
                    pos = (int) (l[1] + l[0]);
                    break;
                }
                default: return false;
            }
            if (pos > end) return false;
        }
        return pos == end;
    }

    private static void walk(byte[] d, int off, int end, String path, int depth, Collector c) {
        int pos = off;
        while (pos < end) {
            long[] t = varint(d, pos, end);
            int field = (int) (t[0] >>> 3), wt = (int) (t[0] & 7);
            pos = (int) t[1];
            Stat st = c.stat(path + "." + field);
            if (wt == 0) {
                long[] v = varint(d, pos, end);
                pos = (int) v[1];
                if (st != null) c.number(st, v[0]);
            } else if (wt == 1) {
                if (st != null) st.fixed64++;
                pos += 8;
            } else if (wt == 5) {
                if (st != null) st.fixed32++;
                pos += 4;
            } else {
                long[] l = varint(d, pos, end);
                int s = (int) l[1], e = s + (int) l[0];
                pos = e;
                if (st == null) {
                    if (depth < MAX_DEPTH && !isText(d, s, e) && isMessage(d, s, e)) walk(d, s, e, path + "." + field, depth + 1, c);
                    continue;
                }
                if (e == s) {
                    st.empty++;
                } else if (isText(d, s, e)) {
                    c.text(st, new String(d, s, e - s, StandardCharsets.UTF_8), isMessage(d, s, e));
                } else if (depth < MAX_DEPTH && isMessage(d, s, e)) {
                    st.messages++;
                    walk(d, s, e, path + "." + field, depth + 1, c);
                } else {
                    st.bytesN++;
                    st.lenMin = Math.min(st.lenMin, e - s);
                    st.lenMax = Math.max(st.lenMax, e - s);
                }
            }
        }
    }

    /** {value, next position}, or null when the varint is malformed or runs past end. */
    static long[] varint(byte[] d, int pos, int end) {
        long v = 0;
        for (int shift = 0; shift < 64; shift += 7) {
            if (pos >= end) return null;
            int x = d[pos++] & 0xff;
            v |= (long) (x & 0x7f) << shift;
            if ((x & 0x80) == 0) return new long[]{v, pos};
        }
        return null;
    }

    /** Strict UTF-8 with no control characters other than tab, CR and LF. */
    static boolean isText(byte[] d, int s, int e) {
        if (e <= s) return false;
        CharsetDecoder dec = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT);
        String str;
        try {
            str = dec.decode(ByteBuffer.wrap(d, s, e - s)).toString();
        } catch (CharacterCodingException ex) {
            return false;
        }
        for (int i = 0; i < str.length(); i++) {
            char ch = str.charAt(i);
            if ((ch < 0x20 && ch != '\t' && ch != '\n' && ch != '\r') || ch == 0x7f) return false;
        }
        return true;
    }

    // ---- recording -------------------------------------------------------------------------

    static final class Stat {
        final String path;
        int objects, arrays, bools, nulls, floats, messages, bytesN, fixed32, fixed64, empty;
        int arrMin = Integer.MAX_VALUE, arrMax = -1;
        int texts, textAlsoMessage, textLenMin = Integer.MAX_VALUE, textLenMax = -1, hexLike, keyIdHits, jidHits, schemaHits;
        final TreeSet<String> schemaSeen = new TreeSet<>();
        int lenMin = Integer.MAX_VALUE, lenMax = -1;
        int plainN, msN, sN, bigN, bigDigits, newer;
        long plainMin = Long.MAX_VALUE, plainMax = Long.MIN_VALUE, msMin = Long.MAX_VALUE, msMax = Long.MIN_VALUE,
                sMin = Long.MAX_VALUE, sMax = Long.MIN_VALUE;

        Stat(String path) { this.path = path; }
    }

    static final class Collector {
        final Full full;
        final Map<String, Stat> stats = new LinkedHashMap<>();
        final List<Long> ids = new ArrayList<>();
        boolean idsCapped;
        int droppedPaths;

        Collector(Full full) { this.full = full; }

        /** The stat for a path, or null once MAX_RECORDED_PATHS distinct paths exist. */
        Stat stat(String path) {
            Stat s = stats.get(path);
            if (s == null) {
                if (stats.size() >= MAX_RECORDED_PATHS) { droppedPaths++; return null; }
                s = new Stat(path);
                stats.put(path, s);
            }
            return s;
        }

        void id(long v) {
            if (ids.size() < MAX_IDS) ids.add(v); else idsCapped = true;
        }

        void number(Stat st, long v) {
            long newest = full.newestMessageTime();
            if (v > -PLAIN_LIMIT && v < PLAIN_LIMIT) {
                st.plainN++;
                st.plainMin = Math.min(st.plainMin, v);
                st.plainMax = Math.max(st.plainMax, v);
            } else if (v >= MS_LO && v < MS_HI) {
                st.msN++;
                st.msMin = Math.min(st.msMin, v);
                st.msMax = Math.max(st.msMax, v);
                if (newest > 0 && v > newest) st.newer++;
            } else if (v >= MS_LO / 1000 && v < MS_HI / 1000) {
                st.sN++;
                st.sMin = Math.min(st.sMin, v);
                st.sMax = Math.max(st.sMax, v);
                if (newest > 0 && v * 1000 > newest) st.newer++;
            } else {
                st.bigN++;
                st.bigDigits = Math.max(st.bigDigits, Long.toString(v).replace("-", "").length());
            }
        }

        void text(Stat st, String v, boolean alsoMessage) {
            st.texts++;
            if (alsoMessage) st.textAlsoMessage++;
            int len = v.length();
            st.textLenMin = Math.min(st.textLenMin, len);
            st.textLenMax = Math.max(st.textLenMax, len);
            if (HEX.matcher(v).matches()) st.hexLike++;
            if (full.messageKeyIds().contains(v)) st.keyIdHits++;
            if (full.jidRawStrings().contains(v)) st.jidHits++;
            if (full.schemaNames().contains(v)) {
                st.schemaHits++;
                if (st.schemaSeen.size() < MAX_SCHEMA_SHOWN) st.schemaSeen.add(v);
            }
        }

        void lines(StringBuilder b) {
            int shown = 0;
            for (Stat s : stats.values()) {
                if (shown++ >= MAX_SHOWN_PATHS) break;
                b.append("    ").append(s.path).append("  ").append(describe(s)).append('\n');
            }
            int more = stats.size() - Math.min(stats.size(), MAX_SHOWN_PATHS);
            if (more > 0 || droppedPaths > 0) {
                b.append("    … ").append(more).append(" more paths").append(droppedPaths > 0 ? " (and values past the path cap not recorded)" : "").append('\n');
            }
        }
    }

    static String describe(Stat s) {
        List<String> p = new ArrayList<>();
        if (s.objects > 0) p.add("object×" + s.objects);
        if (s.messages > 0) p.add("message×" + s.messages);
        if (s.arrays > 0) p.add("array×" + s.arrays + " len " + s.arrMin + ".." + s.arrMax);
        if (s.texts > 0) {
            StringBuilder t = new StringBuilder("text×").append(s.texts).append(" len ").append(s.textLenMin).append("..").append(s.textLenMax);
            if (s.hexLike > 0) t.append(", hex-like ").append(s.hexLike);
            if (s.keyIdHits > 0) t.append(", equal to a full-backup message key_id ").append(s.keyIdHits);
            if (s.jidHits > 0) t.append(", equal to a full-backup jid ").append(s.jidHits);
            if (s.textAlsoMessage > 0) t.append(", also parses as a message ").append(s.textAlsoMessage);
            if (s.schemaHits > 0) {
                t.append(", schema names ").append(s.schemaHits);
                if (s.schemaHits == s.texts) t.append(' ').append(s.schemaSeen);
            }
            p.add(t.toString());
        }
        if (s.plainN > 0) p.add("int×" + s.plainN + " " + s.plainMin + ".." + s.plainMax);
        if (s.msN > 0) p.add("time(ms)×" + s.msN + " " + when(s.msMin) + " .. " + when(s.msMax));
        if (s.sN > 0) p.add("time(s)×" + s.sN + " " + when(s.sMin * 1000) + " .. " + when(s.sMax * 1000));
        if (s.newer > 0) p.add("newer than the full backup's newest message " + s.newer);
        if (s.bigN > 0) p.add("large number×" + s.bigN + " (up to " + s.bigDigits + " digits)");
        if (s.floats > 0) p.add("decimal×" + s.floats);
        if (s.bools > 0) p.add("bool×" + s.bools);
        if (s.nulls > 0) p.add("null×" + s.nulls);
        if (s.fixed64 > 0) p.add("fixed64×" + s.fixed64);
        if (s.fixed32 > 0) p.add("fixed32×" + s.fixed32);
        if (s.bytesN > 0) p.add("bytes×" + s.bytesN + " len " + s.lenMin + ".." + s.lenMax);
        if (s.empty > 0) p.add("empty×" + s.empty);
        return String.join("; ", p);
    }

    static String when(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US);
        f.setTimeZone(zone);
        return f.format(new Date(ms));
    }
}
