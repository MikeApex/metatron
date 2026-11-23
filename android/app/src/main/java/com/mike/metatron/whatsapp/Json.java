package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * A small strict JSON reader for an increment's header and table entries (format description § 12).
 * Platform-free — Android's org.json is not available to JVM unit tests. Objects become
 * LinkedHashMap, arrays ArrayList, integers Long, other numbers Double, JSON null a Java null.
 * Anything that is not well-formed JSON throws {@link Malformed}; its message names a position,
 * never content.
 */
final class Json {
    static final int MAX_DEPTH = 64;

    static final class Malformed extends Exception {
        Malformed(String what, int at) {
            super(what + " at character " + at);
        }
    }

    private final String s;
    private int i;

    private Json(String s) {
        this.s = s;
    }

    static Object parse(String text) throws Malformed {
        Json p = new Json(text);
        p.ws();
        Object v = p.value(0);
        p.ws();
        if (p.i != p.s.length()) throw new Malformed("text after the value", p.i);
        return v;
    }

    private Object value(int depth) throws Malformed {
        if (depth > MAX_DEPTH) throw new Malformed("nested too deep", i);
        ws();
        if (i >= s.length()) throw new Malformed("unexpected end", i);
        char c = s.charAt(i);
        if (c == '{') {
            i++;
            Map<String, Object> m = new LinkedHashMap<>();
            ws();
            if (peek('}')) { i++; return m; }
            while (true) {
                ws();
                String k = string();
                ws();
                expect(':');
                if (m.containsKey(k)) throw new Malformed("duplicate key", i);
                m.put(k, value(depth + 1));
                ws();
                if (peek(',')) { i++; continue; }
                expect('}');
                return m;
            }
        }
        if (c == '[') {
            i++;
            List<Object> l = new ArrayList<>();
            ws();
            if (peek(']')) { i++; return l; }
            while (true) {
                l.add(value(depth + 1));
                ws();
                if (peek(',')) { i++; continue; }
                expect(']');
                return l;
            }
        }
        if (c == '"') return string();
        if (s.startsWith("true", i)) { i += 4; return Boolean.TRUE; }
        if (s.startsWith("false", i)) { i += 5; return Boolean.FALSE; }
        if (s.startsWith("null", i)) { i += 4; return null; }
        return number();
    }

    private Object number() throws Malformed {
        int start = i;
        if (peek('-')) i++;
        int digits = i;
        while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
        if (i == digits) throw new Malformed("unexpected character", start);
        boolean integer = true;
        if (peek('.')) {
            integer = false;
            i++;
            int f = i;
            while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            if (i == f) throw new Malformed("bad number", start);
        }
        if (peek('e') || peek('E')) {
            integer = false;
            i++;
            if (peek('+') || peek('-')) i++;
            int e = i;
            while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            if (i == e) throw new Malformed("bad number", start);
        }
        String n = s.substring(start, i);
        try {
            return integer ? (Object) Long.parseLong(n) : (Object) Double.parseDouble(n);
        } catch (NumberFormatException ex) {
            // An integer past 64 bits: kept as a double — no column this reader uses is that large.
            return Double.parseDouble(n);
        }
    }

    private String string() throws Malformed {
        expect('"');
        StringBuilder out = new StringBuilder();
        while (true) {
            if (i >= s.length()) throw new Malformed("unterminated string", i);
            char c = s.charAt(i++);
            if (c == '"') return out.toString();
            if (c < 0x20) throw new Malformed("control character in string", i - 1);
            if (c != '\\') { out.append(c); continue; }
            if (i >= s.length()) throw new Malformed("unterminated escape", i);
            char e = s.charAt(i++);
            switch (e) {
                case '"': out.append('"'); break;
                case '\\': out.append('\\'); break;
                case '/': out.append('/'); break;
                case 'b': out.append('\b'); break;
                case 'f': out.append('\f'); break;
                case 'n': out.append('\n'); break;
                case 'r': out.append('\r'); break;
                case 't': out.append('\t'); break;
                case 'u':
                    if (i + 4 > s.length()) throw new Malformed("short \\u escape", i);
                    try {
                        out.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                    } catch (NumberFormatException ex) {
                        throw new Malformed("bad \\u escape", i);
                    }
                    i += 4;
                    break;
                default:
                    throw new Malformed("bad escape", i - 1);
            }
        }
    }

    private void ws() {
        while (i < s.length()) {
            char c = s.charAt(i);
            if (c != ' ' && c != '\n' && c != '\r' && c != '\t') return;
            i++;
        }
    }

    private boolean peek(char c) {
        return i < s.length() && s.charAt(i) == c;
    }

    private void expect(char c) throws Malformed {
        if (!peek(c)) throw new Malformed("expected '" + c + "'", i);
        i++;
    }
}
