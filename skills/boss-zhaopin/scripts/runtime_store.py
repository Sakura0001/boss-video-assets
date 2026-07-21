#!/usr/bin/env python3

import argparse
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
RUNTIME_TTL = timedelta(days=3)
FOLLOWUP_INTERVAL = timedelta(hours=6)
MAX_GENERAL_FOLLOWUPS = 8
MAX_APPLICATION_STATUS_QUESTIONS = 2
DEDUPE_EXPIRES_AT = datetime(2027, 12, 31, 23, 59, 59, tzinfo=TZ)


def default_state_dir() -> Path:
    configured = os.environ.get("BOSS_ZHAOPIN_STATE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex" / "state" / "boss-zhaopin"


def default_db_path() -> Path:
    return default_state_dir() / "state.sqlite3"


@dataclass(frozen=True)
class TransferDecision:
    action: str
    reason: str


def evaluate_transfer(
    application_target: str,
    psych_status: str,
    interview_status: str,
    written_status: str,
) -> TransferDecision:
    if application_target == "cloud_software":
        return TransferDecision("stop", "already_cloud_software_department")
    if psych_status == "failed":
        return TransferDecision("stop", "psychological_assessment_failed")
    if interview_status == "started":
        return TransferDecision("stop", "interview_already_started")
    if application_target == "none":
        return TransferDecision("exchange_wechat", "not_submitted")
    if interview_status == "unknown":
        return TransferDecision("ask_process_stage", "interview_status_unknown")
    if application_target not in {"other", "unknown"}:
        return TransferDecision("ask_application_target", "application_target_unknown")
    if written_status == "failed":
        return TransferDecision("exchange_wechat", "written_exam_retest_allowed")
    return TransferDecision("exchange_wechat", "transfer_before_interview_allowed")


def _coerce_datetime(value: Union[str, datetime]) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed.astimezone(TZ)


def _iso(value: Union[str, datetime]) -> str:
    return _coerce_datetime(value).isoformat()


class RuntimeStore:
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = Path(db_path).expanduser() if db_path is not None else default_db_path()
        self.conn: Optional[sqlite3.Connection] = None

    def init(self) -> "RuntimeStore":
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt":
            os.chmod(self.db_path.parent, 0o700)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL,
                school TEXT NOT NULL DEFAULT '',
                major TEXT NOT NULL DEFAULT '',
                degree TEXT NOT NULL DEFAULT '',
                grad_year INTEGER,
                application_status TEXT NOT NULL DEFAULT '',
                original_department TEXT NOT NULL DEFAULT '',
                last_contact_at TEXT,
                followup_count INTEGER NOT NULL DEFAULT 0,
                followup_variant INTEGER NOT NULL DEFAULT 0,
                manual_takeover INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dedupe (
                candidate_id TEXT PRIMARY KEY,
                first_contact_at TEXT NOT NULL,
                final_status TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                candidate_id TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS events_day_type
                ON events(occurred_at, event_type);
            CREATE TABLE IF NOT EXISTS wechat_ledger (
                candidate_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                exchanged_at TEXT NOT NULL,
                school TEXT NOT NULL DEFAULT '',
                major TEXT NOT NULL DEFAULT '',
                degree TEXT NOT NULL DEFAULT '',
                application_status TEXT NOT NULL DEFAULT '',
                original_department TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT ''
            );
            """
        )
        self.conn.commit()
        if os.name != "nt":
            os.chmod(self.db_path, 0o600)
        return self

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _db(self) -> sqlite3.Connection:
        if self.conn is None:
            self.init()
        assert self.conn is not None
        return self.conn

    @staticmethod
    def _row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        return dict(row) if row is not None else None

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        row = self._db().execute(
            "SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        return self._row(row)

    def upsert_candidate(
        self,
        candidate_id: str,
        display_name: str,
        stage: str,
        now: Union[str, datetime],
        school: Optional[str] = None,
        major: Optional[str] = None,
        degree: Optional[str] = None,
        grad_year: Optional[int] = None,
        application_status: Optional[str] = None,
        original_department: Optional[str] = None,
        last_contact_at: Optional[Union[str, datetime]] = None,
        followup_count: Optional[int] = None,
        followup_variant: Optional[int] = None,
        manual_takeover: Optional[bool] = None,
    ) -> Dict[str, Any]:
        current = self.get_candidate(candidate_id) or {}
        now_dt = _coerce_datetime(now)
        values = {
            "candidate_id": candidate_id,
            "display_name": display_name or current.get("display_name", ""),
            "stage": stage,
            "school": current.get("school", "") if school is None else school,
            "major": current.get("major", "") if major is None else major,
            "degree": current.get("degree", "") if degree is None else degree,
            "grad_year": current.get("grad_year") if grad_year is None else grad_year,
            "application_status": current.get("application_status", "")
            if application_status is None
            else application_status,
            "original_department": current.get("original_department", "")
            if original_department is None
            else original_department,
            "last_contact_at": current.get("last_contact_at")
            if last_contact_at is None
            else _iso(last_contact_at),
            "followup_count": current.get("followup_count", 0)
            if followup_count is None
            else followup_count,
            "followup_variant": current.get("followup_variant", 0)
            if followup_variant is None
            else followup_variant,
            "manual_takeover": current.get("manual_takeover", 0)
            if manual_takeover is None
            else int(manual_takeover),
            "updated_at": now_dt.isoformat(),
            "expires_at": (now_dt + RUNTIME_TTL).isoformat(),
        }
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        updates = ", ".join(
            f"{column}=excluded.{column}" for column in values if column != "candidate_id"
        )
        with self._db():
            self._db().execute(
                f"INSERT INTO candidates ({columns}) VALUES ({placeholders}) "
                f"ON CONFLICT(candidate_id) DO UPDATE SET {updates}",
                tuple(values.values()),
            )
        result = self.get_candidate(candidate_id)
        assert result is not None
        return result

    def due_followups(self, as_of: Union[str, datetime]) -> List[Dict[str, Any]]:
        as_of_dt = _coerce_datetime(as_of)
        threshold = (as_of_dt - FOLLOWUP_INTERVAL).isoformat()
        rows = self._db().execute(
            """
            SELECT * FROM candidates
            WHERE stage IN ('greeted', 'waiting_resume', 'waiting_application_status')
              AND manual_takeover = 0
              AND last_contact_at IS NOT NULL
              AND last_contact_at <= ?
              AND expires_at > ?
              AND (
                    (stage = 'waiting_application_status' AND followup_count < ?)
                 OR (stage != 'waiting_application_status' AND followup_count < ?)
              )
            ORDER BY last_contact_at, candidate_id
            """,
            (
                threshold,
                as_of_dt.isoformat(),
                MAX_APPLICATION_STATUS_QUESTIONS,
                MAX_GENERAL_FOLLOWUPS,
            ),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_followup_sent(
        self, candidate_id: str, variant: int, at: Union[str, datetime]
    ) -> Dict[str, Any]:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")
        limit = (
            MAX_APPLICATION_STATUS_QUESTIONS
            if candidate["stage"] == "waiting_application_status"
            else MAX_GENERAL_FOLLOWUPS
        )
        if candidate["followup_count"] >= limit:
            raise ValueError(f"follow-up limit reached for {candidate_id}")
        return self.upsert_candidate(
            candidate_id=candidate_id,
            display_name=candidate["display_name"],
            stage=candidate["stage"],
            now=at,
            last_contact_at=at,
            followup_count=candidate["followup_count"] + 1,
            followup_variant=variant,
        )

    def mark_manual_takeover(
        self, candidate_id: str, at: Union[str, datetime]
    ) -> Dict[str, Any]:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")
        return self.upsert_candidate(
            candidate_id=candidate_id,
            display_name=candidate["display_name"],
            stage="manual_takeover",
            now=at,
            manual_takeover=True,
        )

    def purge_runtime(self, as_of: Union[str, datetime]) -> int:
        with self._db():
            cursor = self._db().execute(
                "DELETE FROM candidates WHERE expires_at <= ?", (_iso(as_of),)
            )
        return cursor.rowcount

    def mark_deduped(
        self,
        candidate_id: str,
        status: str,
        at: Union[str, datetime],
        expires_at: Union[str, datetime] = DEDUPE_EXPIRES_AT,
    ) -> None:
        with self._db():
            self._db().execute(
                """
                INSERT INTO dedupe(candidate_id, first_contact_at, final_status, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    final_status = excluded.final_status,
                    expires_at = excluded.expires_at
                """,
                (candidate_id, _iso(at), status, _iso(expires_at)),
            )

    def is_deduped(self, candidate_id: str, at: Union[str, datetime]) -> bool:
        row = self._db().execute(
            "SELECT 1 FROM dedupe WHERE candidate_id = ? AND expires_at >= ?",
            (candidate_id, _iso(at)),
        ).fetchone()
        return row is not None

    def record_event(
        self,
        event_type: str,
        at: Union[str, datetime],
        candidate_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload_json = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
        with self._db():
            self._db().execute(
                "INSERT INTO events(event_type, occurred_at, candidate_id, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (event_type, _iso(at), candidate_id, payload_json),
            )

    def complete_wechat(
        self,
        candidate_id: str,
        display_name: str,
        exchanged_at: Union[str, datetime],
        school: str,
        major: str,
        degree: str,
        application_status: str,
        original_department: str,
        note: str,
    ) -> None:
        exchanged = _coerce_datetime(exchanged_at)
        expires = (exchanged + RUNTIME_TTL).isoformat()
        dedupe_expires = DEDUPE_EXPIRES_AT.isoformat()
        payload_json = json.dumps(
            {"application_status": application_status}, ensure_ascii=False, sort_keys=True
        )
        db = self._db()
        with db:
            db.execute(
                """
                INSERT INTO candidates(
                    candidate_id, display_name, stage, school, major, degree,
                    application_status, original_department, updated_at, expires_at
                ) VALUES (?, ?, 'wechat_exchange_completed', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    stage='wechat_exchange_completed',
                    school=excluded.school,
                    major=excluded.major,
                    degree=excluded.degree,
                    application_status=excluded.application_status,
                    original_department=excluded.original_department,
                    updated_at=excluded.updated_at,
                    expires_at=excluded.expires_at
                """,
                (
                    candidate_id,
                    display_name,
                    school,
                    major,
                    degree,
                    application_status,
                    original_department,
                    exchanged.isoformat(),
                    expires,
                ),
            )
            db.execute(
                """
                INSERT INTO dedupe(candidate_id, first_contact_at, final_status, expires_at)
                VALUES (?, ?, 'wechat_exchange_completed', ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    final_status='wechat_exchange_completed',
                    expires_at=excluded.expires_at
                """,
                (candidate_id, exchanged.isoformat(), dedupe_expires),
            )
            db.execute(
                """
                INSERT INTO wechat_ledger(
                    candidate_id, display_name, exchanged_at, school, major, degree,
                    application_status, original_department, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    exchanged_at=excluded.exchanged_at,
                    school=excluded.school,
                    major=excluded.major,
                    degree=excluded.degree,
                    application_status=excluded.application_status,
                    original_department=excluded.original_department,
                    note=excluded.note
                """,
                (
                    candidate_id,
                    display_name,
                    exchanged.isoformat(),
                    school,
                    major,
                    degree,
                    application_status,
                    original_department,
                    note,
                ),
            )
            db.execute(
                "INSERT INTO events(event_type, occurred_at, candidate_id, payload_json) "
                "VALUES ('wechat_exchange_completed', ?, ?, ?)",
                (exchanged.isoformat(), candidate_id, payload_json),
            )

    def wechat_ledger(self) -> List[Dict[str, Any]]:
        rows = self._db().execute(
            "SELECT * FROM wechat_ledger ORDER BY exchanged_at, candidate_id"
        ).fetchall()
        return [dict(row) for row in rows]

    def greeting_count(self, date: str) -> int:
        row = self._db().execute(
            "SELECT COUNT(*) AS count FROM events "
            "WHERE event_type = 'greeted' AND substr(occurred_at, 1, 10) = ?",
            (date,),
        ).fetchone()
        return int(row["count"])

    def _event_count(self, date: str, event_type: str) -> int:
        row = self._db().execute(
            "SELECT COUNT(*) AS count FROM events "
            "WHERE event_type = ? AND substr(occurred_at, 1, 10) = ?",
            (event_type, date),
        ).fetchone()
        return int(row["count"])

    def daily_report(self, date: str) -> str:
        labels = [
            ("主动打招呼数", "greeted"),
            ("候选人回复数", "candidate_replied"),
            ("收到简历数", "resume_received"),
            ("确认未投递数", "confirmed_unsubmitted"),
            ("确认非云软件研发部数", "confirmed_non_cloud_software"),
            ("完成微信交换数", "wechat_exchange_completed"),
        ]
        counts = {event: self._event_count(date, event) for _, event in labels}
        lines = [f"# {date} 招聘日报", ""]
        lines.extend(f"- {label}：{counts[event]}" for label, event in labels)

        greeted = counts["greeted"]
        replied = counts["candidate_replied"]
        resumes = counts["resume_received"]
        exchanged = counts["wechat_exchange_completed"]

        def rate(numerator: int, denominator: int) -> str:
            return "N/A" if denominator == 0 else f"{numerator / denominator:.1%}"

        lines.extend(
            [
                "",
                "## 转化率",
                f"- 回复/招呼：{rate(replied, greeted)}",
                f"- 简历/回复：{rate(resumes, replied)}",
                f"- 微信交换/简历：{rate(exchanged, resumes)}",
            ]
        )

        ledger = self._db().execute(
            "SELECT * FROM wechat_ledger WHERE substr(exchanged_at, 1, 10) = ? "
            "ORDER BY exchanged_at, candidate_id",
            (date,),
        ).fetchall()
        lines.extend(["", "## 完成微信交换的候选人"])
        if not ledger:
            lines.append("- 无记录")
        else:
            for row in ledger:
                detail = " / ".join(
                    value
                    for value in [
                        row["school"],
                        row["major"],
                        row["degree"],
                        row["application_status"],
                        row["original_department"],
                    ]
                    if value
                )
                suffix = f"（{detail}）" if detail else ""
                lines.append(f"- {row['display_name']}，{row['exchanged_at']}{suffix}")

        stopped = self._db().execute(
            "SELECT payload_json FROM events WHERE event_type = 'stopped' "
            "AND substr(occurred_at, 1, 10) = ?",
            (date,),
        ).fetchall()
        reasons: Dict[str, int] = {}
        for row in stopped:
            reason = json.loads(row["payload_json"]).get("reason", "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
        lines.extend(["", "## 停止联系"])
        if reasons:
            lines.extend(f"- {reason}：{count}" for reason, count in sorted(reasons.items()))
        else:
            lines.append("- 无记录")

        gaps = self._db().execute(
            "SELECT payload_json FROM events WHERE event_type = 'knowledge_gap' "
            "AND substr(occurred_at, 1, 10) = ? ORDER BY id",
            (date,),
        ).fetchall()
        lines.extend(["", "## 知识库未覆盖问题"])
        summaries = [json.loads(row["payload_json"]).get("summary", "未分类") for row in gaps]
        lines.extend((f"- {summary}" for summary in summaries),)
        if not summaries:
            lines.append("- 无记录")
        return "\n".join(lines)


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Boss recruiting local runtime state")
    parser.add_argument("--db", default=str(default_db_path()))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    purge = sub.add_parser("purge")
    purge.add_argument("--as-of", required=True)

    upsert = sub.add_parser("candidate-upsert")
    upsert.add_argument("--candidate-id", required=True)
    upsert.add_argument("--display-name", required=True)
    upsert.add_argument("--stage", required=True)
    upsert.add_argument("--now", required=True)
    upsert.add_argument("--school")
    upsert.add_argument("--major")
    upsert.add_argument("--degree")
    upsert.add_argument("--grad-year", type=int)
    upsert.add_argument("--application-status")
    upsert.add_argument("--original-department")
    upsert.add_argument("--last-contact-at")
    upsert.add_argument("--followup-count", type=int)
    upsert.add_argument("--followup-variant", type=int)
    upsert.add_argument("--manual-takeover", type=_parse_bool)

    get = sub.add_parser("candidate-get")
    get.add_argument("--candidate-id", required=True)

    due = sub.add_parser("due-followups")
    due.add_argument("--as-of", required=True)

    followup = sub.add_parser("followup-sent")
    followup.add_argument("--candidate-id", required=True)
    followup.add_argument("--variant", type=int, required=True)
    followup.add_argument("--at", required=True)

    manual = sub.add_parser("manual-takeover")
    manual.add_argument("--candidate-id", required=True)
    manual.add_argument("--at", required=True)

    check = sub.add_parser("dedupe-check")
    check.add_argument("--candidate-id", required=True)
    check.add_argument("--at", required=True)

    dedupe = sub.add_parser("dedupe-add")
    dedupe.add_argument("--candidate-id", required=True)
    dedupe.add_argument("--status", required=True)
    dedupe.add_argument("--at", required=True)

    event = sub.add_parser("record-event")
    event.add_argument("--type", required=True)
    event.add_argument("--candidate-id")
    event.add_argument("--at", required=True)
    event.add_argument("--payload", default="{}")

    decision = sub.add_parser("evaluate-transfer")
    decision.add_argument(
        "--application-target", choices=["none", "cloud_software", "other", "unknown"], required=True
    )
    decision.add_argument(
        "--psych-status", choices=["not_taken", "passed", "failed", "unknown"], required=True
    )
    decision.add_argument(
        "--interview-status", choices=["not_started", "started", "unknown"], required=True
    )
    decision.add_argument(
        "--written-status", choices=["not_taken", "passed", "failed", "unknown"], required=True
    )

    wechat = sub.add_parser("wechat-complete")
    wechat.add_argument("--candidate-id", required=True)
    wechat.add_argument("--display-name", required=True)
    wechat.add_argument("--exchanged-at", required=True)
    wechat.add_argument("--school", default="")
    wechat.add_argument("--major", default="")
    wechat.add_argument("--degree", default="")
    wechat.add_argument("--application-status", default="")
    wechat.add_argument("--original-department", default="")
    wechat.add_argument("--note", default="")

    count = sub.add_parser("greeting-count")
    count.add_argument("--date", required=True)

    report = sub.add_parser("daily-report")
    report.add_argument("--date", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    store = RuntimeStore(args.db).init()
    try:
        if args.command == "init":
            _print_json({"db": str(store.db_path)})
        elif args.command == "purge":
            _print_json({"removed": store.purge_runtime(args.as_of)})
        elif args.command == "candidate-upsert":
            values = vars(args).copy()
            for key in ["command", "db"]:
                values.pop(key)
            candidate_id = values.pop("candidate_id")
            display_name = values.pop("display_name")
            stage = values.pop("stage")
            now = values.pop("now")
            _print_json(store.upsert_candidate(candidate_id, display_name, stage, now, **values))
        elif args.command == "candidate-get":
            _print_json(store.get_candidate(args.candidate_id))
        elif args.command == "due-followups":
            _print_json(store.due_followups(args.as_of))
        elif args.command == "followup-sent":
            _print_json(store.mark_followup_sent(args.candidate_id, args.variant, args.at))
        elif args.command == "manual-takeover":
            _print_json(store.mark_manual_takeover(args.candidate_id, args.at))
        elif args.command == "dedupe-check":
            _print_json({"deduped": store.is_deduped(args.candidate_id, args.at)})
        elif args.command == "dedupe-add":
            store.mark_deduped(args.candidate_id, args.status, args.at)
            _print_json({"deduped": True})
        elif args.command == "record-event":
            store.record_event(args.type, args.at, args.candidate_id, json.loads(args.payload))
            _print_json({"recorded": True})
        elif args.command == "evaluate-transfer":
            result = evaluate_transfer(
                args.application_target, args.psych_status, args.interview_status, args.written_status
            )
            _print_json(asdict(result))
        elif args.command == "wechat-complete":
            store.complete_wechat(
                args.candidate_id,
                args.display_name,
                args.exchanged_at,
                args.school,
                args.major,
                args.degree,
                args.application_status,
                args.original_department,
                args.note,
            )
            _print_json({"completed": True})
        elif args.command == "greeting-count":
            _print_json({"count": store.greeting_count(args.date)})
        elif args.command == "daily-report":
            print(store.daily_report(args.date))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
