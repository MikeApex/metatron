package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.mike.metatron.whatsapp.Gate.State;

import org.junit.Test;

/** The consent gate's reading of a /device/* reply (plan § 3.12, § 4.0). */
public class GateTest {
    @Test
    public void okOpensTheChannel() {
        for (State from : State.values()) assertEquals(State.OPEN, Gate.next(from, 200, ""));
    }

    @Test
    public void refusedPairingIsUnpaired() {
        for (State from : State.values()) assertEquals(State.UNPAIRED, Gate.next(from, 401, ""));
    }

    @Test
    public void onlyTheExactConsentedOffDetailUnlocksTheConsentedState() {
        assertEquals(State.CONSENTED_OFF, Gate.next(State.NO_CONSENT, 403, "consented_off"));
        assertEquals(State.CONSENTED_OFF, Gate.next(State.OPEN, 403, "consented_off"));
    }

    @Test
    public void everyOther403IsNoConsent() {
        // An older VM answers "channel_off" for every closed gate: it must fail closed (verify new 1).
        for (String detail : new String[] {"channel_off", "no_consent", "", "Consented_off",
                "consented_off ", " consented_off", "consented", "Not available to this account."}) {
            for (State from : State.values()) {
                assertEquals(detail, State.NO_CONSENT, Gate.next(from, 403, detail));
            }
        }
    }

    @Test
    public void anUnreadableTokenOrANonHttpsAddressIsUnpaired() {
        // F10: no silent failure — the listener goes off and the job is cancelled through apply.
        for (State from : State.values()) {
            assertEquals(State.UNPAIRED, Gate.next(from, DeviceApi.UNPAIRED, "unpaired"));
            assertEquals(State.UNPAIRED, Gate.next(from, DeviceApi.NOT_HTTPS, "not_https"));
        }
    }

    @Test
    public void networkAndServerErrorsChangeNothing() {
        int[] silent = {DeviceApi.NETWORK, 500, 502, 503, 404, 400, 413, 0};
        for (int status : silent) {
            for (State from : State.values()) {
                assertEquals("status " + status, from, Gate.next(from, status, "consented_off"));
            }
        }
    }

    @Test
    public void onceOpenedAnythingShortOfOpenCancelsTheJob() {
        assertTrue(Gate.shouldCancelJob(State.CONSENTED_OFF, true));
        assertTrue(Gate.shouldCancelJob(State.NO_CONSENT, true));
        assertTrue(Gate.shouldCancelJob(State.UNPAIRED, true));
        assertFalse(Gate.shouldCancelJob(State.OPEN, true));
    }

    @Test
    public void beforeTheFirstOpenOnlyConsentedOffKeepsAJobForTheDryRun() {
        assertFalse(Gate.shouldCancelJob(State.CONSENTED_OFF, false));
        assertFalse(Gate.shouldCancelJob(State.OPEN, false));
        assertTrue(Gate.shouldCancelJob(State.NO_CONSENT, false));
        assertTrue(Gate.shouldCancelJob(State.UNPAIRED, false));
    }
}
