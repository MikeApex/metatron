package com.mike.metatron.whatsapp;

import android.content.Context;
import android.os.Environment;

import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.BooleanSupplier;

/**
 * The one owner of the decrypt in the app (plan § 3.1): every read of a WhatsApp backup — the
 * nightly job's, the dry run's and the share-list screen's on-demand chat list — goes through
 * here, and nothing else calls {@link BackupDecryptor#decrypt}.
 *
 * <p>One read, under the {@link WorkFolder} lease (one at a time, across threads and processes):
 * sweep the whole work folder → locate the live set → refuse it while WhatsApp may be writing it
 * → load the key → decrypt the full backup <b>into the work folder only</b> → read its messages
 * since a whole second (schema-checked) and its chat list → delete the decrypted copy → read each
 * increment → fold the chat list and combine. <b>The decrypted copy and its side files are deleted
 * in {@code finally}, the work folder is swept again, and the key is destroyed in {@code
 * finally}</b> — whatever happened.
 *
 * <p>Where the read starts: the VM's cursor minus {@value #OVERLAP_DAYS} days (decision 2), or,
 * with no cursor (a first read, or the dry run), now minus {@value #FIRST_READ_DAYS} days (W6).
 *
 * <p>Everything here is plain Java behind {@link Env}, so the kill path, the overlap and the
 * canonical allowlist are unit-tested on the JVM; {@link #androidEnv} is the thin Android half. The folded
 * chat list of the last read is kept <b>in memory only</b>, for this process's life, never on disk.
 * Nothing here logs, and no exception's message leaves it: a failed read is a code.
 */
public final class NightlyRead {
    public static final int OVERLAP_DAYS = 8;
    public static final int FIRST_READ_DAYS = 90;
    static final long OVERLAP_SECONDS = OVERLAP_DAYS * 24L * 3600;
    static final long FIRST_READ_SECONDS = FIRST_READ_DAYS * 24L * 3600;

    /** No key is stored, or the stored one cannot be opened: the user enters it again. */
    public static final String NO_KEY = "no_key";
    /** All-files access is not held, so WhatsApp's folder cannot be read. */
    public static final String NO_ACCESS = "no_access";

    /** The decrypted full backup's name inside the work folder. */
    static final String DB_NAME = "base.db";

    /** The folded chat list of the last read in this process. Memory only — never written to disk. */
    private static volatile ChatList lastChats;

    private NightlyRead() {}

    /** Everything a read touches outside plain Java. The real one is {@link #androidEnv}. */
    interface Env {
        File backupDir();

        File workDir();

        File workLock();

        /** Whether WhatsApp's folder may be read at all (All-files access). */
        boolean storageGranted();

        /** The derived backup key, or null when none is stored. */
        BackupKey loadKey() throws Exception;

        BackupLocator.Clock clock();

        BackupLocator.Sleeper sleeper();

        void decrypt(File backup, BackupKey key, File destination) throws BackupException, IOException;

        Base readBase(File database, long sinceSeconds) throws BackupException;

        ChatList readChats(File database) throws BackupException;

        Increment readIncrement(File file, long number, BackupKey key) throws BackupException, IOException;

        /** Checked between steps: a cancelled read stops at the next one, its finally still runs. */
        boolean cancelled();
    }

    /** What the full backup gave: its messages since the since-second, its jid tables, its uncounted rows. */
    static final class Base {
        final List<WaMessage> messages;
        final BackupCombiner.JidTables tables;
        final int withoutKeyId, withoutChat;

        Base(List<WaMessage> messages, BackupCombiner.JidTables tables, int withoutKeyId, int withoutChat) {
            this.messages = messages;
            this.tables = tables;
            this.withoutKeyId = withoutKeyId;
            this.withoutChat = withoutChat;
        }
    }

    /** One read's outcome. {@link #toString()} carries counts and the code only. */
    public static final class Result {
        /** "" when the read succeeded; else a {@link BackupError#code}, {@link RunReport#IO_ERROR}, {@link #NO_KEY} or {@link #NO_ACCESS}. */
        public final String error;
        /** Stopped at a cancel check; nothing to report. */
        public final boolean cancelled;
        /** The combined messages of the allowed chats (allowlist made canonical in tonight's tables); null unless ok. */
        public final BackupCombiner.Combined combined;
        /** The chat list folded through the set's increments; null unless ok. */
        public final ChatList chats;
        /** Tonight's hidden id → canonical id, for every hidden id the folded tables link; empty unless ok. */
        public final Map<String, String> hiddenToCanonical;
        /** The whole second the read started from. */
        public final long sinceSeconds;

        private Result(String error, boolean cancelled, BackupCombiner.Combined combined, ChatList chats,
                       Map<String, String> hiddenToCanonical, long sinceSeconds) {
            this.error = error;
            this.cancelled = cancelled;
            this.combined = combined;
            this.chats = chats;
            this.hiddenToCanonical = hiddenToCanonical;
            this.sinceSeconds = sinceSeconds;
        }

        public boolean ok() {
            return error.isEmpty() && !cancelled;
        }

        static Result failed(String code, long since) {
            return new Result(code, false, null, null, Collections.<String, String>emptyMap(), since);
        }

        static Result stopped(long since) {
            return new Result("", true, null, null, Collections.<String, String>emptyMap(), since);
        }

        @Override
        public String toString() {
            return "NightlyRead.Result(" + (cancelled ? "cancelled" : error.isEmpty() ? "ok" : error)
                    + (combined == null ? "" : ", " + combined.messages.size() + " messages") + ")";
        }
    }

    /** A cancel check fired. Internal: never leaves this class. */
    private static final class Cancelled extends Exception {}

    // ---- plain Java, unit-tested -------------------------------------------------------------

    /** The whole second a read starts from: cursor − 8 days, or now − 90 days with no cursor. */
    static long since(Long cursorSeconds, long nowMs) {
        if (cursorSeconds != null) return Math.max(0, cursorSeconds - OVERLAP_SECONDS);
        return Math.max(0, nowMs / 1000 - FIRST_READ_SECONDS);
    }

    /**
     * One full read. Fills the report's read counts — received rows read across <b>all</b> chats and
     * how many had text, per source; rows without a key id or a chat; undecodable texts; base key
     * collisions; deletions listed; when WhatsApp wrote the set and its full backup. Never throws.
     *
     * @param cursorSeconds the VM's cursor; null for a first read or the dry run (now − 90 days)
     * @param allowlist     the shared canonical chat ids
     */
    static Result run(Env env, Long cursorSeconds, Set<String> allowlist, long nowMs, RunReport report) {
        final long since = since(cursorSeconds, nowMs);
        try {
            return underLease(env, since, () -> fullRead(env, since, allowlist, report));
        } catch (Cancelled e) {
            return Result.stopped(since);
        } catch (Refusal e) {
            return Result.failed(e.code, since);
        }
    }

    /**
     * The chat list folded through the set's increments, for the share-list screen when no nightly
     * read has run in this process. Null when it cannot be read for a reason other than a named
     * refusal (no key, no access, an I/O failure, cancelled).
     */
    static ChatList readChatList(Env env) throws BackupException {
        try {
            return underLease(env, 0, () -> {
                ChatList held = lastChats;
                if (held != null) return held; // a read finished while this one waited for the lease
                return chatsOnly(env);
            });
        } catch (Cancelled e) {
            return null;
        } catch (Refusal e) {
            if (e.backup != null) throw e.backup;
            return null;
        }
    }

    /** A failed step, as its code (and the refusal itself when it is a named {@link BackupException}). */
    private static final class Refusal extends Exception {
        final String code;
        final BackupException backup;

        Refusal(String code, BackupException backup) {
            this.code = code;
            this.backup = backup;
        }
    }

    private interface Step<T> {
        T run() throws BackupException, IOException, InterruptedException, Cancelled, Refusal;
    }

    /** Takes the lease, sweeps, runs {@code step}, sweeps again; every failure becomes a {@link Refusal}. */
    private static <T> T underLease(Env env, long since, Step<T> step) throws Cancelled, Refusal {
        if (!env.storageGranted()) throw new Refusal(NO_ACCESS, null);
        WorkFolder folder;
        WorkFolder.Lease lease;
        try {
            folder = new WorkFolder(env.workDir(), env.workLock());
            lease = folder.acquire();
        } catch (RuntimeException e) {
            throw new Refusal(RunReport.IO_ERROR, null);
        }
        try {
            folder.sweep(lease);
            if (env.cancelled()) throw new Cancelled();
            return step.run();
        } catch (BackupException e) {
            throw new Refusal(e.error.code, e);
        } catch (IOException | UncheckedIOException e) {
            throw new Refusal(RunReport.IO_ERROR, null);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new Cancelled();
        } finally {
            try {
                folder.sweep(lease);
            } catch (RuntimeException ignored) {
                // Left for the next sweep, which refuses its run if the folder still cannot be emptied.
            }
            lease.close();
        }
    }

    private static Result fullRead(Env env, long since, Set<String> allowlist, RunReport report)
            throws BackupException, IOException, InterruptedException, Cancelled, Refusal {
        IncrementSet set = IncrementSet.locate(env.backupDir());
        report.backupWritten = set.newestWriteMs() / 1000;
        report.fullBackupWritten = set.base.lastModified() / 1000;
        set.requireComplete(env.clock(), env.sleeper());
        check(env);

        File db = new File(env.workDir(), DB_NAME);
        BackupKey key = null;
        try {
            key = key(env);
            check(env);
            env.decrypt(set.base, key, db);
            check(env);
            Base base = env.readBase(db, since);
            ChatList chats = env.readChats(db);
            BackupDecryptor.deleteDecrypted(db); // as soon as it has been read
            List<Increment> increments = increments(env, set, key);
            key.destroy();

            ChatList folded = chats.fold(increments);
            // The combine canonicalises before it filters, so the allowlist must be canonical too: a
            // chat shared under its hidden id whose link is in tonight's tables — new tonight or
            // already in the full backup — has its messages under the phone-number id, which the
            // share list learns only in tonight's post (F1). Read them now rather than drop them.
            Map<String, String> links = hiddenToCanonical(folded.jids);
            Set<String> canonical = canonicalAllowlist(allowlist, links);
            BackupCombiner.Combined combined = BackupCombiner.combine(base.messages, base.tables, increments, canonical, since);
            count(report, base, increments, combined);
            lastChats = folded;
            return new Result("", false, combined, folded, links, since);
        } finally {
            BackupDecryptor.deleteDecrypted(db);
            if (key != null) key.destroy();
        }
    }

    private static ChatList chatsOnly(Env env)
            throws BackupException, IOException, InterruptedException, Cancelled, Refusal {
        IncrementSet set = IncrementSet.locate(env.backupDir());
        set.requireComplete(env.clock(), env.sleeper());
        check(env);
        File db = new File(env.workDir(), DB_NAME);
        BackupKey key = null;
        try {
            key = key(env);
            check(env);
            env.decrypt(set.base, key, db);
            check(env);
            ChatList chats = env.readChats(db);
            BackupDecryptor.deleteDecrypted(db);
            List<Increment> increments = increments(env, set, key);
            ChatList folded = chats.fold(increments);
            lastChats = folded;
            return folded;
        } finally {
            BackupDecryptor.deleteDecrypted(db);
            if (key != null) key.destroy();
        }
    }

    private static BackupKey key(Env env) throws Refusal {
        BackupKey key;
        try {
            key = env.loadKey();
        } catch (Exception e) {
            throw new Refusal(NO_KEY, null);
        }
        if (key == null) throw new Refusal(NO_KEY, null);
        return key;
    }

    private static List<Increment> increments(Env env, IncrementSet set, BackupKey key)
            throws BackupException, IOException, Cancelled {
        List<Increment> out = new ArrayList<>();
        for (File f : set.increments) {
            check(env);
            out.add(env.readIncrement(f, IncrementSet.number(f), key));
        }
        return out;
    }

    private static void check(Env env) throws Cancelled {
        if (env.cancelled()) throw new Cancelled();
    }

    /**
     * The allowlist plus the canonical id, in tonight's folded tables, of every allowed id those
     * tables link ({@code hiddenToCanonical}). The same set when nothing is added.
     */
    static Set<String> canonicalAllowlist(Set<String> allowlist, Map<String, String> hiddenToCanonical) {
        Set<String> out = null;
        for (String id : allowlist) {
            String c = hiddenToCanonical.get(id);
            if (c != null && !allowlist.contains(c)) {
                if (out == null) out = new HashSet<>(allowlist);
                out.add(c);
            }
        }
        return out == null ? allowlist : out;
    }

    /** Every hidden id the tables link, → its canonical id. Sorted, so the same tables give the same map. */
    static Map<String, String> hiddenToCanonical(BackupCombiner.JidTables tables) {
        BackupCombiner.Canon canon = new BackupCombiner.Canon(tables);
        Map<String, String> out = new TreeMap<>();
        for (String raw : tables.raw.values()) {
            if (!raw.endsWith("@lid")) continue;
            String c = canon.of(raw);
            if (!c.equals(raw)) out.put(raw, c);
        }
        return Collections.unmodifiableMap(out);
    }

    /** The read's counts, across all chats — the allowlist plays no part in them. */
    static void count(RunReport r, Base base, List<Increment> increments, BackupCombiner.Combined combined) {
        long received = 0, text = 0;
        for (WaMessage m : base.messages) {
            if (m.fromMe) continue;
            received++;
            if (m.text != null && !m.text.isEmpty()) text++;
        }
        r.baseReceived = received;
        r.baseReceivedText = text;
        received = 0;
        text = 0;
        long undecodable = 0;
        for (Increment inc : increments) {
            undecodable += inc.textUndecodable;
            for (WaMessage m : inc.messages) {
                if (m.fromMe) continue;
                received++;
                if (m.text != null && !m.text.isEmpty()) text++;
            }
        }
        r.incReceived = received;
        r.incReceivedText = text;
        r.withoutKeyId = base.withoutKeyId;
        r.withoutChat = base.withoutChat;
        r.textUndecodable = undecodable;
        r.baseKeyCollisions = combined.baseKeyCollisions;
        r.deletionsListed = combined.deletionsListed;
    }

    /** Forgets the in-memory chat list — "Turn off", and tests. */
    static void forgetChatList() {
        lastChats = null;
    }

    // ---- on the phone --------------------------------------------------------------------------

    /**
     * The chat list from the last read in this process, folded through its increments (§ 3.9) —
     * held in memory only, never written to disk. When there is none and {@code readIfNone}, an
     * on-demand read under the work-folder lock (decrypt, read the chat list, delete the copy,
     * destroy the key — all in finally). Blocking: never on the main thread. Null when there is
     * none and no read was allowed — and also when the on-demand read could not run for a reason
     * that is not a named refusal: no key stored, no All-files access, an I/O failure.
     */
    public static ChatList chatList(Context ctx, boolean readIfNone) throws BackupException {
        ChatList held = lastChats;
        if (held != null || !readIfNone) return held;
        return readChatList(androidEnv(ctx.getApplicationContext(), () -> false));
    }

    /** The real reader: WhatsApp's folder on shared storage, the key from the Keystore, SQLite. */
    static Env androidEnv(final Context ctx, final BooleanSupplier cancelled) {
        return new Env() {
            @Override public File backupDir() {
                return new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
            }
            @Override public File workDir() { return WaFiles.workDir(ctx); }
            @Override public File workLock() { return WaFiles.workLock(ctx); }
            @Override public boolean storageGranted() { return WhatsAppActivity.allFilesGranted(ctx); }
            @Override public BackupKey loadKey() throws Exception { return KeyVault.loadKey(ctx); }
            @Override public BackupLocator.Clock clock() { return BackupLocator.SYSTEM_CLOCK; }
            @Override public BackupLocator.Sleeper sleeper() { return BackupLocator.THREAD_SLEEP; }
            @Override public void decrypt(File backup, BackupKey key, File destination) throws BackupException, IOException {
                BackupDecryptor.decrypt(backup, key, destination, BackupDecryptor.FILESYSTEM);
            }
            @Override public Base readBase(File database, long sinceSeconds) throws BackupException {
                FullBackupMessages f = FullBackupMessages.read(database, sinceSeconds);
                return new Base(f.messages, f.tables, f.withoutKeyId, f.withoutChat);
            }
            @Override public ChatList readChats(File database) throws BackupException {
                return ChatList.read(database);
            }
            @Override public Increment readIncrement(File file, long number, BackupKey key) throws BackupException, IOException {
                return IncrementReader.read(file, number, key);
            }
            @Override public boolean cancelled() { return cancelled.getAsBoolean(); }
        };
    }
}
