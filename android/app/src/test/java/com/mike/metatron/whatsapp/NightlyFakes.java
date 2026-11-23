package com.mike.metatron.whatsapp;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.function.BooleanSupplier;
import java.util.function.Function;

/**
 * Fakes for the nightly read, the poster and the run: a fake reader environment (real files for the
 * backup set and the work folder, a fake decrypt, made-up rows), a fake VM, a fake host. Every id,
 * label and text is made up.
 */
final class NightlyFakes {
    static final String HIDDEN = "made-up-hidden-1@lid";
    static final String PHONE = "made-up-phone-1@s.test";
    static final String GROUP = "made-up-group-1@g.us";
    static final String OTHER = "made-up-other-1@s.test";
    static final String MEMBER = "made-up-member-1@s.test";
    static final String LABEL = "made-up-label-kestrel";
    /** Planted texts: asserted never to appear in any report, file or toString. */
    static final String T1 = "planted-text-umber-otter-501";
    static final String T2 = "planted-text-saffron-wren-502";
    static final String T3 = "planted-text-teal-marten-503";

    private NightlyFakes() {}

    static BackupKey key() {
        byte[] root = new byte[32];
        Arrays.fill(root, (byte) 7);
        return BackupKey.fromRoot(root);
    }

    static boolean destroyed(BackupKey k) {
        for (byte b : k.aesKey()) if (b != 0) return false;
        return true;
    }

    static WaMessage received(String chat, long second, String text, long row) {
        return new WaMessage(chat, "made-up-key-" + row, false, second * 1000L, null, text, row, 0, null);
    }

    static WaMessage mine(String chat, long second, long row) {
        return new WaMessage(chat, "made-up-key-" + row, true, second * 1000L, null, null, row, 0, null);
    }

    static Increment inc(long n, List<WaMessage> messages, int undecodable, Increment.TableDelta... deltas) {
        Map<String, Increment.TableDelta> t = new LinkedHashMap<>();
        for (Increment.TableDelta d : deltas) t.put(d.table, d);
        return new Increment(n, 0, 0, 0, 0, new ArrayList<>(messages), new ArrayList<Long>(), t, undecodable);
    }

    /** A jid_map delta linking jid row {@code lid} to jid row {@code jid}. */
    static Increment.TableDelta link(long lid, long jid) {
        Map<String, Object> row = new HashMap<>();
        row.put("lid_row_id", lid);
        row.put("jid_row_id", jid);
        return new Increment.TableDelta("jid_map", "lid_row_id", new ArrayList<>(Collections.singletonList(row)),
                new ArrayList<Long>(), 0);
    }

    static ChatList emptyChats(BackupCombiner.JidTables t) {
        return new ChatList(t, new TreeMap<Long, ChatList.ChatRow>(), new TreeMap<Long, String>(),
                new TreeMap<Long, Long>(), new TreeMap<String, Long>());
    }

    static void touch(File f, long mtimeMs) throws IOException {
        f.getParentFile().mkdirs();
        try (FileOutputStream o = new FileOutputStream(f)) {
            o.write(new byte[] {1, 2, 3});
        }
        if (!f.setLastModified(mtimeMs)) throw new IOException("setLastModified");
    }

    static int count(File dir) {
        String[] k = dir.list();
        return k == null ? 0 : k.length;
    }

    /** The reader's environment: real files for the set and the work folder, the rest made up. */
    static final class FakeEnv implements NightlyRead.Env {
        final File backupDir, workDir, workLock;
        final List<String> log;
        long nowMs;
        boolean granted = true;
        BackupKey key = key();
        boolean keyMissing;
        List<WaMessage> baseMessages = new ArrayList<>();
        BackupCombiner.JidTables tables = new BackupCombiner.JidTables();
        int withoutKeyId, withoutChat;
        List<Increment> increments = new ArrayList<>();
        Long sinceSeen;
        int decrypts;
        int workFilesAtDecrypt = -1;
        File destinationSeen;
        Exception decryptThrows;
        BackupException readBaseThrows;
        BooleanSupplier cancelled = () -> false;
        /** Cancel after the decrypt has written its copy. */
        boolean cancelAfterDecrypt;
        private boolean decrypted;

        FakeEnv(File root, long nowMs, List<String> log) {
            this.backupDir = new File(root, "Databases");
            this.workDir = new File(root, "wa_work");
            this.workLock = new File(root, "wa_work.lock");
            this.nowMs = nowMs;
            this.log = log;
            workDir.mkdirs();
        }

        /** Writes the base and {@code increments.size()} increment files, written an hour ago. */
        FakeEnv files() throws IOException {
            touch(new File(backupDir, "msgstore.db.crypt15"), nowMs - 3_600_000L);
            for (int i = 1; i <= increments.size(); i++) {
                touch(new File(backupDir, "msgstore-increment-" + i + ".db.crypt15"), nowMs - 3_600_000L + i);
            }
            return this;
        }

        @Override public File backupDir() { return backupDir; }
        @Override public File workDir() { return workDir; }
        @Override public File workLock() { return workLock; }
        @Override public boolean storageGranted() { return granted; }
        @Override public BackupKey loadKey() { return keyMissing ? null : key; }
        @Override public BackupLocator.Clock clock() { return () -> nowMs; }
        @Override public BackupLocator.Sleeper sleeper() { return ms -> { }; }

        @Override
        public void decrypt(File backup, BackupKey k, File destination) throws BackupException, IOException {
            log.add("decrypt");
            decrypts++;
            workFilesAtDecrypt = count(workDir);
            destinationSeen = destination;
            write(destination);
            decrypted = true;
            if (decryptThrows != null) {
                // a half-written copy and its side files, as a crash mid-decrypt would leave
                write(new File(destination.getPath() + ".partial"));
                write(new File(destination.getPath() + "-journal"));
                if (decryptThrows instanceof BackupException) throw (BackupException) decryptThrows;
                throw (IOException) decryptThrows;
            }
        }

        @Override
        public NightlyRead.Base readBase(File database, long sinceSeconds) throws BackupException {
            sinceSeen = sinceSeconds;
            if (readBaseThrows != null) throw readBaseThrows;
            write(new File(database.getPath() + "-wal"));
            List<WaMessage> out = new ArrayList<>();
            for (WaMessage m : baseMessages) if (m.timeMs >= sinceSeconds * 1000L) out.add(m);
            return new NightlyRead.Base(out, tables, withoutKeyId, withoutChat);
        }

        @Override
        public ChatList readChats(File database) {
            return emptyChats(tables);
        }

        @Override
        public Increment readIncrement(File file, long number, BackupKey k) {
            log.add("increment " + number);
            return increments.get((int) number - 1);
        }

        @Override
        public boolean cancelled() {
            return (cancelAfterDecrypt && decrypted) || cancelled.getAsBoolean();
        }

        private static void write(File f) {
            try (FileOutputStream o = new FileOutputStream(f)) {
                o.write("SQLite format 3\0made-up".getBytes(StandardCharsets.US_ASCII));
            } catch (IOException e) {
                throw new AssertionError(e);
            }
        }
    }

    /** One recorded call to the fake VM. */
    static final class Call {
        final String method, path, body;
        final int timeout;

        Call(String method, String path, String body, int timeout) {
            this.method = method;
            this.path = path;
            this.body = body;
            this.timeout = timeout;
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> json() {
            try {
                return (Map<String, Object>) Json.parse(body);
            } catch (Json.Malformed e) {
                throw new AssertionError("body is not JSON");
            }
        }
    }

    /** The VM: replies from a handler; every call recorded, and its method + path appended to the log. */
    static final class FakeApi implements DeviceApi {
        final List<Call> calls = new ArrayList<>();
        final List<String> log;
        Function<Call, Result> handler;

        FakeApi(List<String> log, Function<Call, Result> handler) {
            this.log = log;
            this.handler = handler;
        }

        @Override
        public Result get(String path) {
            Call c = new Call("GET", path, null, 0);
            calls.add(c);
            log.add("GET " + path);
            return handler.apply(c);
        }

        @Override
        public Result post(String path, String jsonBody, int readTimeoutMs) {
            Call c = new Call("POST", path, jsonBody, readTimeoutMs);
            calls.add(c);
            log.add("POST " + path);
            return handler.apply(c);
        }

        List<Call> posts(String path) {
            List<Call> out = new ArrayList<>();
            for (Call c : calls) if (c.method.equals("POST") && c.path.equals(path)) out.add(c);
            return out;
        }

        int postCount() {
            int n = 0;
            for (Call c : calls) if (c.method.equals("POST")) n++;
            return n;
        }
    }

    static DeviceApi.Result ok(String body) {
        return new DeviceApi.Result(200, body, "");
    }

    static DeviceApi.Result accepted(int n) {
        return ok("{\"accepted\":" + n + ",\"duplicates\":0,\"updated\":0,\"dropped_not_shared\":0,"
                + "\"held_back\":0,\"rejected\":[],\"action_needed\":false}");
    }

    static DeviceApi.Result dropped(int n) {
        return ok("{\"accepted\":0,\"duplicates\":0,\"updated\":0,\"dropped_not_shared\":" + n
                + ",\"held_back\":0,\"rejected\":[],\"action_needed\":false}");
    }

    /** The posting half of a host, over a fake VM. Gate state follows {@link Gate#next}. */
    static class PosterHost implements Poster.Host {
        final FakeApi api;
        Gate.State state = Gate.State.OPEN;
        boolean everOpened;
        ShareList.Post repost = ShareList.Post.ACCEPTED;
        int reposts;
        boolean shareOutOfStep;
        BooleanSupplier cancelled = () -> false;

        PosterHost(FakeApi api) {
            this.api = api;
        }

        @Override public DeviceApi api() { return api; }

        @Override
        public Gate.State observe(DeviceApi.Result r) {
            state = Gate.next(state, r.status, r.detail);
            if (state == Gate.State.OPEN) everOpened = true;
            return state;
        }

        @Override
        public ShareList.Post repostShareList() {
            reposts++;
            api.log.add("repost");
            return repost;
        }

        @Override public void raiseShareOutOfStep() { shareOutOfStep = true; }
        @Override public boolean cancelled() { return cancelled.getAsBoolean(); }
    }

    /** The whole run's host. */
    static final class RunHost extends PosterHost implements NightlyRun.Host {
        final FakeEnv env;
        final File stateDir, scratchDir;
        long nowMs;
        ShareList.Post share = ShareList.Post.ACCEPTED;
        Map<String, String> kinds = new HashMap<>();
        final Map<Notices.Notice, Boolean> notices = new HashMap<>();
        final List<String> log;

        RunHost(FakeApi api, FakeEnv env, File stateDir, File scratchDir, long nowMs) {
            super(api);
            this.env = env;
            this.stateDir = stateDir;
            this.scratchDir = scratchDir;
            this.nowMs = nowMs;
            this.log = api.log;
        }

        @Override public long nowMs() { return nowMs; }
        @Override public Gate.State state() { return state; }
        @Override public boolean everOpened() { return everOpened; }
        @Override public NightlyRead.Env readEnv() { return env; }

        /** The merges the share list reports tonight (from → to), handed to the run as postNightly would. */
        final Map<String, String> migrations = new LinkedHashMap<>();

        @Override
        public ShareList.Post postShareList(BackupCombiner.Combined combined, Map<String, String> hiddenToCanonical,
                                            Map<String, String> migrationsOut) {
            log.add("share");
            migrationsOut.putAll(migrations);
            return share;
        }

        @Override public Map<String, String> sharedKinds() { return kinds; }
        @Override public Set<String> allowlist() { return kinds.keySet(); }
        @Override public String label(String id) { return LABEL; }
        @Override public SentHashes sent() { return SentHashes.open(stateDir); }
        @Override public File stateDir() { return stateDir; }
        @Override public File dryScratchDir() { return scratchDir; }
        @Override public void raise(Notices.Notice n) { notices.put(n, true); }
        @Override public void clear(Notices.Notice n) { notices.put(n, false); }
    }
}
