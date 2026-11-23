package com.mike.metatron.whatsapp;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.os.Process;

import java.io.File;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * The nightly backup read (plan §§ 3.2–3.3): one one-shot JobScheduler job at a time
 * ({@link WaFiles#NIGHTLY_JOB_ID}) — earliest 03:00, charging required until the 06:00 override
 * deadline, persisted across reboot. On finish it schedules the next night; the three retry-later
 * codes reschedule +30 min, at most 6 times. {@link #onStopJob} asks to be rescheduled (verify new
 * 4): the cursor has advanced per accepted batch, so the resumed run starts where this one stopped.
 * A system-stopped run, and a job that finds a run still in progress, schedule a run +5 min out
 * (within the retry cap; F5) — only the user's {@link #cancel} ends with nothing scheduled.
 *
 * <p>Thin on purpose: what a run does is {@link NightlyRun}, when it runs is {@link
 * NightlySchedule} — both plain Java and unit-tested. This class owns the thread, the cancel flag
 * and the JobScheduler calls. Work runs off the main thread, one run at a time per process (the
 * work-folder lease also holds across processes); a cancelled run stops at its next check, between
 * steps and between batches, with every decrypted copy deleted in its finally.
 */
public class NightlyJob extends JobService {
    private static final Object LOCK = new Object();
    /** The run in progress in this process, if any. */
    private static Running current;

    /** One run: its cancel flag and, for a scheduled run, its JobScheduler handle. */
    private static final class Running {
        final AtomicBoolean cancelled = new AtomicBoolean();
        final JobService service;
        final JobParameters params;
        /** The system stopped it ({@link #onStopJob}): no jobFinished; it runs again soon (F5). */
        volatile boolean systemStopped;
        /** The user's {@link #cancel} (gate closed, "Turn off"): ends with nothing rescheduled. */
        volatile boolean userCancelled;

        Running(JobService service, JobParameters params) {
            this.service = service;
            this.params = params;
        }
    }

    @Override
    public boolean onStartJob(JobParameters params) {
        Context app = getApplicationContext();
        if (start(app, NightlyRun.Trigger.NIGHT, this, params)) return true;
        // A run is still in progress — one the system stopped, still reaching its next cancel
        // check, or one the app started. Never finished with nothing (F5): run again soon.
        afterRun(app, true, false, false, "");
        return false;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        synchronized (LOCK) {
            if (current != null && current.params == params) {
                current.systemStopped = true;
                current.cancelled.set(true);
            }
        }
        return true; // reschedule (verify new 4); the run's own end also schedules it soon (F5)
    }

    // ---- the statics the screen, the gate and the app call -------------------------------------

    /** Schedules the next night's run if none is scheduled — only when the gate and the grants allow one. */
    public static void ensureScheduled(Context ctx) {
        Context app = ctx.getApplicationContext();
        if (!allowed(app)) return;
        JobScheduler js = scheduler(app);
        if (js == null || js.getPendingJob(WaFiles.NIGHTLY_JOB_ID) != null) return;
        long now = System.currentTimeMillis();
        schedule(app, js, NightlySchedule.nextNight(now, TimeZone.getDefault()), now);
    }

    /**
     * The user's "Dry run now" tap (§ 3.2): before the channel has ever opened, with consent
     * recorded, it opens the 7-night window, runs now, and keeps the nightly job for the window.
     * With the gate already OPEN it starts the real run instead (F9). Returns what the screen
     * says ({@link NightlySchedule#dryTapLabel}); "" when nothing was started.
     */
    public static String runDryNow(Context ctx) {
        final Context app = ctx.getApplicationContext();
        Gate.State state = Gate.state(app);
        String label = NightlySchedule.dryTapLabel(state, Gate.everOpened(app));
        if (label.isEmpty()) return label;
        final boolean real = state == Gate.State.OPEN;
        new Thread(() -> {
            if (!real) {
                final long now = System.currentTimeMillis();
                NightlyState.update(WaFiles.stateDir(app), s -> s.dryTapMs = now);
            }
            // Whichever is started, the VM's answer to the cursor call decides: a gate that
            // opened since the tap makes it a real run — hence the screen's "while the link is off".
            start(app, real ? NightlyRun.Trigger.APP_OPEN : NightlyRun.Trigger.DRY_TAP, null, null);
            ensureScheduled(app);
        }, "metatron-wa-dry").start();
        return label;
    }

    /** Stops all reading: the scheduled job, and any run in progress (at its next check). */
    public static void cancel(Context ctx) {
        synchronized (LOCK) {
            if (current != null) {
                current.userCancelled = true;
                current.cancelled.set(true);
            }
        }
        JobScheduler js = scheduler(ctx.getApplicationContext());
        if (js != null) js.cancel(WaFiles.NIGHTLY_JOB_ID);
    }

    /**
     * App opened (the lead wires this from MainActivity.onResume): when the gate allows a job and
     * no run has succeeded for 26 h — a force-stop cancels jobs and Android says nothing — run now;
     * and make sure the next night is scheduled. Returns at once; the check runs off the main thread.
     */
    public static void onAppOpen(Context ctx) {
        final Context app = ctx.getApplicationContext();
        new Thread(() -> {
            recheckGate(app);
            if (!allowed(app)) return;
            ensureScheduled(app);
            NightlyState st = NightlyState.load(WaFiles.stateDir(app));
            if (NightlySchedule.overdue(System.currentTimeMillis(), st.lastSuccessMs, st.lastAttemptMs)) {
                start(app, NightlyRun.Trigger.APP_OPEN, null, null);
            }
        }, "metatron-wa-open").start();
    }

    // ---- inside ----------------------------------------------------------------------------------

    /**
     * After a 403 the job is cancelled and the listener off; only the WhatsApp screen re-asked
     * the VM. So an app open, when the gate was once open and is now not, asks once — at most
     * every 30 min ({@link NightlySchedule#recheckGate}) — and an OPEN answer brings the listener
     * back through {@link Gate#observe} and the job through {@link #ensureScheduled} (F6).
     */
    private static void recheckGate(Context app) {
        final long now = System.currentTimeMillis();
        NightlyState st = NightlyState.load(WaFiles.stateDir(app));
        if (!NightlySchedule.recheckGate(DeviceTokenVault.present(app), Gate.everOpened(app), Gate.state(app),
                now, st.gateCheckMs)) return;
        NightlyState.update(WaFiles.stateDir(app), s -> s.gateCheckMs = now);
        Gate.refresh(app, new DeviceClient(app));
    }

    /** Whether a job may be scheduled or run unprompted (§ 3.12; {@link NightlySchedule#jobAllowed}). */
    static boolean allowed(Context app) {
        Gate.State s = Gate.state(app);
        long tap = NightlyState.load(WaFiles.stateDir(app)).dryTapMs;
        return NightlySchedule.jobAllowed(s, Gate.everOpened(app),
                NightlySchedule.inDryWindow(System.currentTimeMillis(), tap),
                KeyVault.present(app), WhatsAppActivity.allFilesGranted(app));
    }

    /** Starts a run on its own thread unless one is in progress. True when started. */
    private static boolean start(final Context app, final NightlyRun.Trigger trigger, JobService service, JobParameters params) {
        final Running r;
        synchronized (LOCK) {
            if (current != null) return false;
            r = new Running(service, params);
            current = r;
        }
        Thread t = new Thread(() -> {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            runAndFinish(app, trigger, r);
        }, "metatron-wa-nightly");
        t.start();
        return true;
    }

    private static void runAndFinish(Context app, NightlyRun.Trigger trigger, Running r) {
        NightlyRun.Outcome o = null;
        try {
            o = new NightlyRun(new AndroidHost(app, r.cancelled)).run(trigger);
        } catch (RuntimeException e) {
            o = null; // a fault: no report, nothing retried tonight; the next night runs again
        } finally {
            synchronized (LOCK) {
                if (current == r) current = null;
            }
            if (r.params != null && !r.systemStopped) r.service.jobFinished(r.params, false);
            afterRun(app, false, r.userCancelled, r.systemStopped, o == null ? "" : o.error);
        }
    }

    /**
     * What follows a run (or a job that found one in progress, {@code busy}): {@link
     * NightlySchedule#afterEnd} / {@link NightlySchedule#whenBusy} decide — the next night, +30
     * min, +5 min, or nothing after the user's cancel (F5).
     */
    private static void afterRun(Context app, final boolean busy, final boolean userCancelled,
                                 final boolean systemStopped, final String error) {
        if (!allowed(app)) return;
        JobScheduler js = scheduler(app);
        if (js == null) return;
        final NightlySchedule.Next[] next = {NightlySchedule.Next.NIGHT};
        NightlyState.update(WaFiles.stateDir(app), s -> next[0] = busy ? NightlySchedule.whenBusy(s)
                : NightlySchedule.afterEnd(userCancelled, systemStopped, error, s));
        long now = System.currentTimeMillis();
        long[] when;
        switch (next[0]) {
            case NONE: return;
            case RETRY: when = NightlySchedule.retry(now); break;
            case SOON: when = NightlySchedule.soon(now); break;
            default: when = NightlySchedule.nextNight(now, TimeZone.getDefault());
        }
        schedule(app, js, when, now);
    }

    private static void schedule(Context app, JobScheduler js, long[] when, long now) {
        long latency = Math.max(0, when[0] - now);
        long deadline = Math.max(latency, when[1] - now);
        JobInfo job = new JobInfo.Builder(WaFiles.NIGHTLY_JOB_ID, new ComponentName(app, NightlyJob.class))
                .setMinimumLatency(latency)
                .setOverrideDeadline(deadline)
                .setRequiresCharging(true)
                .setPersisted(true)
                .build();
        try {
            js.schedule(job);
        } catch (RuntimeException ignored) {
            // e.g. the system's job limit: the app-open rule and the next boot schedule it again
        }
    }

    private static JobScheduler scheduler(Context app) {
        return (JobScheduler) app.getSystemService(Context.JOB_SCHEDULER_SERVICE);
    }

    /** The real {@link NightlyRun.Host}: the VM, the gate, the share list, the files. */
    private static final class AndroidHost implements NightlyRun.Host {
        private final Context ctx;
        private final AtomicBoolean cancelled;
        private final DeviceApi api;

        AndroidHost(Context ctx, AtomicBoolean cancelled) {
            this.ctx = ctx;
            this.cancelled = cancelled;
            this.api = new DeviceClient(ctx);
        }

        @Override public DeviceApi api() { return api; }
        @Override public Gate.State observe(DeviceApi.Result r) { return Gate.observe(ctx, r); }
        @Override public ShareList.Post repostShareList() { return ShareList.repost(ctx, api); }
        @Override public void raiseShareOutOfStep() { Notices.raise(ctx, Notices.Notice.SHARE_OUT_OF_STEP); }
        @Override public boolean cancelled() { return cancelled.get(); }
        @Override public long nowMs() { return System.currentTimeMillis(); }
        @Override public Gate.State state() { return Gate.state(ctx); }
        @Override public boolean everOpened() { return Gate.everOpened(ctx); }
        @Override public NightlyRead.Env readEnv() { return NightlyRead.androidEnv(ctx, cancelled::get); }
        @Override public ShareList.Post postShareList(BackupCombiner.Combined c, Map<String, String> h2c,
                                                      Map<String, String> migrationsOut) {
            return ShareList.postNightly(ctx, api, c, h2c, migrationsOut);
        }
        @Override public Map<String, String> sharedKinds() { return ShareList.sharedKinds(ctx); }
        @Override public Set<String> allowlist() { return ShareList.allowlist(ctx); }
        @Override public String label(String id) { return ShareList.label(ctx, id); }
        @Override public SentHashes sent() { return SentHashes.open(WaFiles.stateDir(ctx)); }
        @Override public File stateDir() { return WaFiles.stateDir(ctx); }
        @Override public File dryScratchDir() { return new File(WaFiles.noBackup(ctx), "wa_dry_sent"); }
        @Override public void raise(Notices.Notice n) { Notices.raise(ctx, n); }
        @Override public void clear(Notices.Notice n) { Notices.clear(ctx, n); }
    }
}
