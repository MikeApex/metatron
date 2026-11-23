package com.mike.metatron.whatsapp;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * "Choose chats" (plan § 3.9), built in code; FLAG_SECURE, because chat names are on it.
 *
 * Lists the chats from {@link NightlyRead#chatList} (read off the main thread), newest activity
 * first, with a search box. A one-to-one shows the user's own contact name, or "Unknown contact"
 * with the person's own WhatsApp name in small grey text — that name is shown here only and never
 * leaves the phone. A group shows its subject.
 *
 * Save posts the list at the user's tap — the only place an empty list may be posted — and warns
 * first when it removes a chat from Metatron. Until the VM accepts the list the screen says "not
 * yet sent to Metatron", and opening the screen re-posts it. It requests nothing itself: without
 * the contacts grant (the WhatsApp screen's button) one-to-ones show "Unknown contact".
 */
public class ShareListActivity extends Activity {
    private static final String REINSTALL = "Metatron keeps your previous choices until you save a new list — saving replaces them";
    private static final String REMOVE_WARNING = "removed from Metatron straight away — its messages there are deleted";

    /** One row on the screen. Phone only. */
    private static final class Row {
        final String id;
        final String primary;
        /** Small grey text under the name; null when none. */
        final String secondary;
        final String search;
        final boolean pendingRemoval;

        Row(String id, String primary, String secondary, boolean pendingRemoval) {
            this.id = id;
            this.primary = primary;
            this.secondary = secondary;
            this.pendingRemoval = pendingRemoval;
            String s = primary + (secondary == null ? "" : " " + secondary);
            this.search = s.toLowerCase(Locale.ROOT);
        }
    }

    private int pad;
    private TextView status, notice, loading;
    private EditText search;
    private ListView list;
    private Button save;
    private final Adapter adapter = new Adapter();

    private final List<Row> rows = new ArrayList<>();
    private final Set<String> ticked = new LinkedHashSet<>();
    /** What the store holds as shared now — un-ticking one of these removes it from Metatron. */
    private final Set<String> sharedBefore = new LinkedHashSet<>();
    private Map<String, ChatList.Chat> available = Collections.emptyMap();
    private ShareStore.Found found = ShareStore.Found.ABSENT;
    private volatile boolean busy;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        pad = (int) (12 * getResources().getDisplayMetrics().density);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(pad, pad, pad, pad);

        TextView title = text(col, "Choose chats Metatron may see", 18);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        status = text(col, "", 14);
        notice = text(col, "", 13);
        notice.setVisibility(View.GONE);
        search = new EditText(this);
        search.setHint("Search");
        search.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        search.setSingleLine(true);
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int a, int b, int c) {}
            @Override public void onTextChanged(CharSequence s, int a, int b, int c) {}
            @Override public void afterTextChanged(Editable s) { adapter.filter(s.toString()); }
        });
        col.addView(search);
        loading = text(col, "Reading your chats…", 14);
        list = new ListView(this);
        list.setAdapter(adapter);
        list.setOnItemClickListener((parent, view, position, id) -> toggle(adapter.shown.get(position)));
        col.addView(list, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        save = new Button(this);
        save.setText("Save");
        save.setAllCaps(false);
        save.setEnabled(false);
        save.setOnClickListener(v -> onSave());
        col.addView(save);
        setContentView(col);
        load(true);
    }

    private TextView text(LinearLayout into, String s, int size) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        t.setPadding(0, pad / 3, 0, pad / 3);
        into.addView(t);
        return t;
    }

    // ---- loading -------------------------------------------------------------------------------

    /** Reads the chat list (and, on open, re-posts a list the VM has not accepted) off the main thread. */
    private void load(final boolean repostIfBehind) {
        final Context app = getApplicationContext();
        new Thread(() -> {
            String refusal = null;
            ChatList chats = null;
            try {
                chats = NightlyRead.chatList(app, true);
            } catch (BackupException e) {
                refusal = e.error.userText;
            } catch (RuntimeException e) {
                refusal = "Could not read your chats (" + e.getClass().getSimpleName() + ")";
            }
            ShareStore store = ShareList.store(app);
            if (repostIfBehind && store.read().found == ShareStore.Found.SAVED && !store.acceptedCurrent()) {
                store.repost(new DeviceClient(app));
            }
            ShareStore.Read r = store.read();
            List<Row> built = build(app, chats, r);
            final String shownRefusal = refusal;
            final ChatList shownChats = chats;
            runOnUiThread(() -> {
                if (isFinishing()) return;
                show(built, r, shownChats, shownRefusal);
            });
        }, "metatron-wa-share").start();
    }

    /** The rows: the chat list's chats newest first, then any stored chat it no longer shows. Background thread. */
    private static List<Row> build(Context app, ChatList chats, ShareStore.Read r) {
        ShareList.AndroidContacts contacts = new ShareList.AndroidContacts(app);
        List<Row> out = new ArrayList<>();
        Set<String> listed = new LinkedHashSet<>();
        Set<String> pending = r.state == null ? Collections.<String>emptySet() : r.state.pending;
        if (chats != null) {
            for (ChatList.Chat c : chats.chats) {
                listed.add(c.id);
                if (ChatList.GROUP.equals(c.kind)) {
                    String subject = ShareStore.clean(c.subject);
                    out.add(new Row(c.id, subject.isEmpty() ? "Group without a name" : subject, null, pending.contains(c.id)));
                } else {
                    String digits = ShareStore.phoneDigits(c.id);
                    String name = digits == null ? null : ShareStore.clean(contacts.nameFor(digits));
                    if (name != null && !name.isEmpty()) {
                        out.add(new Row(c.id, name, null, pending.contains(c.id)));
                    } else {
                        String own = ShareStore.clean(c.displayName);
                        out.add(new Row(c.id, "Unknown contact", own.isEmpty() ? null : own, pending.contains(c.id)));
                    }
                }
            }
        }
        if (r.state != null) {
            for (Map.Entry<String, ShareStore.Entry> e : r.state.chats.entrySet()) {
                if (listed.contains(e.getKey()) || r.state.merges.containsKey(e.getKey())) continue;
                String label = e.getValue().label;
                if (label.isEmpty()) label = ChatList.GROUP.equals(e.getValue().kind) ? "Group without a name" : "Unknown contact";
                out.add(new Row(e.getKey(), label, "Not in the latest chat list", false));
            }
        }
        return out;
    }

    private void show(List<Row> built, ShareStore.Read r, ChatList chats, String refusal) {
        rows.clear();
        rows.addAll(built);
        available = chats == null ? Collections.<String, ChatList.Chat>emptyMap() : chats.byId();
        found = r.found;
        ticked.clear();
        sharedBefore.clear();
        if (r.found == ShareStore.Found.SAVED) {
            for (String id : r.state.chats.keySet()) {
                if (!r.state.merges.containsKey(id) && !r.state.pending.contains(id)) sharedBefore.add(id);
            }
        }
        ticked.addAll(sharedBefore);
        if (refusal != null) loading.setText(refusal);
        else if (rows.isEmpty()) loading.setText("No chats to show yet.");
        else loading.setVisibility(View.GONE);
        showStatus(r);
        adapter.filter(search.getText().toString());
        save.setEnabled(!busy);
    }

    private void showStatus(ShareStore.Read r) {
        switch (r.found) {
            case SAVED:
                boolean accepted = r.state.accepted == r.state.version;
                status.setText(accepted ? "Sent to Metatron" : "Not yet sent to Metatron");
                if (!r.state.pending.isEmpty() && !accepted) {
                    notice.setText(r.state.pending.size() + " chat(s) you un-ticked are not yet confirmed removed "
                            + "from Metatron. Nothing more from them is sent; they are sent again for removal.");
                    notice.setVisibility(View.VISIBLE);
                } else {
                    notice.setVisibility(View.GONE);
                }
                break;
            case UNREADABLE:
                status.setText("Your chosen chats could not be read on this phone. Nothing is sent until you save again.");
                notice.setText(REINSTALL);
                notice.setVisibility(View.VISIBLE);
                break;
            default:
                status.setText("No chats chosen on this phone yet. Nothing is sent until you save.");
                notice.setText(REINSTALL);
                notice.setVisibility(View.VISIBLE);
                break;
        }
    }

    private void toggle(Row row) {
        if (!ticked.remove(row.id)) ticked.add(row.id);
        adapter.notifyDataSetChanged();
    }

    // ---- saving --------------------------------------------------------------------------------

    private void onSave() {
        if (busy) return;
        int removing = 0;
        for (String id : sharedBefore) if (!ticked.contains(id)) removing++;
        String warning = null;
        if (found != ShareStore.Found.SAVED) {
            warning = "Saving replaces the chats Metatron has now. Any chat not ticked here is " + REMOVE_WARNING + ".";
        } else if (removing > 0) {
            warning = (removing == 1 ? "The chat you un-ticked is " : removing + " chats you un-ticked are ")
                    + REMOVE_WARNING + ".";
        }
        if (warning == null) {
            saveNow();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Remove from Metatron?")
                .setMessage(warning)
                .setPositiveButton("Save", (d, w) -> saveNow())
                .setNegativeButton("Cancel", null)
                .create()
                .show();
    }

    private void saveNow() {
        if (busy) return;
        busy = true;
        save.setEnabled(false);
        final Context app = getApplicationContext();
        final List<String> chosen = new ArrayList<>(ticked);
        final Map<String, ChatList.Chat> chats = new HashMap<>(available);
        new Thread(() -> {
            String said;
            try {
                ShareStore.Saved s = ShareList.saveAndPost(app, new DeviceClient(app), chosen, chats);
                said = outcome(s);
            } catch (RuntimeException e) {
                said = "Could not save (" + e.getClass().getSimpleName() + ")";
            }
            final String shown = said;
            runOnUiThread(() -> {
                busy = false;
                if (isFinishing()) return;
                Toast.makeText(this, shown, Toast.LENGTH_LONG).show();
                load(false);
            });
        }, "metatron-wa-share-save").start();
    }

    private static String outcome(ShareStore.Saved s) {
        if (s.post == ShareList.Post.ACCEPTED) {
            if (s.removedConfirmed == 0) return "Sent to Metatron";
            return "Sent to Metatron — " + (s.removedConfirmed == 1 ? "1 chat" : s.removedConfirmed + " chats")
                    + " removed from Metatron";
        }
        return "Saved on this phone, not yet sent to Metatron. It is sent again at the next run or when you open this screen.";
    }

    // ---- the list ------------------------------------------------------------------------------

    private final class Adapter extends BaseAdapter {
        final List<Row> shown = new ArrayList<>();

        void filter(String query) {
            String q = query == null ? "" : query.trim().toLowerCase(Locale.ROOT);
            shown.clear();
            for (Row r : rows) if (q.isEmpty() || r.search.contains(q)) shown.add(r);
            notifyDataSetChanged();
        }

        @Override public int getCount() { return shown.size(); }
        @Override public Object getItem(int i) { return shown.get(i); }
        @Override public long getItemId(int i) { return i; }

        @Override
        public View getView(int position, View convert, ViewGroup parent) {
            Holder h;
            if (convert == null) {
                h = new Holder(ShareListActivity.this);
                convert = h.root;
                convert.setTag(h);
            } else {
                h = (Holder) convert.getTag();
            }
            Row r = shown.get(position);
            h.tick.setChecked(ticked.contains(r.id));
            h.name.setText(r.primary);
            String small = r.secondary;
            if (r.pendingRemoval && !ticked.contains(r.id)) {
                small = (small == null ? "" : small + " · ") + "being removed from Metatron";
            }
            h.small.setText(small == null ? "" : small);
            h.small.setVisibility(small == null ? View.GONE : View.VISIBLE);
            return convert;
        }
    }

    private static final class Holder {
        final LinearLayout root;
        final CheckBox tick;
        final TextView name, small;

        Holder(Context c) {
            int p = (int) (8 * c.getResources().getDisplayMetrics().density);
            root = new LinearLayout(c);
            root.setOrientation(LinearLayout.HORIZONTAL);
            root.setPadding(0, p / 2, 0, p / 2);
            tick = new CheckBox(c);
            tick.setClickable(false);
            tick.setFocusable(false);
            root.addView(tick);
            LinearLayout texts = new LinearLayout(c);
            texts.setOrientation(LinearLayout.VERTICAL);
            texts.setPadding(p, 0, 0, 0);
            name = new TextView(c);
            name.setTextSize(15);
            small = new TextView(c);
            small.setTextSize(12);
            small.setTextColor(Color.GRAY);
            texts.addView(name);
            texts.addView(small);
            root.addView(texts, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        }
    }
}
