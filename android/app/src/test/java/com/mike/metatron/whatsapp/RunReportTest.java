package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.ArrayList;
import java.util.Map;

import org.junit.Test;

/** The night's counts: exactly the VM's key set, a strict reader, and codes only. */
public class RunReportTest {
    private static RunReport sample() {
        RunReport r = new RunReport();
        r.runAt = 1_700_000_000L;
        r.dryRun = 1;
        r.backupWritten = 1_699_990_000L;
        r.fullBackupWritten = 1_699_500_000L;
        long n = 1;
        r.baseReceived = n++; r.baseReceivedText = n++; r.incReceived = n++; r.incReceivedText = n++;
        r.withoutKeyId = n++; r.withoutChat = n++; r.textUndecodable = n++; r.baseKeyCollisions = n++;
        r.deletionsListed = n++; r.postedMessages = n++; r.postedUpdates = n++; r.postedReplyMarkers = n++;
        r.skippedUnchanged = n++; r.rejected = n++; r.droppedNotShared = n++; r.sameSecondGroups = n;
        r.error = BackupError.BEING_WRITTEN.code;
        return r;
    }

    @Test
    @SuppressWarnings("unchecked")
    public void toJsonHasExactlyTheKeysInOrder() throws Exception {
        Map<String, Object> m = (Map<String, Object>) Json.parse(sample().toJson());
        assertEquals(RunReport.KEYS, new ArrayList<>(m.keySet()));
        assertEquals(22, m.size());
        assertEquals(1L, m.get("v"));
        assertEquals(1L, m.get("dry_run"));
        assertEquals(16L, m.get("same_second_groups"));
        assertEquals("being_written", m.get("error"));
        // A fresh report: every number 0, v 1, error "".
        Map<String, Object> fresh = (Map<String, Object>) Json.parse(new RunReport().toJson());
        assertEquals(RunReport.KEYS, new ArrayList<>(fresh.keySet()));
        assertEquals("", fresh.get("error"));
        assertEquals(0L, fresh.get("run_at"));
    }

    @Test
    public void roundTrips() {
        RunReport a = sample();
        RunReport b = RunReport.fromJson(a.toJson());
        assertNotNull(b);
        assertEquals(a.toJson(), b.toJson());
        assertEquals(16L, b.sameSecondGroups);
        assertEquals("being_written", b.error);
        RunReport c = RunReport.fromJson(new RunReport().toJson());
        assertNotNull(c);
        assertEquals("", c.error);
        for (String code : new String[]{RunReport.IO_ERROR, RunReport.SHARE_OUT_OF_STEP, RunReport.POST_FAILED}) {
            RunReport r = new RunReport();
            r.error = code;
            assertEquals(code, RunReport.fromJson(r.toJson()).error);
        }
        for (BackupError e : BackupError.values()) assertTrue(e.code, RunReport.isCode(e.code));
    }

    @Test
    public void malformedOrWrongTypedInputIsNull() {
        String good = sample().toJson();
        String[] bad = {
                null, "", "not json", "[]", "1", "\"s\"", "{}", good + "x", good.substring(0, good.length() - 1),
                good.replace("\"v\":1", "\"v\":2"),                       // wrong version
                good.replace("\"dry_run\":1", "\"dry_run\":2"),           // not 0/1
                good.replace("\"rejected\":14", "\"rejected\":-1"),       // negative
                good.replace("\"rejected\":14", "\"rejected\":1.5"),      // not an integer
                good.replace("\"rejected\":14", "\"rejected\":\"14\""),   // a string
                good.replace("\"rejected\":14", "\"rejected\":null"),     // null
                good.replace("\"rejected\":14", "\"rejected\":true"),     // boolean
                good.replace("\"error\":\"being_written\"", "\"error\":3"),
                good.replace("\"error\":\"being_written\"", "\"error\":\"Free text here\""),
                good.replace(",\"same_second_groups\":16", ""),           // a key missing
                good.replace("{\"v\":1", "{\"v\":1,\"extra\":0"),         // a key too many
                good.replace("\"run_at\"", "\"runAt\""),                  // the Java name, not the JSON key
        };
        for (String s : bad) assertNull(s, RunReport.fromJson(s));
    }

    @Test
    public void freeTextInErrorNeverLeaves() {
        String planted = "planted-secret-wording-91";
        RunReport r = new RunReport();
        r.error = planted;
        try {
            r.toJson();
            fail("a non-code error must be refused");
        } catch (IllegalStateException expected) {
            assertTrue(!String.valueOf(expected).contains(planted));
        }
        assertTrue(!r.toString().contains(planted));
        r.error = "Being_Written";   // uppercase is not a code shape
        assertTrue(!RunReport.isCode(r.error));
        r.error = null;
        assertTrue(!RunReport.isCode(r.error));
    }
}
