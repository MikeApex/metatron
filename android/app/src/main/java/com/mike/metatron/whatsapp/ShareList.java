package com.mike.metatron.whatsapp;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.ContactsContract;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * The chats the user shares (plan § 3.9) — the Android side. Every decision is in
 * {@link ShareStore}, which works on {@code wa_state/share.json}; this class hands it the file,
 * the user's contacts (only when {@code READ_CONTACTS} is granted — it never asks) and the hooks:
 * every /device/* reply a method here receives goes through {@link Gate#observe}, and
 * {@code SHARE_OUT_OF_STEP} is raised and cleared through {@link Notices}.
 */
public final class ShareList {
    /** How a share-list post went. */
    public enum Post {
        /** The VM accepted this version. */
        ACCEPTED,
        /** Nothing posted: no list the user saved on this install, or it does not read cleanly — send no events. */
        NOT_SAVED,
        /** The VM answered, but not 200 (403, 400, …). */
        REFUSED,
        /** No answer (network, timeout). */
        FAILED
    }

    private ShareList() {}

    static ShareStore store(Context ctx) {
        final Context app = ctx.getApplicationContext();
        return new ShareStore(WaFiles.stateDir(app), new AndroidContacts(app), new ShareStore.Hooks() {
            @Override
            public void observe(DeviceApi.Result reply) {
                Gate.observe(app, reply);
            }

            @Override
            public void outOfStep(boolean raised) {
                if (raised) Notices.raise(app, Notices.Notice.SHARE_OUT_OF_STEP);
                else Notices.clear(app, Notices.Notice.SHARE_OUT_OF_STEP);
            }
        });
    }

    /**
     * The chats whose events may be sent now: canonical id → "group" | "one_to_one". Excludes
     * pending removals. Empty unless the list is the user's own save on this install and reads cleanly.
     */
    public static Map<String, String> sharedKinds(Context ctx) {
        return store(ctx).sharedKinds();
    }

    /** The combine's allowlist: the shared canonical ids (the combine canonicalises before it filters). */
    public static Set<String> allowlist(Context ctx) {
        return sharedKinds(ctx).keySet();
    }

    /**
     * The nightly post, after the read (§ 3.2, verify 6): migrate every shared entry whose id
     * tonight's tables ({@code hiddenToCanonical}) link to another id — new tonight or already in
     * the full backup (F1) — store the night's link map (hidden id → canonical, for the live feed),
     * then post the whole list with each group's {@code senders} rebuilt from {@code
     * combined.groupSenders} and the current contacts, and the unaccepted {@code merges}. {@link
     * Post#NOT_SAVED} — no post — when the list was never saved by the user on this install or is
     * unreadable (verify new 2). Raises / clears {@code SHARE_OUT_OF_STEP} per § 3.6.
     */
    public static Post postNightly(Context ctx, DeviceApi api, BackupCombiner.Combined combined,
                                   Map<String, String> hiddenToCanonical) {
        return postNightly(ctx, api, combined, hiddenToCanonical, null);
    }

    /** As above; {@code migrationsOut} receives the unaccepted merges (from → to) for the sent-hash list (F2). */
    public static Post postNightly(Context ctx, DeviceApi api, BackupCombiner.Combined combined,
                                   Map<String, String> hiddenToCanonical, Map<String, String> migrationsOut) {
        return store(ctx).postNightly(api, combined == null ? null : combined.newLinks,
                combined == null ? null : combined.groupSenders, hiddenToCanonical, migrationsOut);
    }

    /** Re-post the current list as it stands (a batch came back with drops — review 1). */
    public static Post repost(Context ctx, DeviceApi api) {
        return store(ctx).repost(api);
    }

    /** Whether the VM has accepted the list's current version. */
    public static boolean acceptedCurrent(Context ctx) {
        return store(ctx).acceptedCurrent();
    }

    /**
     * The live feed's lookup: a notification's raw chat id → its canonical id when that chat is
     * shared (and not pending removal), via the stored link map; null when not shared, or a
     * one-to-one hidden id the map does not link (held for the backup, § 3.10).
     */
    public static String canonicalShared(Context ctx, String rawChatId) {
        return store(ctx).canonicalShared(rawChatId);
    }

    /** "group" | "one_to_one" for a shared canonical id; null when not shared. */
    public static String kindOf(Context ctx, String canonicalChatId) {
        return store(ctx).kindOf(canonicalChatId);
    }

    /**
     * The label the screen shows for a shared chat — the user's contact name or the group subject;
     * "" when none. On the phone only (the run-status view's per-chat counts); never posted.
     */
    public static String label(Context ctx, String canonicalChatId) {
        return store(ctx).label(canonicalChatId);
    }

    /** "Turn off": forget the list, the link map and the accepted version. */
    public static void deleteAll(Context ctx) {
        store(ctx).deleteAll();
    }

    /**
     * The user's own tap on Save (the screen): the ticked chats become the list, posted at once —
     * the only post that may send an empty list. Blocking.
     */
    static ShareStore.Saved saveAndPost(Context ctx, DeviceApi api, Collection<String> ticked,
                                        Map<String, ChatList.Chat> available) {
        return store(ctx).saveAndPost(api, ticked, available);
    }

    /** Whether the contacts grant is held. Never requested here (the WhatsApp screen asks). */
    static boolean contactsGranted(Context ctx) {
        return ctx.checkSelfPermission(Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED;
    }

    /**
     * The user's contacts by phone number, through the system's own number matching (so a number
     * saved without its country code still matches). One lookup per number per instance.
     */
    static final class AndroidContacts implements ShareStore.Contacts {
        private final Context ctx;
        private final Map<String, String> cache = new HashMap<>();
        private Boolean granted;

        AndroidContacts(Context ctx) {
            this.ctx = ctx;
        }

        @Override
        public boolean available() {
            if (granted == null) granted = contactsGranted(ctx);
            return granted;
        }

        @Override
        public String nameFor(String phoneDigits) {
            if (!available() || phoneDigits == null || phoneDigits.isEmpty()) return null;
            if (cache.containsKey(phoneDigits)) return cache.get(phoneDigits);
            String name = null;
            Uri uri = Uri.withAppendedPath(ContactsContract.PhoneLookup.CONTENT_FILTER_URI, Uri.encode("+" + phoneDigits));
            try (Cursor c = ctx.getContentResolver().query(uri,
                    new String[] {ContactsContract.PhoneLookup.DISPLAY_NAME}, null, null, null)) {
                if (c != null && c.moveToFirst() && !c.isNull(0)) name = c.getString(0);
            } catch (RuntimeException e) {
                // A revoked grant or a provider failure: no name, as for an unknown number.
                name = null;
            }
            cache.put(phoneDigits, name);
            return name;
        }
    }
}
