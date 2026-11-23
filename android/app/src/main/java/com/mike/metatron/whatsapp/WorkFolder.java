package com.mike.metatron.whatsapp;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.io.UncheckedIOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.locks.ReentrantLock;

/**
 * The nightly read's work folder and its lock (build plan § 3.1). Plain Java against a directory,
 * so the kill test runs on the JVM.
 *
 * <ul>
 * <li><b>One run at a time:</b> a {@link Lease} holds a process-wide {@link ReentrantLock} for the
 *     canonical lock-file path <i>and</i> a {@link FileChannel} lock on that file. The first stops a
 *     second thread of this process (the JVM refuses an overlapping file lock from the same process
 *     rather than waiting); the second stops another process.</li>
 * <li><b>The sweep deletes every file in the folder, any name, recursively</b> — the decrypted copy,
 *     its SQLite side files, a {@code .partial}, and anything nobody predicted. It runs at process
 *     start ({@link #sweepIfIdle}) and at the start of each run, under the lease. Never from a
 *     screen.</li>
 * <li><b>The key never lives here</b> — it is in {@code no_backup/wa_key/}, a sibling — so no sweep
 *     can take it. A symbolic link inside the folder is removed as a link; its target, wherever it
 *     is, is never followed.</li>
 * </ul>
 *
 * A {@code Lease} must be closed on the thread that acquired it ({@link ReentrantLock} is owned by
 * a thread). I/O failures surface as {@link UncheckedIOException}, carrying no file content.
 */
public final class WorkFolder {
    /** Process-wide: one {@link ReentrantLock} per canonical lock-file path. */
    private static final Map<String, ReentrantLock> LOCKS = new HashMap<>();

    private final File workDir;
    private final File lockFile;
    private final String workPath;
    private final String lockPath;
    private final ReentrantLock processLock;

    public WorkFolder(File workDir, File lockFile) {
        this.workDir = canonical(workDir);
        this.lockFile = canonical(lockFile);
        this.workPath = this.workDir.getPath();
        this.lockPath = this.lockFile.getPath();
        if (lockPath.equals(workPath) || lockPath.startsWith(workPath + File.separator)) {
            // The sweep would delete the lock file out from under its own lock.
            throw new IllegalArgumentException("the lock file must not be inside the work folder");
        }
        synchronized (LOCKS) {
            ReentrantLock l = LOCKS.get(lockPath);
            if (l == null) {
                l = new ReentrantLock();
                LOCKS.put(lockPath, l);
            }
            this.processLock = l;
        }
    }

    public File dir() {
        return workDir;
    }

    /** Held by one run: both locks. Closing releases both; closing twice is harmless. */
    public final class Lease implements AutoCloseable {
        private final RandomAccessFile file;
        private final FileLock fileLock;
        private boolean closed;

        private Lease(RandomAccessFile file, FileLock fileLock) {
            this.file = file;
            this.fileLock = fileLock;
        }

        WorkFolder folder() {
            return WorkFolder.this;
        }

        public synchronized boolean isLive() {
            return !closed;
        }

        @Override
        public synchronized void close() {
            if (closed) return;
            closed = true;
            try {
                fileLock.release();
            } catch (IOException ignored) {
                // Closing the channel below releases it as well.
            } finally {
                try {
                    file.close();
                } catch (IOException ignored) {
                    // Nothing left to release.
                } finally {
                    processLock.unlock();
                }
            }
        }
    }

    /** Waits for both locks. A thread that already holds this folder's lease is refused, not deadlocked. */
    public Lease acquire() {
        if (processLock.isHeldByCurrentThread()) throw new IllegalStateException("this thread already holds the work folder");
        processLock.lock();
        boolean ok = false;
        try {
            RandomAccessFile f = openLockFile();
            try {
                FileLock fl = f.getChannel().lock();
                Lease lease = new Lease(f, fl);
                ok = true;
                return lease;
            } finally {
                if (!ok) closeQuietly(f);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } finally {
            if (!ok) processLock.unlock();
        }
    }

    /** Both locks if both are free at once, else null. Never waits. */
    public Lease tryAcquire() {
        if (processLock.isHeldByCurrentThread() || !processLock.tryLock()) return null;
        boolean ok = false;
        try {
            RandomAccessFile f = openLockFile();
            try {
                FileLock fl;
                try {
                    fl = f.getChannel().tryLock();
                } catch (OverlappingFileLockException e) {
                    fl = null;   // this process holds it through another path
                }
                if (fl == null) return null;
                Lease lease = new Lease(f, fl);
                ok = true;
                return lease;
            } finally {
                if (!ok) closeQuietly(f);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } finally {
            if (!ok) processLock.unlock();
        }
    }

    /**
     * Deletes every file and folder inside {@link #dir()}, keeping the folder itself.
     *
     * @throws IllegalStateException without a live lease of this folder
     * @throws UncheckedIOException  if anything is left behind — a decrypted copy that cannot be
     *                               removed is a fault the run must not continue past
     */
    public void sweep(Lease lease) {
        if (lease == null || !lease.isLive() || !sameFolder(lease.folder())) {
            throw new IllegalStateException("sweep needs a live lease of this work folder");
        }
        if (!workDir.exists() && !workDir.mkdirs()) {
            throw new UncheckedIOException(new IOException("work folder cannot be created"));
        }
        if (!workDir.isDirectory()) throw new UncheckedIOException(new IOException("work folder is not a folder"));
        deleteChildren(workDir);
        String[] left = workDir.list();
        if (left == null || left.length != 0) {
            throw new UncheckedIOException(new IOException("work folder not empty after sweep"));
        }
    }

    /**
     * The start-up sweep: {@link #tryAcquire} → {@link #sweep} → release. Never throws — it runs from
     * {@code Application.onCreate}. True only when the folder was swept clean; false when a run holds
     * it, or something could not be removed (the next sweep, under the run's lease, tries again and
     * refuses the run if it still cannot).
     */
    public static boolean sweepIfIdle(File workDir, File lockFile) {
        try {
            WorkFolder w = new WorkFolder(workDir, lockFile);
            Lease lease = w.tryAcquire();
            if (lease == null) return false;
            try {
                w.sweep(lease);
                return true;
            } finally {
                lease.close();
            }
        } catch (RuntimeException e) {
            return false;
        }
    }

    private boolean sameFolder(WorkFolder other) {
        return other == this || (other.workPath.equals(workPath) && other.lockPath.equals(lockPath));
    }

    private RandomAccessFile openLockFile() throws IOException {
        File parent = lockFile.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs() && !parent.isDirectory()) {
            throw new IOException("lock folder cannot be created");
        }
        return new RandomAccessFile(lockFile, "rw");
    }

    /** Depth first. A link is deleted as a link: its child is compared by canonical path, never followed. */
    private static void deleteChildren(File dir) {
        String[] names = dir.list();
        if (names == null) return;
        for (String name : names) {
            File child = new File(dir, name);
            if (child.isDirectory() && !isLink(child)) deleteChildren(child);
            child.delete();
        }
    }

    private static boolean isLink(File f) {
        try {
            // dir is canonical, so a plain child's canonical form is itself; a link's is its target.
            return !f.getCanonicalFile().equals(f.getAbsoluteFile());
        } catch (IOException e) {
            return true;   // unknown: treat as a link, so it is removed but never descended into
        }
    }

    private static File canonical(File f) {
        try {
            return f.getCanonicalFile();
        } catch (IOException e) {
            return f.getAbsoluteFile();
        }
    }

    private static void closeQuietly(RandomAccessFile f) {
        try {
            f.close();
        } catch (IOException ignored) {
            // Nothing to release.
        }
    }
}
