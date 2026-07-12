#!/usr/bin/env python3

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from runtime_store import RuntimeStore, evaluate_transfer


TZ = ZoneInfo("Asia/Shanghai")


def at(hour: int, day: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, 0, tzinfo=TZ)


class TransferDecisionTest(unittest.TestCase):
    def test_cloud_software_history_stops_transfer(self):
        decision = evaluate_transfer("cloud_software", "passed", "not_started", "passed")
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.reason, "already_cloud_software_department")

    def test_failed_psychological_assessment_stops_transfer(self):
        decision = evaluate_transfer("other", "failed", "not_started", "not_taken")
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.reason, "psychological_assessment_failed")

    def test_started_interview_stops_transfer(self):
        decision = evaluate_transfer("other", "passed", "started", "passed")
        self.assertEqual(decision.action, "stop")
        self.assertEqual(decision.reason, "interview_already_started")

    def test_failed_written_exam_can_retest_without_waiting(self):
        decision = evaluate_transfer("other", "passed", "not_started", "failed")
        self.assertEqual(decision.action, "exchange_wechat")
        self.assertEqual(decision.reason, "written_exam_retest_allowed")

    def test_unsubmitted_candidate_can_exchange_wechat(self):
        decision = evaluate_transfer("none", "not_taken", "not_started", "not_taken")
        self.assertEqual(decision.action, "exchange_wechat")
        self.assertEqual(decision.reason, "not_submitted")

    def test_unknown_interview_stage_must_be_asked(self):
        decision = evaluate_transfer("other", "passed", "unknown", "passed")
        self.assertEqual(decision.action, "ask_process_stage")


class RuntimeStoreTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "state" / "state.sqlite3"
        self.store = RuntimeStore(self.db_path)
        self.store.init()

    def tearDown(self):
        self.store.close()
        self.tempdir.cleanup()

    def test_database_permissions_are_private(self):
        self.assertEqual(os.stat(self.db_path.parent).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(self.db_path).st_mode & 0o777, 0o600)

    def test_due_followups_respect_six_hours_eight_limit_and_manual_takeover(self):
        now = at(12)
        cases = [
            ("too-soon", at(7), 0, False, "waiting_resume"),
            ("due", at(6), 2, False, "waiting_resume"),
            ("maxed", at(1), 8, False, "waiting_resume"),
            ("manual", at(1), 1, True, "waiting_resume"),
            ("terminal", at(1), 1, False, "stopped"),
        ]
        for candidate_id, last_contact, count, manual, stage in cases:
            self.store.upsert_candidate(
                candidate_id=candidate_id,
                display_name=candidate_id,
                stage=stage,
                now=last_contact,
                last_contact_at=last_contact,
                followup_count=count,
                manual_takeover=manual,
            )

        due = self.store.due_followups(now)
        self.assertEqual([row["candidate_id"] for row in due], ["due"])

    def test_followup_sent_increments_count_and_rotates_variant(self):
        self.store.upsert_candidate(
            candidate_id="candidate-1",
            display_name="同学甲",
            stage="waiting_resume",
            now=at(1),
            last_contact_at=at(1),
        )
        updated = self.store.mark_followup_sent("candidate-1", variant=3, at=at(7))
        self.assertEqual(updated["followup_count"], 1)
        self.assertEqual(updated["followup_variant"], 3)
        self.assertEqual(updated["last_contact_at"], at(7).isoformat())

    def test_manual_takeover_suppresses_due_followup(self):
        self.store.upsert_candidate(
            candidate_id="candidate-1",
            display_name="同学甲",
            stage="waiting_resume",
            now=at(1),
            last_contact_at=at(1),
        )
        self.store.mark_manual_takeover("candidate-1", at(2))
        self.assertEqual(self.store.due_followups(at(12)), [])

    def test_purge_removes_three_day_runtime_but_preserves_long_term_data(self):
        created = at(9, day=1)
        self.store.upsert_candidate(
            candidate_id="expired",
            display_name="过期同学",
            stage="waiting_resume",
            now=created,
            last_contact_at=created,
        )
        self.store.mark_deduped("expired", "contacted", created)
        self.store.complete_wechat(
            candidate_id="success",
            display_name="成功同学",
            exchanged_at=at(10, day=1),
            school="测试大学",
            major="计算机科学",
            degree="硕士",
            application_status="未投递",
            original_department="",
            note="",
        )

        removed = self.store.purge_runtime(at(10, day=5))

        self.assertEqual(removed, 2)
        self.assertIsNone(self.store.get_candidate("expired"))
        self.assertTrue(self.store.is_deduped("expired", at(10, day=5)))
        self.assertEqual(self.store.wechat_ledger()[0]["display_name"], "成功同学")

    def test_complete_wechat_updates_all_state_atomically(self):
        self.store.upsert_candidate(
            candidate_id="candidate-1",
            display_name="张同学",
            stage="handoff_eligible",
            now=at(8),
            last_contact_at=at(8),
        )
        self.store.complete_wechat(
            candidate_id="candidate-1",
            display_name="张同学",
            exchanged_at=at(9),
            school="目标大学",
            major="电子信息",
            degree="硕士",
            application_status="已投其他部门",
            original_department="终端",
            note="微信备注姓名",
        )

        candidate = self.store.get_candidate("candidate-1")
        self.assertEqual(candidate["stage"], "wechat_exchange_completed")
        self.assertTrue(self.store.is_deduped("candidate-1", at(10)))
        ledger = self.store.wechat_ledger()
        self.assertEqual(ledger[0]["display_name"], "张同学")
        self.assertEqual(ledger[0]["original_department"], "终端")

    def test_daily_report_contains_funnel_counts_stop_reasons_and_names(self):
        day = "2026-07-10"
        events = [
            ("greeted", "c1", {}),
            ("candidate_replied", "c1", {}),
            ("resume_received", "c1", {}),
            ("confirmed_unsubmitted", "c1", {}),
            ("confirmed_non_cloud_software", "c2", {}),
            ("stopped", "c3", {"reason": "interview_already_started"}),
            ("knowledge_gap", "c4", {"summary": "补充住房福利口径"}),
        ]
        for event_type, candidate_id, payload in events:
            self.store.record_event(event_type, at(8), candidate_id, payload)
        self.store.complete_wechat(
            candidate_id="c1",
            display_name="李同学",
            exchanged_at=at(9),
            school="目标大学",
            major="数学",
            degree="本科",
            application_status="未投递",
            original_department="",
            note="",
        )

        report = self.store.daily_report(day)

        self.assertIn("2026-07-10 招聘日报", report)
        self.assertIn("主动打招呼数：1", report)
        self.assertIn("完成微信交换数：1", report)
        self.assertIn("李同学", report)
        self.assertIn("interview_already_started：1", report)
        self.assertIn("补充住房福利口径", report)

    def test_greeting_count_supports_daily_cap(self):
        for index in range(3):
            self.store.record_event("greeted", at(8) + timedelta(minutes=index), f"c{index}", {})
        self.assertEqual(self.store.greeting_count("2026-07-10"), 3)

    def test_event_payload_must_be_json_serializable(self):
        with self.assertRaises(TypeError):
            self.store.record_event("greeted", at(8), "c1", {"bad": object()})


if __name__ == "__main__":
    unittest.main(verbosity=2)
