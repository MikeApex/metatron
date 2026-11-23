package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * The work folder (build plan § 3.1): the kill test, the lease, and that a sweep never reaches the
 * key beside the folder or a link's target.
 */
public class WorkFolderTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private File noBackup, work, lock, keyDir, keyFile;
    private static final byte[] KEY_BYTES = "made-up-wrapped-key-bytes".getBytes(StandardCharsets.UTF_8);

    @Before
    public void layout() throws IOException {
        noBackup = tmp.newFolder("no_backup");
        work = new File(noBackup, "wa_work");
        lock = new File(noBackup, "wa_work.lock");
        keyDir = new File(noBackup, "wa_key");
        assertTrue(work.mkdirs() && keyDir.mkdirs());
        keyFile = new File(keyDir, "key.bin");
        write(keyFile, KEY_BYTES);
    }

    private static void write(File f, byte[] b) throws IOException {
        try (FileOutputStream out = new FileOutputStream(f)) {
            out.write(b);
        }
    }

    /** What a run killed after decrypt leaves: the copy, its side files, a .partial, and the unpredicted. */
    private void leaveAKilledRun() throws IOException {
        String db = "msgstore.db";
        for (String name : new String[]{db, db + "-journal", db + "-wal", db + "-shm", db + ".partial",
                "odd name (2).tmp~", ".hidden"}) {
            write(new File(work, name), new byte[4096]);
        }
        File nested = new File(work, "nested/deeper");
        assertTrue(nested.mkdirs());
        write(new File(nested, "left.bin"), new byte[16]);
        assertTrue(work.list().length >= 8);
    }

    private void assertKeyUntouched() throws IOException {
        assertTrue(keyFile.isFile());
        assertArrayEquals(KEY_BYTES, Files.readAllBytes(keyFile.toPath()));
    }

    @Test
    public void killTest_aFreshStartSweepsEverythingAndLeavesTheKey() throws IOException {
        leaveAKilledRun();
        // A fresh process: nothing in memory, just the folder as the killed run left it.
        assertTrue(WorkFolder.sweepIfIdle(work, lock));
        assertTrue(work.isDirectory());
        assertEquals(0, work.list().length);
        assertKeyUntouched();
        assertTrue(lock.isFile());   // the lock file lives beside the folder, not in it
        // And the sweep a run does under its lease.
        leaveAKilledRun();
        WorkFolder w = new WorkFolder(work, lock);
        try (WorkFolder.Lease lease = w.acquire()) {
            w.sweep(lease);
        }
        assertEquals(0, work.list().length);
        assertKeyUntouched();
    }

    @Test
    public void sweepIfIdleIsFalseWhileAnotherThreadHoldsTheLease() throws Exception {
        leaveAKilledRun();
        CountDownLatch held = new CountDownLatch(1), done = new CountDownLatch(1);
        AtomicReference<Throwable> err = new AtomicReference<>();
        Thread runner = new Thread(() -> {
            WorkFolder w = new WorkFolder(work, lock);
            try (WorkFolder.Lease lease = w.acquire()) {
                held.countDown();
                done.await(10, TimeUnit.SECONDS);
            } catch (Throwable t) {
                err.set(t);
            }
        });
        runner.start();
        assertTrue(held.await(10, TimeUnit.SECONDS));
        assertFalse(WorkFolder.sweepIfIdle(work, lock));
        assertNull(new WorkFolder(work, lock).tryAcquire());
        assertTrue("a busy folder is not swept", work.list().length >= 8);
        done.countDown();
        runner.join(10_000);
        assertNull(err.get());
        assertTrue(WorkFolder.sweepIfIdle(work, lock));
        assertEquals(0, work.list().length);
    }

    @Test
    public void acquireWaitsForTheHolder() throws Exception {
        WorkFolder w = new WorkFolder(work, lock);
        WorkFolder.Lease first = w.acquire();
        AtomicBoolean got = new AtomicBoolean();
        CountDownLatch acquired = new CountDownLatch(1);
        Thread t = new Thread(() -> {
            try (WorkFolder.Lease l = new WorkFolder(work, lock).acquire()) {
                got.set(true);
                acquired.countDown();
            }
        });
        t.start();
        assertFalse(acquired.await(300, TimeUnit.MILLISECONDS));
        first.close();
        assertTrue(acquired.await(10, TimeUnit.SECONDS));
        t.join(10_000);
        assertTrue(got.get());
    }

    @Test
    public void sweepRefusesWithoutALiveLeaseOfThisFolder() throws IOException {
        leaveAKilledRun();
        WorkFolder w = new WorkFolder(work, lock);
        try {
            w.sweep(null);
            fail("no lease");
        } catch (IllegalStateException expected) {
            // ok
        }
        WorkFolder.Lease lease = w.acquire();
        lease.close();
        lease.close();   // twice is harmless
        try {
            w.sweep(lease);
            fail("a closed lease");
        } catch (IllegalStateException expected) {
            // ok
        }
        File otherWork = new File(noBackup, "other_work"), otherLock = new File(noBackup, "other.lock");
        assertTrue(otherWork.mkdirs());
        WorkFolder other = new WorkFolder(otherWork, otherLock);
        try (WorkFolder.Lease l = other.acquire()) {
            w.sweep(l);
            fail("a lease of another folder");
        } catch (IllegalStateException expected) {
            // ok
        }
        assertTrue("nothing was swept by a refused call", work.list().length >= 8);
    }

    @Test
    public void theSameThreadCannotTakeTheLeaseTwice() {
        WorkFolder w = new WorkFolder(work, lock);
        try (WorkFolder.Lease l = w.acquire()) {
            assertNull(w.tryAcquire());
            assertNull(new WorkFolder(work, lock).tryAcquire());
            assertFalse(WorkFolder.sweepIfIdle(work, lock));
            try {
                w.acquire();
                fail("re-entry would deadlock on the file lock");
            } catch (IllegalStateException expected) {
                // ok
            }
        }
        WorkFolder.Lease again = w.tryAcquire();
        assertNotNull(again);
        again.close();
    }

    @Test
    public void aLinkInsideTheFolderIsRemovedNotFollowed() throws IOException {
        File link = new File(work, "to_key");
        try {
            Files.createSymbolicLink(link.toPath(), keyDir.toPath());
        } catch (UnsupportedOperationException | IOException e) {
            return;   // no symlinks on this file system: nothing to test
        }
        assertTrue(WorkFolder.sweepIfIdle(work, lock));
        assertEquals(0, work.list().length);
        assertKeyUntouched();
    }

    @Test
    public void theLockFileMayNotLiveInTheFolder() {
        try {
            new WorkFolder(work, new File(work, "lock"));
            fail("the sweep would delete its own lock");
        } catch (IllegalArgumentException expected) {
            // ok
        }
    }

    @Test
    public void aMissingFolderIsCreatedBySweep() {
        assertTrue(work.delete());
        assertTrue(WorkFolder.sweepIfIdle(work, lock));
        assertTrue(work.isDirectory());
    }
}
