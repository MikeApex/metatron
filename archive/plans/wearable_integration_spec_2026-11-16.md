# Wearable Health Data Integration: Handoff Spec

> **Status: researched, nothing built.** Sections 1–7 are Mike's web-researched spec, facts
> checked online on **2026-11-16**. Items marked UNCONFIRMED were not verified then. Section 8
> holds Claude Code's review against the repo on the same date. Discussion and earlier reasoning,
> verbatim: `archive/transcripts/2026-11-13 — Review any conversations about wearables to
> incorporate into.md`. Backlog: activity numbers screenshotted in by hand `[DB-1029-05]`; daily
> logging of steps, sleep and meals `[DB-1029-03]`.
>
> **Re-verify before buying or building.** Device support, prices and Health Connect rules
> change; this file records what was true on 2026-11-16.

## 1. Constraints

- Raw health data never touches a vendor cloud. It stays on the phone (Android, UK) and on the
  user's own VM.
- A one-time vendor sign-in is acceptable only to fetch a pairing key. After that, data must stay
  local.
- The VM reduces raw data to a few derived values before any model sees it.
- Immediate goal: replace manually screenshotting tracker data into the assistant.
- Data types: sleep (timing and stages), steps, active minutes, resting HR, HRV, SpO2, workouts,
  blood pressure.

## 2. Recommendation 1: Amazfit Bip 6

- **Why first:** the cheapest device Gadgetbridge rates "Highly supported", and it covers every
  wrist data type above.
- **Price:** about £62–80 (UK).
- **Measurements:** 24/7 HR, SpO2 and stress; sleep stages including REM; sleep HRV (measured
  during sleep only); steps and workouts. Battery up to 14 days.
- **Pairing:** pair once with the Zepp app to get the auth key (Zepp account needed), then enter
  the key in Gadgetbridge. Never unpair the watch in Zepp — that invalidates the key. Then remove
  Zepp's permissions or uninstall it.
- **Alerts:** on-watch smart alerts for abnormal readings, plus high/low HR and low-SpO2 alerts
  configurable in Gadgetbridge. Wrist buzz only; no AFib detection; nobody is contacted.
- **Trade-offs:** budget sensor. One review found step count off by 10–13 per 100 steps.

## 3. Recommendation 2 (runner-up): Garmin Forerunner 165

- **Why second:** better sensors, and Gadgetbridge pairs it with no Garmin account at all.
- **Price:** about £150 on deal, £249.99 list.
- **Gadgetbridge support:** "Mostly supported", no vendor pairing. Sleep tracking should work
  (the watch has "glances").
- **Measurements:** steps, intensity minutes, HR, resting HR, SpO2, stress, respiration, HRV,
  sleep times and stages including naps, workouts.
- **Alerts:** on-watch high/low HR threshold alerts (fire after 10 minutes of inactivity). No
  background AFib alert, no ECG; incident detection needs the Garmin Connect app.
- **Trade-offs:** firmware updates likely need Garmin Express plus an account (UNCONFIRMED).

## 4. Pipeline spec (both devices)

```
SYNC APP:   Gadgetbridge 0.95+ (F-Droid or Codeberg build).
            Settings > External Integrations > Health Connect:
            enable, select device, "Sync after device sync" = ON.
            Initial sync range: choose (3/7/30 days, all, or custom).
READ PATH:  Android Health Connect (on-device).
            Fallback: Gadgetbridge DB/ZIP export.
PERMISSIONS (client app, Capacitor native plugin):
            READ_* for each record type below
            + android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND
              (check FEATURE_READ_HEALTH_DATA_IN_BACKGROUND first)
            + PERMISSION_READ_HEALTH_DATA_HISTORY
              (without it, reads stop 30 days before the first grant)
RECORDS:    SleepSessionRecord (with stages)   StepsRecord
            HeartRateRecord                    RestingHeartRateRecord
            HeartRateVariabilityRmssdRecord    OxygenSaturationRecord
            ExerciseSessionRecord              ActiveCaloriesBurnedRecord
            DistanceRecord                     BloodPressureRecord
DERIVE ON VM: active minutes (no Health Connect type from Gadgetbridge;
            compute from steps, HR and exercise sessions), sleep vs
            personal norm, recovery.
KNOWN ISSUES: Gadgetbridge's Health Connect sync is young. Recent releases
            fixed duplicate, truncated and partial sleep records, so
            de-duplicate on ingest.
LATENCY:    Batch only. Data reaches Health Connect after each watch sync,
            so this path can't drive real-time alerts.
HYGIENE:    Turn OFF Health Connect's own cloud backup on the phone.
```

## 5. Blood pressure plan

- **Now:** the user speaks the reading ("BP 128 over 82"); parse into systolic, diastolic and
  pulse.
- **Later:** Beurer BM69 upper-arm cuff. Listed on validatebp.org (ISO 81060-2:2013).
  Gadgetbridge rates it "Mostly supported", pairs it without the vendor app, and writes it to
  Health Connect as a `BloodPressureRecord` (Gadgetbridge 0.95+). Check the BIHS list before
  buying (UNCONFIRMED there).
- **Rejected:** Omron with omblepy — omblepy doesn't run on Android, and the current M7
  (HEM-7380T1) gets only basic readout. Braun iCheck 7 — wrist cuff, no clinical validation.

## 6. Samsung Galaxy experiment (only if cardiac alerts become a requirement)

**Goal:** test whether a Galaxy Watch can give real AFib alerts and ECG while keeping data local.

**Confirmed:**
- Samsung Health Monitor (the ECG and AFib-alert app) works without a Samsung account.
- ECG reports are saved on the phone. The AFib alert runs on the watch and notifies after
  possible AFib is detected over about one hour.
- Samsung Health's cloud sync can be turned off: Samsung Health > Settings > Privacy > "Sync
  with Samsung Cloud". With it off, data stays on the phone and still flows to Health Connect.
- Health Monitor officially works only with a Galaxy phone. Hardware floor: Galaxy Watch 4 or
  newer on Wear OS 4+, phone on Android 12+.

**UNCONFIRMED:**
- Whether Health Monitor contacts Samsung after activation (activation needs an active cellular
  connection).
- Whether Samsung Health or Galaxy Wearable upload anything with no account signed in.
- Whether the AFib alert still works with the phone offline.

**Protocol:**
1. Email Samsung UK support: does Health Monitor send ECG or AFib-alert data to Samsung after
   activation, and does the alert work with the phone offline? Get the answer in writing.
2. Buy a Galaxy phone and watch from a retailer with a return window (UK online purchases carry
   a 14-day cancellation right).
3. Set up with no Samsung account. Don't sign into Samsung Health. Turn off "Sync with Samsung
   Cloud". Never link Health Monitor to Samsung Health.
4. Activate Health Monitor once while online. Record an ECG and confirm the report appears on
   the phone. Turn on the AFib alert and confirm it's active.
5. Run PCAPdroid (no root needed) on Samsung Health, Health Monitor and Galaxy Wearable for 3–5
   days. Log every connection to a Samsung domain.
6. Block those apps' internet access with NetGuard. Then: record another ECG; restart watch and
   phone and check the AFib alert is still enabled; confirm steps, sleep and HR still reach
   Health Connect; check Health Connect's cloud backup is off and its app-access list shows only
   the user's app reading the data.

**Pass:** ECG and AFib alert keep working with internet blocked; no account required; after
activation, traffic to Samsung is limited to things like update checks, with no regular
health-data uploads.
**Fail:** any forced sign-in, any feature that breaks when blocked, or unexplained regular
uploads. Then return the hardware and use the two-device route: a local Gadgetbridge tracker for
the assistant, plus a separate cloud-based alert device the assistant never reads. Pixel Watch is
the only option that calls emergency services (Loss of Pulse Detection, live in the UK).
**Limit:** traffic capture shows whether data leaves the phone, not what it contains — sufficient
for this rule.

## 7. Open item

The user's current tracker is still unknown. If Gadgetbridge supports it, prototype on it before
buying anything.

## 8. Review against the repo (Claude Code, 2026-11-16)

**Repo blockers:**
1. **The app's lowest supported Android version is below what Health Connect needs.**
   `android/variables.gradle` sets `minSdkVersion = 24`; the Health Connect client library needs
   26 (from memory — verify at build time). Raising it drops only very old phones but is a
   deliberate change and an APK rebuild. The app is Capacitor 8 and already carries hand-written
   native Java (the WhatsApp module), so a small in-repo plugin is realistic if no community
   plugin passes vetting.
2. **There is nowhere to store vitals.** The 2026-06-02 session recorded HR, SpO2, HRV,
   temperature and glucose fields as "ready to receive" wearable data. Nothing in `tools/`,
   `core/` or `config/agents/physical_health.md` holds them, or BP. **That note was wrong.**
   Spoken BP is therefore not zero-build: it needs a vitals record and a parse step — a small
   first build that the wearable feed would reuse.

**Gaps in the spec:**
3. **Delete the Zepp account after pairing**, not just the app — anything synced during pairing
   otherwise stays on Zepp's servers.
4. **Background sync.** Gadgetbridge pushes to Health Connect only after it syncs the watch. It
   needs a battery-optimisation exemption and an auto-fetch interval, or data arrives only when
   opened.
5. **Read cadence and de-duplication key** are unspecified. Health Connect record ids are the
   natural key, given the known duplicate-sleep issue.
6. **Section 6 stays deferred** — it means buying a Galaxy phone as well as a watch, and nothing
   yet makes cardiac alerts a requirement.

**Privacy:** raw data phone → VM sits inside the 2026-08-09 single-user clarification of
§ Section 0; Gadgetbridge has no internet permission at all; derived values before any model
matches the 2026-10-24 plan.

**Recommended build order:**
- (a) Vitals record + spoken BP — server-only, deploys to the VM.
- (b) Health Connect read in the APK + an endpoint posting to the VM — APK rebuild plus the
  `minSdkVersion` change. One session; recommended model **Opus 5.5** (native code, a new data
  path and privacy reduction in one change). Run cost negligible: a few KB/day on the VM, and a
  handful of tokens in the morning brief for the derived values.

**Mike's decisions outstanding:**
- Device: Bip 6 recommended (pipeline is device-agnostic, so starting cheap costs nothing later);
  Forerunner 165 if better sensors and no account ever outweigh £80.
- Name the current tracker first — if Gadgetbridge supports it, buy nothing yet.
- Setup (purchase, Zepp pairing, Gadgetbridge, Health Connect backup off) is phone-side and
  Mike-only — run it as a guided walkthrough session.

## Sources

- Gadgetbridge Health Connect: https://gadgetbridge.org/basics/integrations/health-connect/
- Gadgetbridge Amazfit: https://gadgetbridge.org/gadgets/wearables/amazfit
- Gadgetbridge Zepp OS features: https://gadgetbridge.org/basics/topics/zeppos
- Gadgetbridge Huami server pairing: https://gadgetbridge.org/basics/pairing/huami-xiaomi-server/
- Gadgetbridge Garmin: https://gadgetbridge.org/gadgets/wearables/garmin/
- Gadgetbridge Beurer: https://gadgetbridge.org/gadgets/blood-monitors/beurer/
- Amazfit Bip 6: https://us.amazfit.com/products/bip-6
- Android Health Connect read data: https://developer.android.com/guide/health-and-fitness/health-connect/develop/read-data
- Android Health Connect read restrictions: https://developer.android.com/guide/health-and-fitness/health-connect/develop/aggregate-data
- validatebp.org BM69: https://www.validatebp.org/device/bm69
- Samsung Health Monitor usage conditions: https://www.samsung.com/ae/support/apps-services/learn-more-about-the-conditions-of-using-samsung-health-monitor/
- Samsung ECG app instructions for use: https://images.samsung.com/samsung-health/ifu/IFU_ECG_CA.pdf
- Samsung Health Monitor needs a Galaxy phone: https://www.androidauthority.com/samsung-galaxy-watch-9-health-monitor-app-flaw-3690635/
