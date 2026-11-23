package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.mike.metatron.whatsapp.Notices.Ledger;
import com.mike.metatron.whatsapp.Notices.Notice;

import java.util.EnumSet;

import org.junit.Test;

/** Once per onset, and the link states never notify (plan § 3.6, decision 3). */
public class NoticesTest {
    @Test
    public void raisingTwicePostsOnce() {
        Ledger l = new Ledger(EnumSet.noneOf(Notice.class));
        assertTrue(l.raise(Notice.BACKUP_STALE));
        assertFalse(l.raise(Notice.BACKUP_STALE));
        assertEquals(EnumSet.of(Notice.BACKUP_STALE), l.active());
    }

    @Test
    public void clearedThenRaisedPostsAgain() {
        Ledger l = new Ledger(EnumSet.noneOf(Notice.class));
        assertTrue(l.raise(Notice.READ_REFUSED));
        assertTrue(l.clear(Notice.READ_REFUSED));
        assertFalse(l.clear(Notice.READ_REFUSED));
        assertTrue(l.raise(Notice.READ_REFUSED));
    }

    @Test
    public void linkStatesAreRecordedButNeverPost() {
        Ledger l = new Ledger(EnumSet.noneOf(Notice.class));
        assertFalse(l.raise(Notice.LINK_OFF));
        assertFalse(l.raise(Notice.NEEDS_CONSENT));
        assertTrue(l.active().contains(Notice.LINK_OFF));
        assertTrue(l.active().contains(Notice.NEEDS_CONSENT));
        l.clear(Notice.LINK_OFF);
        assertFalse(l.raise(Notice.LINK_OFF));
    }

    @Test
    public void everyOtherNoticePostsOnOnset() {
        for (Notice n : Notice.values()) {
            boolean linkState = n == Notice.LINK_OFF || n == Notice.NEEDS_CONSENT;
            assertEquals(n.name(), !linkState, new Ledger(EnumSet.noneOf(Notice.class)).raise(n));
        }
    }

    @Test
    public void onsetSurvivesBeingStoredAndRead() {
        Ledger l = new Ledger(EnumSet.noneOf(Notice.class));
        l.raise(Notice.TEXT_GONE);
        l.raise(Notice.REPAIR_NEEDED);
        Ledger back = Ledger.decode(l.encode());
        assertEquals(l.active(), back.active());
        assertFalse("already active after a restart: no second post", back.raise(Notice.TEXT_GONE));
        assertTrue(back.raise(Notice.SHARE_OUT_OF_STEP));
    }

    @Test
    public void unreadableStoreIsEmptyNotACrash() {
        assertTrue(Ledger.decode("").active().isEmpty());
        assertTrue(Ledger.decode(null).active().isEmpty());
        assertEquals(EnumSet.of(Notice.TEXT_GONE), Ledger.decode("SOMETHING_OLD,,TEXT_GONE").active());
    }

    @Test
    public void everyNoticeHasCodeWrittenWords() {
        for (Notice n : Notice.values()) {
            assertFalse(n.name(), Notices.title(n).isEmpty());
            assertFalse(n.name(), Notices.text(n).isEmpty());
        }
    }
}
