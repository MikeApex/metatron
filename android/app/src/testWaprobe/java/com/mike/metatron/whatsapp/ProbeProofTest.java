package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import org.junit.Test;

import java.util.Arrays;
import java.util.List;

/**
 * ProbeProof's comparisons on planted messages: the counts must be right and no planted value may
 * appear. Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.ProbeProofTest'
 */
public class ProbeProofTest {
    static final String ALICE = "447700900123@s.whatsapp.net", GROUP = "120363000000000001@g.us", BOB = "447700900222@s.whatsapp.net";

    @Test public void agreementAndVersusCountAndNeverShowAValue() {
        List<WaMessage> newest = Arrays.asList(
                new WaMessage(ALICE, "KEY1", false, 1_763_870_400_250L, null, "secret words one", 1),
                new WaMessage(GROUP, "KEY2", false, 1_763_870_401_000L, BOB, "secret words two", 2),
                new WaMessage(GROUP, "KEY3", true, 1_763_870_402_000L, null, null, 3));
        List<WaMessage> inc = Arrays.asList(
                new WaMessage(ALICE, "KEY1", false, 1_763_870_400_000L, null, "secret words one", 1),
                new WaMessage(GROUP, "KEY2", false, 1_763_870_401_000L, BOB, "secret words EDITED", 2),
                new WaMessage(ALICE, "KEY9", false, 1_763_870_409_000L, null, "secret not in newest", 9));
        String a = ProbeProof.agreement(inc, ProbeProof.index(newest));
        assertEquals("matched by (chat, from-me, key_id) 2 of 3; of those: time 2, group sender 1 of 1, "
                + "text equal 1 / differs 1 / both none 0, row id 2", a);
        String v = ProbeProof.versus(inc, newest, 1_763_870_401_500L);
        assertEquals("combined 3 vs newest 3 in the same window: in both 2 (text equal 1, differs 1), only combined 1, only newest 1"
                + "\n    only newest, by chat kind {g.us=1} in 1 chats; from me 1, with text 0, timed before the base was written 0", v);
        for (String leak : new String[]{"secret", "KEY", "447700900", "120363", "whatsapp.net"}) {
            assertFalse(leak, a.contains(leak) || v.contains(leak));
        }
    }
}
