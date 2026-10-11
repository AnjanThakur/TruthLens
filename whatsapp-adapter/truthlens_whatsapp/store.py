import hashlib
import hmac
import json
import sqlite3
import time
from contextlib import contextmanager
from uuid import uuid4

from cryptography.fernet import Fernet

from .errors import ServiceError

DDL = """
CREATE TABLE IF NOT EXISTS transport_config (
 id INTEGER PRIMARY KEY, provider TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, sender TEXT NOT NULL, payload TEXT, state TEXT NOT NULL,
 created DOUBLE PRECISION NOT NULL, lease DOUBLE PRECISION NOT NULL DEFAULT 0,
 report TEXT, error TEXT, language TEXT NOT NULL DEFAULT 'en'
);
CREATE INDEX IF NOT EXISTS jobs_pending ON jobs(state, created);
CREATE INDEX IF NOT EXISTS jobs_sender ON jobs(sender, created);
CREATE TABLE IF NOT EXISTS preferences (
 sender TEXT PRIMARY KEY, language TEXT NOT NULL DEFAULT 'en',
 stopped INTEGER NOT NULL DEFAULT 0, updated DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
 id TEXT PRIMARY KEY, job_id TEXT NOT NULL, part INTEGER NOT NULL, body TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'prepared', meta_id TEXT UNIQUE, attempts INTEGER NOT NULL DEFAULT 0,
 due DOUBLE PRECISION NOT NULL DEFAULT 0, created DOUBLE PRECISION NOT NULL,
 UNIQUE(job_id, part)
);
"""


class Store:
    def __init__(self, settings):
        self.settings = settings
        self.pg = settings.database_url.get_secret_value().startswith("postgresql://")
        self.cipher = Fernet(settings.state_encryption_key.get_secret_value().encode())
        with self.tx() as db:
            for statement in DDL.split(";"):
                if statement.strip():
                    self.execute(db, statement)
            provider = self.execute(
                db, "SELECT provider FROM transport_config WHERE id=1"
            ).fetchone()
            if provider and provider["provider"] != settings.messaging_provider:
                raise ValueError("Use a separate database for each messaging provider")
            if not provider:
                # Existing databases predate transport selection and belong to Meta.
                has_jobs = self.execute(db, "SELECT id FROM jobs LIMIT 1").fetchone()
                if has_jobs and settings.messaging_provider != "meta":
                    raise ValueError("Use a new database for Twilio; preserve existing Meta state")
                self.execute(
                    db,
                    "INSERT INTO transport_config(id,provider) VALUES(1,?)",
                    (settings.messaging_provider,),
                )

    def identity(self, value):
        return hmac.new(
            self.settings.identity_hash_secret.get_secret_value().encode(),
            value.encode(),
            hashlib.sha256,
        ).hexdigest()

    def seal(self, value):
        return self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()

    def open(self, value):
        return json.loads(self.cipher.decrypt(value.encode()))

    @contextmanager
    def tx(self):
        if self.pg:
            import psycopg
            from psycopg.rows import dict_row

            db = psycopg.connect(
                self.settings.database_url.get_secret_value(), row_factory=dict_row
            )
        else:
            db = sqlite3.connect(self.settings.sqlite_path(), timeout=10)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def execute(self, db, sql, args=()):
        return db.execute(sql.replace("?", "%s") if self.pg else sql, args)

    def enqueue(self, messages):
        now = time.time()
        with self.tx() as db:
            # Serialize admission across hosts, bounding global and per-sender queues.
            if self.pg:
                self.execute(db, "SELECT pg_advisory_xact_lock(927341)")
            for message in messages:
                key, sender = self.identity(message["id"]), self.identity(message["from"])
                if self.execute(db, "SELECT id FROM jobs WHERE id=?", (key,)).fetchone():
                    continue
                command = message.get("text", {}).get("body", "").strip().upper()
                pending = self.execute(
                    db, "SELECT count(*) AS n FROM jobs WHERE state IN ('received','processing')"
                ).fetchone()["n"]
                recent = self.execute(
                    db,
                    "SELECT count(*) AS n FROM jobs WHERE sender=? AND created>?",
                    (sender, now - 60),
                ).fetchone()["n"]
                if (
                    pending >= self.settings.max_queue_jobs
                    or recent >= self.settings.per_sender_per_minute
                ):
                    if command == "STOP":
                        self._preference(db, sender, stopped=1)
                        self.execute(
                            db,
                            "INSERT INTO jobs(id,sender,state,created,error) VALUES(?,?,'completed',?,'stop_ack_suppressed')",
                            (key, sender, now),
                        )
                        continue  # Opt-out works even when the processing queue is full.
                    raise ServiceError("queue_busy")
                self.execute(
                    db,
                    "INSERT INTO jobs(id,sender,payload,state,created) VALUES(?,?,?,'received',?)",
                    (key, sender, self.seal(message), now),
                )
                command = message.get("text", {}).get("body", "").strip().upper()
                if command == "STOP":
                    self._preference(db, sender, stopped=1)
                elif command == "START":
                    self._preference(db, sender, stopped=0)

    def _preference(self, db, sender, *, language=None, stopped=None):
        row = self.execute(db, "SELECT * FROM preferences WHERE sender=?", (sender,)).fetchone()
        lang = language or (row["language"] if row else "en")
        stop = stopped if stopped is not None else (row["stopped"] if row else 0)
        self.execute(
            db,
            "INSERT INTO preferences(sender,language,stopped,updated) VALUES(?,?,?,?) ON CONFLICT(sender) DO UPDATE SET language=excluded.language,stopped=excluded.stopped,updated=excluded.updated",
            (sender, lang, stop, time.time()),
        )

    def preference(self, sender, language=None):
        with self.tx() as db:
            if language:
                self._preference(db, sender, language=language)
            row = self.execute(db, "SELECT * FROM preferences WHERE sender=?", (sender,)).fetchone()
            return dict(row) if row else {"language": "en", "stopped": 0}

    def claim(self, job_id=None):
        now = time.time()
        with self.tx() as db:
            # A crashed provider call is NOT automatically repeated; it may have consumed credits.
            self.execute(
                db,
                "UPDATE jobs SET state='failed',error='worker_interrupted' WHERE state='processing' AND lease<?",
                (now,),
            )
            scope = " AND j.id=?" if job_id is not None else ""
            sql = (
                "SELECT * FROM jobs j WHERE state='received'"
                + scope
                + " AND NOT EXISTS (SELECT 1 FROM jobs p WHERE p.sender=j.sender AND p.state='processing') ORDER BY created LIMIT 1"
            )
            if self.pg:
                self.execute(db, "SELECT pg_advisory_xact_lock(927342)")
                sql += " FOR UPDATE SKIP LOCKED"
            row = self.execute(db, sql, (job_id,) if job_id is not None else ()).fetchone()
            if not row:
                return None
            self.execute(
                db,
                "UPDATE jobs SET state='processing',lease=? WHERE id=?",
                (now + self.settings.job_lease_seconds, row["id"]),
            )
            return dict(row)

    def finish(self, key, *, report=None, error=None):
        with self.tx() as db:
            self.execute(
                db,
                "UPDATE jobs SET state=?,report=?,error=? WHERE id=?",
                (
                    "failed" if error else "completed",
                    self.seal(report) if report else None,
                    error,
                    key,
                ),
            )

    def refresh_payload(self, job, message):
        encrypted = self.seal(message)
        with self.tx() as db:
            self.execute(db, "UPDATE jobs SET payload=? WHERE id=?", (encrypted, job["id"]))
        job["payload"] = encrypted

    def last_report(self, sender):
        with self.tx() as db:
            row = self.execute(
                db,
                "SELECT report FROM jobs WHERE sender=? AND report IS NOT NULL AND created>? ORDER BY created DESC LIMIT 1",
                (sender, time.time() - self.settings.content_retention_hours * 3600),
            ).fetchone()
            return self.open(row["report"]) if row else None

    def prepare(self, job_id, bodies):
        with self.tx() as db:
            for part, body in enumerate(bodies):
                self.execute(
                    db,
                    "INSERT INTO outbox(id,job_id,part,body,created) VALUES(?,?,?,?,?) ON CONFLICT(job_id,part) DO NOTHING",
                    (str(uuid4()), job_id, part, self.seal(body), time.time()),
                )

    def next_send(self, job_id=None):
        with self.tx() as db:
            scope = " AND o.job_id=?" if job_id is not None else ""
            sql = (
                "SELECT o.*,j.payload,j.sender FROM outbox o JOIN jobs j ON j.id=o.job_id WHERE o.state='prepared' AND o.due<=?"
                + scope
                + " AND j.payload IS NOT NULL AND NOT EXISTS(SELECT 1 FROM outbox p WHERE p.job_id=o.job_id AND p.part<o.part AND p.state NOT IN ('accepted','sent','delivered','read')) ORDER BY o.created,o.part LIMIT 1"
            )
            if self.pg:
                sql += " FOR UPDATE OF o SKIP LOCKED"
            args = (time.time(), job_id) if job_id is not None else (time.time(),)
            row = self.execute(db, sql, args).fetchone()
            if row:
                self.execute(
                    db,
                    "UPDATE outbox SET state='sending',attempts=attempts+1,due=? WHERE id=?",
                    (time.time(), row["id"]),
                )
                return dict(row)
            return None

    def send_state(self, key, state, meta_id=None, delay=0):
        with self.tx() as db:
            self.execute(
                db,
                "UPDATE outbox SET state=CASE WHEN state IN ('delivered','read','sent') THEN state ELSE ? END,meta_id=COALESCE(?,meta_id),due=? WHERE id=?",
                (state, meta_id, time.time() + delay, key),
            )

    def delivery(self, status):
        state = status.get("status")
        if state not in {"sent", "delivered", "read", "failed"}:
            return
        with self.tx() as db:
            row = self.execute(
                db,
                "SELECT * FROM outbox WHERE meta_id=? OR id=?",
                (status.get("id"), status.get("biz_opaque_callback_data")),
            ).fetchone()
            if row:
                rank = {"sent": 1, "delivered": 2, "read": 3}
                if state == "failed" and row["state"] in {"delivered", "read"}:
                    return
                if state != "failed" and rank.get(state, 0) < rank.get(row["state"], 0):
                    return
                self.execute(
                    db,
                    "UPDATE outbox SET state=?,meta_id=COALESCE(meta_id,?) WHERE id=?",
                    (state, status.get("id"), row["id"]),
                )

    def cleanup(self):
        now = time.time()
        with self.tx() as db:
            self.execute(
                db,
                "UPDATE outbox SET state='uncertain' WHERE state='sending' AND due<?",
                (now - 120,),
            )
            self.execute(
                db,
                "DELETE FROM outbox WHERE created<?",
                (now - self.settings.content_retention_hours * 3600,),
            )
            self.execute(
                db,
                "UPDATE jobs SET payload=NULL,report=NULL WHERE created<?",
                (now - self.settings.content_retention_hours * 3600,),
            )
            if self.settings.messaging_provider != "twilio":
                self.execute(
                    db,
                    "DELETE FROM jobs WHERE created<?",
                    (now - self.settings.dedup_retention_days * 86400,),
                )
            # Twilio signatures have no timestamp: retain content-free hashed SID
            # tombstones so replaying an old signed event cannot create a new job.
