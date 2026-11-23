package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.junit.Test;

/** The platform-free JSON writer: escaping, and that what it writes {@link Json} reads back. */
public class JsonOutTest {
    @Test
    public void escapesQuotesBackslashesAndControlCharacters() {
        assertEquals("\"a\\\"b\\\\c\"", JsonOut.quote("a\"b\\c"));
        assertEquals("\"\\n\\r\\t\\b\\f\"", JsonOut.quote("\n\r\t\b\f"));
        assertEquals("\"\\u0000\\u0001\\u001f\"", JsonOut.quote("\u0000\u0001\u001f"));
        assertEquals("\"\\u2028\\u2029\"", JsonOut.quote("\u2028\u2029"));
        assertEquals("null", JsonOut.quote(null));
        assertEquals("\"/ \u00e9\"", JsonOut.quote("/ \u00e9"));
    }

    @Test
    public void lonesurrogatesAreEscapedAndPairsKept() {
        String pair = new String(Character.toChars(0x1F600));
        assertEquals("\"" + pair + "\"", JsonOut.quote(pair));
        assertEquals("\"\\ud83dx\"", JsonOut.quote("\ud83dx"));      // high without low
        assertEquals("\"x\\ude00\"", JsonOut.quote("x\ude00"));      // low without high
        assertEquals("\"\\ude00\\ud83d\"", JsonOut.quote("\ude00\ud83d")); // reversed: both lone
        assertEquals("\"a\\ud83d\"", JsonOut.quote("a\ud83d"));      // high at the very end
        // Every lone surrogate escaped: the output has no unpaired surrogate left in it.
        String out = JsonOut.quote("\ud83d\ude00\ud83d \ude00");
        for (int i = 0; i < out.length(); i++) {
            char c = out.charAt(i);
            if (Character.isHighSurrogate(c)) assertTrue(Character.isLowSurrogate(out.charAt(++i)));
            else assertTrue(!Character.isLowSurrogate(c));
        }
    }

    @Test
    public void everyStringRoundTripsThroughJson() throws Exception {
        List<String> samples = Arrays.asList("", "plain", "q\"uo\\te", "\u0000\u0007\u001f\u007f",
                "\ud83d", "\ude00", "x\ud83d\ude00y", "\u2028", "tab\there", "\u00e9\u4e2d");
        for (String s : samples) {
            assertEquals(s, Json.parse(JsonOut.quote(s)));
        }
        StringBuilder all = new StringBuilder();
        for (char c = 0; c < 0x80; c++) all.append(c);
        all.append("\ud800\udfff\udbff");
        assertEquals(all.toString(), Json.parse(JsonOut.quote(all.toString())));
    }

    @Test
    @SuppressWarnings("unchecked")
    public void objectsAndArraysParse() throws Exception {
        String json = JsonOut.obj().put("s", "v\n").put("n", -42L).put("b", true).putNull("z")
                .put("a", JsonOut.arr().add("x").add(7).add(false).add(JsonOut.obj()).add(JsonOut.arr()).addRaw("{\"k\":1}"))
                .put("o", JsonOut.obj().put("inner", (String) null))
                .toString();
        Map<String, Object> m = (Map<String, Object>) Json.parse(json);
        assertEquals("v\n", m.get("s"));
        assertEquals(-42L, m.get("n"));
        assertEquals(Boolean.TRUE, m.get("b"));
        assertTrue(m.containsKey("z") && m.get("z") == null);
        List<Object> a = (List<Object>) m.get("a");
        assertEquals(6, a.size());
        assertEquals("x", a.get(0));
        assertEquals(7L, a.get(1));
        assertEquals(1L, ((Map<String, Object>) a.get(5)).get("k"));
        assertTrue(((Map<String, Object>) m.get("o")).containsKey("inner"));
        assertEquals("{}", JsonOut.obj().toString());
        assertEquals("[]", JsonOut.arr().toString());
    }

    @Test
    public void aRepeatedKeyIsRefused() {
        JsonOut.Obj o = JsonOut.obj().put("k", 1);
        try {
            o.put("k", 2);
            fail("a repeated key must be refused — Json refuses it on read");
        } catch (IllegalArgumentException expected) {
            // ok
        }
    }
}
