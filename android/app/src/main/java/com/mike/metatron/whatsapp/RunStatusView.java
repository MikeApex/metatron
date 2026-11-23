package com.mike.metatron.whatsapp;

import android.content.Context;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.File;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.TimeZone;

/**
 * The last run on the WhatsApp screen: when it ran, real or dry, the report's counts, and for a
 * dry run what it would have sent per chat (labels from {@link ShareList#label}) and the warnings
 * it would have raised. Read from {@code wa_state/last_report.json} ({@link LastReport}) — counts,
 * codes and labels only. Active notices are the screen's own (W3), not repeated here.
 */
public final class RunStatusView {
    private RunStatusView() {}

    public static void addTo(LinearLayout layout, Context ctx) {
        File state = WaFiles.stateDir(ctx);
        for (String line : lines(LastReport.load(state), NightlyState.load(state), sentKeys(state),
                System.currentTimeMillis(), TimeZone.getDefault())) {
            TextView t = new TextView(ctx);
            t.setText(line);
            t.setTextSize(13);
            int pad = (int) (4 * ctx.getResources().getDisplayMetrics().density);
            t.setPadding(0, pad, 0, pad);
            layout.addView(t);
        }
    }

    /** The lines shown — plain Java, unit-tested. {@code sentKeys} < 0 when no sent-hash list exists yet. */
    static List<String> lines(LastReport last, NightlyState st, int sentKeys, long nowMs, TimeZone tz) {
        List<String> out = new ArrayList<>();
        if (last == null) out.add("No nightly read has run yet.");
        else out.addAll(last.lines(tz));
        if (NightlySchedule.inDryWindow(nowMs, st.dryTapMs)) {
            DateFormat f = DateFormat.getDateInstance(DateFormat.MEDIUM);
            f.setTimeZone(tz);
            out.add("Dry runs nightly until " + f.format(new Date(st.dryTapMs + NightlySchedule.DRY_WINDOW_MS)));
        }
        if (sentKeys >= 0) out.add("Messages remembered as sent: " + sentKeys);
        return out;
    }

    /** The sent-hash list's entry count (§ 8's meter), or −1 when none exists — opening one here would create it. */
    private static int sentKeys(File state) {
        if (!new File(state, SentHashes.SALT_FILE).isFile()) return -1;
        try {
            return SentHashes.open(state).size();
        } catch (RuntimeException e) {
            return -1;
        }
    }
}
