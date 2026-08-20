"""
tests/test_vertex_cache_ttl.py — the sliding TTL on Vertex context caches.

Covers the 2026-08-20 cost defect: cache STORAGE is billed per wall-clock hour
($4.50/1M tokens/hour on Pro) and the caches carried a midnight-UTC expiry, so a
cache created at 06:19 billed for 17.7 hours to serve a median 2-minute burst.
The bill exceeded spend_guard's per-call estimate 2.3x and tripped the soft cap,
stopping the VM mid-deploy.

What is under test is the part that is enforced in Python rather than trusted to
Vertex: the ten-minute expiry, the lazy after-the-response refresh, the registry
tuple being rewritten on refresh (a refresh that pushes the server-side expiry
without updating the tuple causes a metered creation per burst), eviction rather
than an exception on a failed refresh, the creation lock, and the ownership tag
carrying no PID.

The Vertex client is a fake — no network, no project, no credentials needed.

Run:  python3 tests/test_vertex_cache_ttl.py
Exit: 0 all pass, 1 on any failure.
"""

from __future__ import annotations

import datetime
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        _failures.append(name)


class FakeUsage:
    def __init__(self, tokens: int):
        self.total_token_count = tokens


class FakeCache:
    def __init__(self, name: str, config, tokens: int = 18127, display_name=None):
        self.name = name
        self.display_name = display_name if display_name is not None else getattr(config, "display_name", None)
        self.expire_time = getattr(config, "expire_time", None)
        self.usage_metadata = FakeUsage(tokens)


class FakeCaches:
    """Records every call so the test can assert on creations vs refreshes."""

    def __init__(self, fail_update: bool = False, create_delay: float = 0.0):
        self.listed: list[FakeCache] = []
        self.created: list[FakeCache] = []
        self.updated: list[tuple[str, object]] = []
        self.deleted: list[str] = []
        self.fail_update = fail_update
        self.create_delay = create_delay

    def create(self, *, model, config):
        if self.create_delay:
            time.sleep(self.create_delay)
        cache = FakeCache(f"cachedContents/{len(self.created) + 1}", config)
        self.created.append(cache)
        return cache

    def list(self):
        return list(self.listed)

    def update(self, *, name, config):
        if self.fail_update:
            raise RuntimeError("update refused")
        self.updated.append((name, config))
        return FakeCache(name, config)

    def delete(self, *, name):
        self.deleted.append(name)


class FakeClient:
    def __init__(self, **kw):
        self.caches = FakeCaches(**kw)


PROMPT = "system prompt under test. " * 40


def main() -> int:
    import core.orchestrator as orch

    # The dev kill switch (VERTEX_CACHE_DISABLED in .env, loaded at orchestrator
    # import) would turn every check below into a test of the switch. Clear it —
    # the switch has its own explicit check at the end, which sets it back.
    os.environ.pop("VERTEX_CACHE_DISABLED", None)

    ttl = orch._VERTEX_CACHE_TTL_MINUTES
    margin = orch._VERTEX_CACHE_REFRESH_MARGIN_MINUTES
    now = lambda: datetime.datetime.now(datetime.timezone.utc)

    # Intercept the storage accrual for the whole run. Without this the suite
    # writes fake dollars into the real data/diagnostics/spend_*.json — a test
    # that corrupts the cost meter it is testing, which is the same class of
    # error as the defect under test.
    charged: list[tuple] = []
    orch._record_cache_storage = lambda model, cache, minutes: charged.append(
        (model, getattr(getattr(cache, "usage_metadata", None), "total_token_count", 0), minutes)
    )

    def fresh_registry():
        with orch._vertex_cache_lock:
            orch._vertex_cache_registry.clear()

    # --- creation ----------------------------------------------------------
    fresh_registry()
    client = FakeClient()
    name = orch._get_or_create_vertex_cache(client, PROMPT, "gemini-3.1-pro-preview", None)
    created = client.caches.created[0]
    remaining = (created.expire_time - now()).total_seconds() / 60

    check("cache is created", name == "cachedContents/1")
    check(
        f"expiry is {ttl} minutes out, not midnight UTC",
        ttl - 1 < remaining <= ttl,
        f"{remaining:.1f} min",
    )
    check("creation stamps an ownership display_name", created.display_name == orch._vertex_cache_owner())
    check("owner tag carries no PID", str(orch._vertex_cache_owner()).count(":") == 2
          and not any(part.isdigit() for part in orch._vertex_cache_owner().split(":")))

    # A second call inside the window reuses the name — no second creation.
    again = orch._get_or_create_vertex_cache(client, PROMPT, "gemini-3.1-pro-preview", None)
    check("a live cache is reused, not recreated", again == name and len(client.caches.created) == 1)

    # --- refresh is lazy ---------------------------------------------------
    orch._refresh_vertex_cache(client, name)
    check(
        f"no refresh while more than {margin} min remain",
        client.caches.updated == [],
        f"{len(client.caches.updated)} update call(s)",
    )

    # Wind the stored expiry down to inside the margin.
    with orch._vertex_cache_lock:
        key = next(iter(orch._vertex_cache_registry))
        orch._vertex_cache_registry[key] = (name, now() + datetime.timedelta(minutes=margin - 1))
    orch._refresh_vertex_cache(client, name)
    check(f"refresh fires inside the {margin} min margin", len(client.caches.updated) == 1)

    with orch._vertex_cache_lock:
        _n, stored_expiry = orch._vertex_cache_registry[key]
    pushed = (stored_expiry - now()).total_seconds() / 60
    sent = (client.caches.updated[0][1].expire_time - now()).total_seconds() / 60
    check(f"refresh pushes the server-side expiry a full {ttl} min", ttl - 1 < sent <= ttl, f"{sent:.1f} min")
    check(
        "the registry tuple is rewritten with the new expiry",
        ttl - 1 < pushed <= ttl,
        f"stored {pushed:.1f} min — a stale tuple makes the next call create a second cache",
    )

    # And with the tuple updated, the next get-or-create must not create again.
    orch._get_or_create_vertex_cache(client, PROMPT, "gemini-3.1-pro-preview", None)
    check("no metered re-creation after a refresh", len(client.caches.created) == 1)

    # --- a failed refresh evicts, it does not raise ------------------------
    fresh_registry()
    bad = FakeClient(fail_update=True)
    bad_name = orch._get_or_create_vertex_cache(bad, PROMPT, "gemini-3.1-pro-preview", None)
    with orch._vertex_cache_lock:
        bad_key = next(iter(orch._vertex_cache_registry))
        orch._vertex_cache_registry[bad_key] = (bad_name, now() + datetime.timedelta(minutes=1))
    raised = None
    try:
        orch._refresh_vertex_cache(bad, bad_name)
    except Exception as e:  # pragma: no cover - the point of the check
        raised = e
    check("a failed refresh does not raise", raised is None, str(raised))
    check("a failed refresh evicts the entry", orch._vertex_cache_registry == {})

    # --- concurrency: one creation, not one per thread ---------------------
    fresh_registry()
    slow = FakeClient(create_delay=0.15)
    results: list[str | None] = []
    threads = [
        threading.Thread(
            target=lambda: results.append(
                orch._get_or_create_vertex_cache(slow, PROMPT, "gemini-3.1-pro-preview", None)
            )
        )
        for _ in range(6)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    check(
        "six concurrent first turns create exactly one cache",
        len(slow.caches.created) == 1,
        f"{len(slow.caches.created)} created — each extra one bills with no handle to delete it",
    )
    check("every thread gets the same cache name", len(set(results)) == 1 and results[0] is not None)

    # --- exit handler deletes what this process created --------------------
    orch._vertex_native_client = slow
    orch._delete_owned_vertex_caches()
    check("exit deletes this process's caches", slow.caches.deleted == ["cachedContents/1"])
    check("exit clears the registry", orch._vertex_cache_registry == {})
    orch._vertex_native_client = None

    # --- eviction ----------------------------------------------------------
    fresh_registry()
    ev = FakeClient()
    ev_name = orch._get_or_create_vertex_cache(ev, PROMPT, "gemini-3.1-pro-preview", None)
    orch._evict_vertex_cache(ev_name)
    check("evict removes the entry", orch._vertex_cache_registry == {})
    check(
        "a 404 on the stream path is recognised as a missing cache",
        orch._is_cache_not_found(RuntimeError("404 NOT_FOUND: CachedContent not found")),
    )
    fresh_registry()

    # --- storage is charged at grant time, per wall-clock window ----------
    import core.spend_guard as guard

    charged.clear()
    fresh_registry()
    sc = FakeClient()
    sc_name = orch._get_or_create_vertex_cache(sc, PROMPT, "gemini-3.1-pro-preview", None)
    check(
        "creation charges a full TTL window of storage",
        charged == [("gemini-3.1-pro-preview", 18127, ttl)],
        str(charged),
    )
    with orch._vertex_cache_lock:
        k = next(iter(orch._vertex_cache_registry))
        orch._vertex_cache_registry[k] = (sc_name, now() + datetime.timedelta(minutes=1))
    orch._refresh_vertex_cache(sc, sc_name, "gemini-3.1-pro-preview")
    check("a refresh charges the window it grants", len(charged) == 2 and charged[1][2] == ttl, str(charged))

    rate = guard._entry_for("gemini-3.1-pro-preview").get("cache_storage_per_hour")
    check("the Pro storage rate is in the pricing table", rate == 4.50, str(rate))
    day_of_storage = 18127 / 1e6 * 4.50 * 17.7
    check(
        "a midnight-expiry Pro cache costs what the bill said it did",
        1.35 < day_of_storage < 1.50,
        f"${day_of_storage:.2f} for one abandoned cache over 17.7 h",
    )
    ten_minutes = 18127 / 1e6 * 4.50 * (ttl / 60)
    check("the same cache on the sliding TTL costs cents", ten_minutes < 0.02, f"${ten_minutes:.4f}")

    # A cache hit must not be priced as a miss.
    hit = guard.estimate_usd("gemini-3.1-pro-preview", 20000, 500, tokens_cached=18127)
    miss = guard.estimate_usd("gemini-3.1-pro-preview", 20000, 500, tokens_cached=0)
    check("cached input is priced at the cached rate", hit < miss, f"hit ${hit:.4f} vs miss ${miss:.4f}")
    check(
        "the cached count is subtracted, never added",
        abs(hit - ((20000 - 18127) / 1e6 * 2.00 + 18127 / 1e6 * 0.20 + 500 / 1e6 * 12.00)) < 1e-9,
    )
    check(
        "a provider that reports no cached count prices exactly as before",
        guard.estimate_usd("gemini-3.1-pro-preview", 20000, 500) == miss,
    )

    # --- the sweep only touches its own decayed caches --------------------
    fresh_registry()
    sw = FakeClient()
    owner = orch._vertex_cache_owner()
    mine_live = FakeCache("cachedContents/mine-live", None, display_name=owner)
    mine_live.expire_time = now() + datetime.timedelta(minutes=ttl)
    mine_orphan = FakeCache("cachedContents/mine-orphan", None, display_name=owner)
    mine_orphan.expire_time = now() + datetime.timedelta(minutes=1)
    theirs = FakeCache("cachedContents/theirs", None, display_name="metatron:vm:scheduler")
    theirs.expire_time = now() + datetime.timedelta(minutes=1)
    legacy = FakeCache("cachedContents/legacy", None, display_name=None)
    legacy.expire_time = now() + datetime.timedelta(hours=6)
    sw.caches.listed = [mine_live, mine_orphan, theirs, legacy]

    swept = orch._sweep_orphaned_vertex_caches(sw)
    check("the sweep reaps an own decayed orphan", "cachedContents/mine-orphan" in sw.caches.deleted)
    check(
        "the sweep never touches another service's cache",
        "cachedContents/theirs" not in sw.caches.deleted,
        "a sweep by model would have each restart destroying the other unit's live cache",
    )
    check("the sweep leaves its own live cache alone", "cachedContents/mine-live" not in sw.caches.deleted)
    check(
        "the sweep leaves unowned pre-TTL caches to the one-time cleanup",
        "cachedContents/legacy" not in sw.caches.deleted,
    )
    check("the sweep reports what it deleted", swept == 1, str(swept))

    # --- kill switch -------------------------------------------------------
    fresh_registry()
    ks = FakeClient()
    os.environ["VERTEX_CACHE_DISABLED"] = "1"
    try:
        off = orch._get_or_create_vertex_cache(ks, PROMPT, "gemini-3.1-pro-preview", None)
    finally:
        del os.environ["VERTEX_CACHE_DISABLED"]
    check(
        "VERTEX_CACHE_DISABLED creates nothing and returns None",
        off is None and ks.caches.created == [],
    )
    check("the caller falls back to an uncached run on None", off is None)
    fresh_registry()

    print()
    if _failures:
        print(f"FAILED — {len(_failures)}: {', '.join(_failures)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
