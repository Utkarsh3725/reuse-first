"""Tiny SQLite TTL cache with ETag support, so repeat searches cost no API quota."""
import json
import sqlite3
import threading
import time


class Cache:
    def __init__(self, path: str = "cache.db", ttl: int = 6 * 3600):
        self.ttl = ttl
        self.lock = threading.Lock()  # one connection shared by worker threads
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT, etag TEXT, ts REAL)"
        )

    def get(self, key: str, allow_stale: bool = False):
        with self.lock:
            row = self.db.execute("SELECT v, etag, ts FROM kv WHERE k=?", (key,)).fetchone()
        if not row:
            return None, None
        value, etag, ts = row
        fresh = time.time() - ts < self.ttl
        if fresh or allow_stale:
            return json.loads(value), etag
        return None, etag  # stale: caller may revalidate with the etag

    def put(self, key: str, value, etag: str | None = None):
        with self.lock:
            self.db.execute(
                "REPLACE INTO kv VALUES (?,?,?,?)",
                (key, json.dumps(value), etag, time.time()),
            )
            self.db.commit()
