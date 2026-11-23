package com.mike.metatron.whatsapp;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * The share list's store and every decision about it (build plan § 3.9), in plain Java so the JVM
 * tests can run it. {@link ShareList} is the Android glue: it hands this a file, a contacts lookup
 * and the hooks into {@link Gate} and {@link Notices}.
 *
 * <p><b>The file</b> ({@code wa_state/share.json}, written atomically): per shared chat its canonical
 * id, kind, label and, for a group, its {@code senders} map; the pending removals; the merges not
 * yet accepted; the link map (hidden id → canonical, for the live feed); the list's version and the
 * version the VM last accepted; the run of failed posts; and {@code saved_by_user} — the mark that
 * the user saved this list on this install. The file is only ever created by the user's own save.
 *
 * <p><b>Names.</b> A one-to-one's label is the user's own contact name for the phone number in its
 * canonical id, or {@code ""}; a group's is its subject (untrusted — set by any member). A group's
 * {@code senders} holds contact names only: a sender id not found in contacts is left out. The
 * person's own WhatsApp display name is never read by this class, so it can never be stored or
 * posted.
 *
 * <p><b>An unattended post never shrinks the list from lost state</b> (verify new 2): the nightly
 * post and the re-post send only a list that reads cleanly and carries the user's save, and never
 * an empty one. A missing, unreadable or never-saved file is {@link ShareList.Post#NOT_SAVED} and
 * nothing is posted. An empty list goes only from {@link #saveAndPost}, the user's own tap.
 *
 * <p><b>Un-ticking</b> is a purge on the VM at once. Until a post is accepted with a reply that
 * carries {@code removed}, the chat is a pending removal: it is out of {@link #sharedKinds} at once
 * and re-posted (as an absence) with every post.
 *
 * <p><b>Merges.</b> The VM purges a chat that drops off the list <i>before</i> it applies
 * {@code merges} ({@code set_share_list}). So the night an entry moves from a hidden id to its
 * canonical one, the hidden id is still posted alongside it, with the merge, until a post carrying
 * that merge is accepted — the merge then moves its facts, and the next post lets the empty hidden
 * id go. Events never go under it: it is not in {@link #sharedKinds}.
 */
final class ShareStore {
    static final String FILE = "share.json";
    static final String PATH = "/device/whatsapp/share-list";
    /** The VM may purge a dropped chat before it answers; longer than a plain GET. */
    static final int POST_TIMEOUT_MS = 30_000;
    /** The VM keeps a label to this many characters. */
    static final int MAX_LABEL = 60;
    /** The VM keeps a group's senders map to this many entries. */
    static final int MAX_SENDERS = 2000;
    /** Refused or failed this many posts in a row → SHARE_OUT_OF_STEP (§ 3.6). */
    static final int OUT_OF_STEP_AFTER = 2;
    private static final int FORMAT = 1;
    private static final int MAX_FILE_BYTES = 4 << 20;

    /** The user's own contacts, by phone number (digits, country code first). */
    interface Contacts {
        /** False when the contacts grant is not held: nothing can be looked up. */
        boolean available();

        /** The contact's name for this number; null when none. Only called when {@link #available}. */
        String nameFor(String phoneDigits);
    }

    /** Where a post's reply and the out-of-step notice go — {@link Gate} and {@link Notices} on the phone. */
    interface Hooks {
        void observe(DeviceApi.Result reply);

        void outOfStep(boolean raised);
    }

    /** What the file holds when it reads; {@link Read#state} null otherwise. */
    enum Found { ABSENT, UNREADABLE, NOT_SAVED, SAVED }

    static final class Read {
        final Found found;
        final State state;

        Read(Found found, State state) {
            this.found = found;
            this.state = state;
        }
    }

    /** One shared chat. */
    static final class Entry {
        final String kind;
        String label;
        /** Groups only: canonical sender id → the user's contact name. */
        final Map<String, String> senders = new TreeMap<>();

        Entry(String kind, String label) {
            this.kind = kind;
            this.label = label == null ? "" : label;
        }

        Entry copy() {
            Entry e = new Entry(kind, label);
            e.senders.putAll(senders);
            return e;
        }
    }

    /** The file's contents. */
    static final class State {
        boolean savedByUser;
        long version;
        long accepted = -1;
        int failures;
        final Map<String, Entry> chats = new TreeMap<>();
        final Set<String> pending = new LinkedHashSet<>();
        /** from → to, not yet accepted. */
        final Map<String, String> merges = new LinkedHashMap<>();
        final Map<String, String> links = new TreeMap<>();

        State copy() {
            State s = new State();
            s.savedByUser = savedByUser;
            s.version = version;
            s.accepted = accepted;
            s.failures = failures;
            for (Map.Entry<String, Entry> e : chats.entrySet()) s.chats.put(e.getKey(), e.getValue().copy());
            s.pending.addAll(pending);
            s.merges.putAll(merges);
            s.links.putAll(links);
            return s;
        }
    }

    /** How the user's save went: the post, and how many un-ticks the VM's reply confirmed removed. */
    static final class Saved {
        final ShareList.Post post;
        final int removedConfirmed;

        Saved(ShareList.Post post, int removedConfirmed) {
            this.post = post;
            this.removedConfirmed = removedConfirmed;
        }
    }

    /** One lock per process for every file read and write; posts are serialised by a second one. */
    private static final Object LOCK = new Object();
    private static final Object POST_LOCK = new Object();

    private final File file;
    private final Contacts contacts;
    private final Hooks hooks;

    ShareStore(File stateDir, Contacts contacts, Hooks hooks) {
        this.file = new File(stateDir, FILE);
        this.contacts = contacts;
        this.hooks = hooks;
    }

    // ---- reads ---------------------------------------------------------------------------------

    Read read() {
        synchronized (LOCK) {
            return load();
        }
    }

    /** Shared canonical id → kind, pending removals and retiring hidden ids excluded. Empty unless SAVED. */
    Map<String, String> sharedKinds() {
        State s = savedState();
        if (s == null) return Collections.emptyMap();
        return kinds(s);
    }

    private static Map<String, String> kinds(State s) {
        Map<String, String> out = new TreeMap<>();
        for (Map.Entry<String, Entry> e : s.chats.entrySet()) {
            if (!s.pending.contains(e.getKey())) out.put(e.getKey(), e.getValue().kind);
        }
        return Collections.unmodifiableMap(out);
    }

    boolean acceptedCurrent() {
        State s = savedState();
        return s != null && s.accepted == s.version;
    }

    /**
     * Raw chat id → canonical id when shared; null when not shared, or when it is a hidden id the
     * stored link map does not link (held for the backup, § 3.10).
     */
    String canonicalShared(String raw) {
        if (raw == null || raw.isEmpty()) return null;
        State s = savedState();
        if (s == null) return null;
        String c = s.links.get(raw);
        if (c == null) {
            if (raw.endsWith("@lid")) return null;
            c = raw;
        }
        return s.chats.containsKey(c) && !s.pending.contains(c) ? c : null;
    }

    String kindOf(String canonical) {
        return sharedKinds().get(canonical);
    }

    /** The stored label of a shared chat; "" when none or not shared. Phone only. */
    String label(String canonical) {
        State s = savedState();
        if (s == null || canonical == null) return "";
        Entry e = s.chats.get(canonical);
        return e == null || s.pending.contains(canonical) ? "" : e.label;
    }

    private State savedState() {
        Read r = read();
        return r.found == Found.SAVED ? r.state : null;
    }

    // ---- the user's save ------------------------------------------------------------------------

    /**
     * The user's tap: the ticked chats become the list, whole. A chat that was shared and is not
     * ticked becomes a pending removal; a ticked chat that was pending is shared again. A ticked id
     * the chat list no longer shows keeps its stored entry. Then the list is posted — the only post
     * that may send an empty list. An absent or unreadable file is replaced: the screen has said
     * that saving replaces what Metatron keeps.
     *
     * @param ticked    canonical ids the user ticked
     * @param available the chat list's chats by canonical id (kind and subject read; the display
     *                  name never)
     */
    Saved saveAndPost(DeviceApi api, Collection<String> ticked, Map<String, ChatList.Chat> available) {
        synchronized (POST_LOCK) {
            Read r = read();
            String expect = fingerprint(r);
            Set<String> sharedBefore = r.found == Found.SAVED ? kinds(r.state).keySet() : Collections.<String>emptySet();
            // A list that reads carries over (version, accepted version, failure run, pending
            // removals, merges); an absent or unreadable one is replaced from nothing.
            State s = r.state == null ? new State() : r.state.copy();
            Set<String> want = new LinkedHashSet<>(ticked);
            Map<String, Entry> next = new TreeMap<>();
            for (String id : want) {
                ChatList.Chat c = available.get(id);
                Entry prev = s.chats.get(id);
                if (c != null) {
                    Entry e = new Entry(c.kind, ChatList.GROUP.equals(c.kind)
                            ? clean(c.subject) : contactLabel(id, prev == null ? "" : prev.label));
                    if (prev != null && prev.kind.equals(e.kind)) e.senders.putAll(prev.senders);
                    next.put(id, e);
                } else if (prev != null) {
                    next.put(id, prev);
                }
            }
            for (String id : s.chats.keySet()) {
                if (!next.containsKey(id) && !s.merges.containsKey(id)) s.pending.add(id);
            }
            s.pending.removeAll(next.keySet());
            // A merge whose canonical id is no longer shared is dropped; its hidden id goes too.
            for (Iterator<Map.Entry<String, String>> it = s.merges.entrySet().iterator(); it.hasNext(); ) {
                Map.Entry<String, String> m = it.next();
                if (!next.containsKey(m.getValue())) {
                    it.remove();
                    s.pending.add(m.getKey());
                }
            }
            s.chats.clear();
            for (Map.Entry<String, Entry> e : next.entrySet()) s.chats.put(e.getKey(), e.getValue());
            for (String id : s.merges.keySet()) s.chats.put(id, retiring(s, id));
            s.links.values().retainAll(next.keySet());
            relabelSenders(s, Collections.<String, Set<String>>emptyMap());
            s.savedByUser = true;
            s.version++;
            // A chat ticked now that was not shared before may have been purged on the VM (an
            // un-tick it confirmed): what the phone remembers sending is gone there, so forget it
            // and the next run sends the chat's window again (F3). One still pending removal is
            // merely deduplicated by the VM. A failed write saves nothing: the user taps again.
            if (!forgetSent(next.keySet(), sharedBefore)) return new Saved(ShareList.Post.FAILED, 0);
            // Turned off while this was being built: not brought back.
            if (!commit(expect, s)) return new Saved(ShareList.Post.FAILED, 0);
            return post(api, s.copy());
        }
    }

    /**
     * Drops the sent-hash entries of every ticked chat not shared before. The sent-hash list lives
     * in the same state folder; with no salt there, nothing was ever recorded and none is created.
     */
    private boolean forgetSent(Set<String> ticked, Set<String> sharedBefore) {
        File dir = file.getParentFile();
        if (dir == null || !new File(dir, SentHashes.SALT_FILE).isFile()) return true;
        try {
            SentHashes sent = null;
            for (String id : ticked) {
                if (sharedBefore.contains(id)) continue;
                if (sent == null) sent = SentHashes.open(dir);
                sent.removeChat(id);
            }
            return true;
        } catch (RuntimeException e) {
            return false;
        }
    }

    /** The entry posted under a hidden id while its merge is unaccepted: the canonical entry's kind, no label. */
    private static Entry retiring(State s, String from) {
        Entry to = s.chats.get(s.merges.get(from));
        return new Entry(to == null ? ChatList.ONE_TO_ONE : to.kind, "");
    }

    // ---- unattended posts -----------------------------------------------------------------------

    /**
     * The nightly post, after the read (§ 3.2): migrate every shared entry whose id tonight's tables
     * link to another id, store the night's links for shared chats, rebuild each group's senders
     * from the night's senders and the current contacts, then post the whole list with the
     * unaccepted merges.
     */
    ShareList.Post postNightly(DeviceApi api, Map<String, String> newLinks,
                               Map<String, Set<String>> groupSenders, Map<String, String> hiddenToCanonical) {
        return postNightly(api, newLinks, groupSenders, hiddenToCanonical, null);
    }

    /**
     * As above; {@code migrationsOut}, when given, receives every merge not yet accepted as it stood
     * before the post (from → to) — tonight's and any carried over — so the sent-hash list can
     * follow them (F2). Filled only when the list was written back.
     *
     * <p>A migration is driven by {@code hiddenToCanonical}, tonight's folded tables (F1): a chat
     * shared under its hidden id migrates whether its link is new tonight or was already in the
     * full backup. {@code newLinks} is still accepted, and is no longer required.
     */
    ShareList.Post postNightly(DeviceApi api, Map<String, String> newLinks, Map<String, Set<String>> groupSenders,
                               Map<String, String> hiddenToCanonical, Map<String, String> migrationsOut) {
        synchronized (POST_LOCK) {
            Read r = read();
            if (r.found != Found.SAVED) return ShareList.Post.NOT_SAVED;
            String expect = fingerprint(r);
            State s = r.state;
            boolean changed = false;
            Map<String, String> moves = new LinkedHashMap<>();
            if (newLinks != null) moves.putAll(newLinks);
            if (hiddenToCanonical != null) {
                for (Map.Entry<String, String> l : hiddenToCanonical.entrySet()) {
                    if (s.chats.containsKey(l.getKey()) && !moves.containsKey(l.getKey())) moves.put(l.getKey(), l.getValue());
                }
            }
            for (Map.Entry<String, String> l : moves.entrySet()) {
                String from = l.getKey(), to = l.getValue();
                if (from == null || to == null || from.equals(to)) continue;
                if (s.merges.containsKey(from)) continue;
                Entry e = s.chats.get(from);
                if (e == null || s.pending.contains(from)) continue;
                s.chats.remove(from);
                changed = true;
                if (s.pending.contains(to)) {
                    // The user un-ticked this chat under its canonical id: it is not
                    // shared again under either id.
                    s.pending.add(from);
                    continue;
                }
                if (!s.chats.containsKey(to)) {
                    s.chats.put(to, new Entry(e.kind, contactLabel(to, "")));
                    s.chats.get(to).senders.putAll(e.senders);
                }
                s.merges.put(from, to);
                s.chats.put(from, retiring(s, from));
                s.links.put(from, to);
            }
            if (hiddenToCanonical != null) {
                for (Map.Entry<String, String> l : hiddenToCanonical.entrySet()) {
                    String h = l.getKey(), c = l.getValue();
                    if (h != null && c != null && !h.equals(c) && isShared(s, c)) s.links.put(h, c);
                }
            }
            for (String id : new ArrayList<>(s.chats.keySet())) {
                Entry e = s.chats.get(id);
                if (ChatList.ONE_TO_ONE.equals(e.kind) && !s.merges.containsKey(id)) e.label = contactLabel(id, e.label);
            }
            relabelSenders(s, groupSenders == null ? Collections.<String, Set<String>>emptyMap() : groupSenders);
            if (changed) s.version++;
            boolean empty = sharedCount(s) == 0;
            // Turned off while this was being built: nothing is written back or posted.
            if (!commit(expect, s)) return ShareList.Post.NOT_SAVED;
            if (migrationsOut != null) migrationsOut.putAll(s.merges);
            if (empty) return ShareList.Post.NOT_SAVED;
            return post(api, s.copy()).post;
        }
    }

    /** Re-post the list as it stands (a batch came back with drops — review 1). Never an empty one. */
    ShareList.Post repost(DeviceApi api) {
        synchronized (POST_LOCK) {
            State snap;
            synchronized (LOCK) {
                Read r = load();
                if (r.found != Found.SAVED) return ShareList.Post.NOT_SAVED;
                if (sharedCount(r.state) == 0) return ShareList.Post.NOT_SAVED;
                snap = r.state;
            }
            return post(api, snap).post;
        }
    }

    private static boolean isShared(State s, String id) {
        return s.chats.containsKey(id) && !s.pending.contains(id) && !s.merges.containsKey(id);
    }

    private static int sharedCount(State s) {
        int n = 0;
        for (String id : s.chats.keySet()) if (isShared(s, id)) n++;
        return n;
    }

    // ---- the post itself ------------------------------------------------------------------------

    /** The request body: every shared chat (and each retiring hidden id), and the unaccepted merges. */
    static String body(State s) {
        JsonOut.Arr chats = JsonOut.arr();
        for (Map.Entry<String, Entry> e : s.chats.entrySet()) {
            if (s.pending.contains(e.getKey())) continue;
            Entry x = e.getValue();
            JsonOut.Obj o = JsonOut.obj().put("chat", e.getKey()).put("kind", x.kind).put("label", x.label);
            if (ChatList.GROUP.equals(x.kind)) {
                JsonOut.Obj senders = JsonOut.obj();
                for (Map.Entry<String, String> m : x.senders.entrySet()) senders.put(m.getKey(), m.getValue());
                o.put("senders", senders);
            }
            chats.add(o);
        }
        JsonOut.Arr merges = JsonOut.arr();
        for (Map.Entry<String, String> m : s.merges.entrySet()) {
            merges.add(JsonOut.obj().put("from", m.getKey()).put("to", m.getValue()));
        }
        return JsonOut.obj().put("chats", chats).put("merges", merges).toString();
    }

    /** Posts the snapshot; then, under the lock, applies the reply to the file as it now stands. */
    private Saved post(DeviceApi api, State snap) {
        DeviceApi.Result r = api.post(PATH, body(snap), POST_TIMEOUT_MS);
        hooks.observe(r);
        ShareList.Post outcome = r.status < 0 ? ShareList.Post.FAILED
                : r.status == 200 && acceptedReply(r.body) ? ShareList.Post.ACCEPTED : ShareList.Post.REFUSED;
        int confirmed = 0;
        boolean raise = false, clear = false;
        synchronized (LOCK) {
            Read now = load();
            // Turned off (or replaced by an unreadable file) while the post was out: write nothing back.
            if (now.found != Found.SAVED) return new Saved(outcome, 0);
            State s = now.state;
            if (outcome == ShareList.Post.ACCEPTED) {
                s.accepted = snap.version;
                for (String id : snap.pending) if (s.pending.remove(id)) confirmed++;
                for (Map.Entry<String, String> m : snap.merges.entrySet()) {
                    if (m.getValue().equals(s.merges.get(m.getKey()))) {
                        s.merges.remove(m.getKey());
                        if (!s.pending.contains(m.getKey())) s.chats.remove(m.getKey());
                    }
                }
                s.failures = 0;
                clear = true;
            } else if (r.status != 403) {
                s.failures++;
                raise = s.failures >= OUT_OF_STEP_AFTER;
            }
            // A 403 is the gate, not a list out of step (lead, 2026-11-23): before the channel opens
            // the VM refuses every share-list post by design, and the gate's own "link is off" line
            // already says so — counting it would raise this notice on the walkthrough's first Saves.
            // It is still not accepted, so the next run, change or app open re-posts.
            writeQuietly(s);
        }
        if (clear) hooks.outOfStep(false);
        if (raise) hooks.outOfStep(true);
        return new Saved(outcome, confirmed);
    }

    /** A 200 is taken as the VM's acceptance only when its reply says what it did: {@code shared} and {@code removed}. */
    static boolean acceptedReply(String body) {
        try {
            Object v = Json.parse(body);
            if (!(v instanceof Map)) return false;
            Map<?, ?> m = (Map<?, ?>) v;
            return m.get("shared") instanceof Long && m.get("removed") instanceof Long;
        } catch (Json.Malformed e) {
            return false;
        }
    }

    // ---- names ----------------------------------------------------------------------------------

    /**
     * A one-to-one's label: the contact name for the phone number in its id, "" when contacts has
     * none. When contacts cannot be read, the stored label — itself only ever from contacts.
     */
    private String contactLabel(String canonical, String stored) {
        if (!contacts.available()) return stored == null ? "" : stored;
        String digits = phoneDigits(canonical);
        if (digits == null) return "";
        return clean(contacts.nameFor(digits));
    }

    /**
     * Each group's senders: its stored ids and the night's, each named from the current contacts;
     * an id contacts does not know is left out. Without the grant the stored names stand and a new
     * id goes unnamed.
     */
    private void relabelSenders(State s, Map<String, Set<String>> tonight) {
        for (Map.Entry<String, Entry> e : s.chats.entrySet()) {
            Entry x = e.getValue();
            if (!ChatList.GROUP.equals(x.kind)) continue;
            if (!contacts.available()) continue;
            Set<String> ids = new LinkedHashSet<>(x.senders.keySet());
            Set<String> seen = tonight.get(e.getKey());
            if (seen != null) ids.addAll(seen);
            x.senders.clear();
            for (String id : ids) {
                if (x.senders.size() >= MAX_SENDERS) break;
                String digits = phoneDigits(id);
                if (digits == null) continue;
                String name = clean(contacts.nameFor(digits));
                if (!name.isEmpty()) x.senders.put(id, name);
            }
        }
    }

    /** The phone number in a {@code digits@s.whatsapp.net} id (a {@code :device} suffix dropped); null otherwise. */
    static String phoneDigits(String id) {
        if (id == null) return null;
        int at = id.indexOf('@');
        if (at <= 0 || !"s.whatsapp.net".equals(id.substring(at + 1))) return null;
        String user = id.substring(0, at);
        int colon = user.indexOf(':');
        if (colon >= 0) user = user.substring(0, colon);
        if (user.length() < 5 || user.length() > 15) return null;
        for (int i = 0; i < user.length(); i++) if (user.charAt(i) < '0' || user.charAt(i) > '9') return null;
        return user;
    }

    /** One line, at most the VM's label length; null as "". */
    static String clean(String s) {
        if (s == null) return "";
        StringBuilder b = new StringBuilder();
        boolean space = false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isWhitespace(c) || Character.isISOControl(c)) {
                space = b.length() > 0;
                continue;
            }
            if (space) b.append(' ');
            space = false;
            b.append(c);
        }
        String out = b.toString();
        if (out.length() > MAX_LABEL) {
            int end = MAX_LABEL;
            if (Character.isHighSurrogate(out.charAt(end - 1))) end--;
            out = out.substring(0, end);
        }
        return out;
    }

    // ---- the file -------------------------------------------------------------------------------

    /** What the file held when read: its whole content, or how it failed to read. */
    private static String fingerprint(Read r) {
        return r.state == null ? r.found.name() : encode(r.state);
    }

    /**
     * Writes {@code s} only if the file still holds what was read ({@code expect}). Every writer but
     * {@link #deleteAll} holds POST_LOCK, so this refuses exactly a turn-off that came in between.
     * The contacts lookups happen before this, outside the file lock the live feed's lookups take.
     */
    private boolean commit(String expect, State s) {
        synchronized (LOCK) {
            if (!fingerprint(load()).equals(expect)) return false;
            try {
                write(s);
                return true;
            } catch (IOException e) {
                return false;
            }
        }
    }

    /** "Turn off": the file gone. A post still out writes nothing back (see {@link #post}). */
    void deleteAll() {
        synchronized (LOCK) {
            file.delete();
            new File(file.getPath() + ".tmp").delete();
        }
    }

    private Read load() {
        if (!file.isFile()) return new Read(Found.ABSENT, null);
        State s;
        try {
            s = parse(readFile());
        } catch (IOException | Json.Malformed | RuntimeException e) {
            return new Read(Found.UNREADABLE, null);
        }
        if (s == null) return new Read(Found.UNREADABLE, null);
        return new Read(s.savedByUser ? Found.SAVED : Found.NOT_SAVED, s);
    }

    private String readFile() throws IOException {
        long len = file.length();
        if (len > MAX_FILE_BYTES) throw new IOException("too large");
        try (InputStream in = new FileInputStream(file)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream((int) len);
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        }
    }

    /** The file's text → a State; null when it is not exactly this format (any field missing or mistyped). */
    static State parse(String text) throws Json.Malformed {
        Object v = Json.parse(text);
        if (!(v instanceof Map)) return null;
        Map<?, ?> m = (Map<?, ?>) v;
        if (!Long.valueOf(FORMAT).equals(m.get("v"))) return null;
        State s = new State();
        if (!(m.get("saved_by_user") instanceof Boolean)) return null;
        s.savedByUser = (Boolean) m.get("saved_by_user");
        if (!(m.get("version") instanceof Long) || !(m.get("accepted") instanceof Long)
                || !(m.get("failures") instanceof Long)) return null;
        s.version = (Long) m.get("version");
        s.accepted = (Long) m.get("accepted");
        s.failures = (int) Math.min(Integer.MAX_VALUE, Math.max(0, (Long) m.get("failures")));
        if (!(m.get("chats") instanceof Map)) return null;
        for (Map.Entry<?, ?> e : ((Map<?, ?>) m.get("chats")).entrySet()) {
            if (!(e.getValue() instanceof Map)) return null;
            Map<?, ?> c = (Map<?, ?>) e.getValue();
            Object kind = c.get("kind"), label = c.get("label");
            if (!ChatList.GROUP.equals(kind) && !ChatList.ONE_TO_ONE.equals(kind)) return null;
            if (!(label instanceof String)) return null;
            Entry x = new Entry((String) kind, (String) label);
            Object senders = c.get("senders");
            if (senders != null) {
                if (!(senders instanceof Map)) return null;
                for (Map.Entry<?, ?> se : ((Map<?, ?>) senders).entrySet()) {
                    if (!(se.getValue() instanceof String)) return null;
                    x.senders.put((String) se.getKey(), (String) se.getValue());
                }
            }
            s.chats.put((String) e.getKey(), x);
        }
        if (!(m.get("pending") instanceof List)) return null;
        for (Object p : (List<?>) m.get("pending")) {
            if (!(p instanceof String)) return null;
            s.pending.add((String) p);
        }
        if (!stringMap(m.get("merges"), s.merges) || !stringMap(m.get("links"), s.links)) return null;
        for (String from : s.merges.keySet()) if (!s.chats.containsKey(from)) return null;
        return s;
    }

    private static boolean stringMap(Object v, Map<String, String> into) {
        if (!(v instanceof Map)) return false;
        for (Map.Entry<?, ?> e : ((Map<?, ?>) v).entrySet()) {
            if (!(e.getValue() instanceof String)) return false;
            into.put((String) e.getKey(), (String) e.getValue());
        }
        return true;
    }

    static String encode(State s) {
        JsonOut.Obj chats = JsonOut.obj();
        for (Map.Entry<String, Entry> e : s.chats.entrySet()) {
            Entry x = e.getValue();
            JsonOut.Obj o = JsonOut.obj().put("kind", x.kind).put("label", x.label);
            if (ChatList.GROUP.equals(x.kind)) {
                JsonOut.Obj senders = JsonOut.obj();
                for (Map.Entry<String, String> m : x.senders.entrySet()) senders.put(m.getKey(), m.getValue());
                o.put("senders", senders);
            }
            chats.put(e.getKey(), o);
        }
        JsonOut.Arr pending = JsonOut.arr();
        for (String p : s.pending) pending.add(p);
        JsonOut.Obj merges = JsonOut.obj();
        for (Map.Entry<String, String> m : s.merges.entrySet()) merges.put(m.getKey(), m.getValue());
        JsonOut.Obj links = JsonOut.obj();
        for (Map.Entry<String, String> l : s.links.entrySet()) links.put(l.getKey(), l.getValue());
        return JsonOut.obj().put("v", FORMAT).put("saved_by_user", s.savedByUser).put("version", s.version)
                .put("accepted", s.accepted).put("failures", s.failures).put("chats", chats)
                .put("pending", pending).put("merges", merges).put("links", links).toString();
    }

    /** Atomically: a temporary file, synced, renamed over the old one. */
    private void write(State s) throws IOException {
        File dir = file.getParentFile();
        if (dir != null && !dir.isDirectory() && !dir.mkdirs()) throw new IOException("no state folder");
        File tmp = new File(file.getPath() + ".tmp");
        try (FileOutputStream out = new FileOutputStream(tmp)) {
            out.write(encode(s).getBytes(StandardCharsets.UTF_8));
            out.getFD().sync();
        }
        if (!tmp.renameTo(file)) {
            tmp.delete();
            throw new IOException("rename failed");
        }
    }

    private void writeQuietly(State s) {
        try {
            write(s);
        } catch (IOException ignored) {
            // The file stays as it was; the next post repeats what this one would have recorded.
        }
    }
}
