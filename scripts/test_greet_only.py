import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.greet_only import (
    CampaignError,
    CampaignRunner,
    Candidate,
    EligibilityPolicy,
    GreetingKnowledgeBaseError,
    load_greeting_messages,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


class FakeBoss:
    def __init__(self, batches):
        self.batches = list(batches)
        self.recommend_calls = []
        self.greeted = []
        self.chat_calls = []
        self.sent = []
        self.fail_send_at = None

    def recommend(self, job, refresh):
        self.recommend_calls.append((job, refresh))
        if not self.batches:
            return []
        return self.batches.pop(0)

    def greet(self, candidate, job):
        self.greeted.append((candidate.geek_id, candidate.name, job))

    def open_exact_chat(self, candidate, job):
        self.chat_calls.append((candidate.name, job))
        return "\n".join(
            [
                f"成功进入候选人聊天：{candidate.name}",
                f"姓名: {candidate.name}",
                f"沟通职位: {job}",
                *[f"[you] {message}" for message in self.sent],
            ]
        )

    def send(self, message):
        if self.fail_send_at is not None and len(self.sent) == self.fail_send_at:
            raise CampaignError("send failed")
        self.sent.append(message)


class FakeStore:
    def __init__(self, count=0, deduped=None):
        self.count = count
        self.deduped = set(deduped or [])
        self.events = []
        self.states = []

    def greeting_count(self, date):
        return self.count

    def is_deduped(self, candidate_id, at):
        return candidate_id in self.deduped

    def record_greeted(self, candidate, eligibility, job, at):
        self.count += 1
        self.deduped.add(candidate.geek_id)
        self.events.append((candidate.geek_id, job, at))

    def mark_waiting_resume(self, candidate, eligibility, at):
        self.states.append((candidate.geek_id, "waiting_resume", at))


def candidate(
    geek_id="c1",
    name="候选人",
    base_info="27年应届生 / 博士",
    experience="浙江大学 人工智能",
    advantage="",
    highlights=None,
    can_greet=True,
):
    return Candidate(
        geek_id=geek_id,
        name=name,
        base_info=base_info,
        expect="上海 算法工程师",
        experience=experience,
        advantage=advantage,
        highlights=tuple(highlights or ()),
        can_greet=can_greet,
        has_history_chat=False,
        has_viewed=False,
    )


class GreetingKnowledgeBaseTests(unittest.TestCase):
    def test_loads_exact_messages_in_required_order(self):
        content = """# 主动打招呼话术

### 真人化说明

`第一条原文`

### 一条合并岗位介绍

`第二条原文`

### 索要附件简历

`第三条原文`
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "greetings.md"
            path.write_text(content, encoding="utf-8")
            self.assertEqual(
                load_greeting_messages(path),
                ("第一条原文", "第二条原文", "第三条原文"),
            )

    def test_missing_message_fails_instead_of_generating_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "greetings.md"
            path.write_text("### 真人化说明\n\n`只有一条`\n", encoding="utf-8")
            with self.assertRaises(GreetingKnowledgeBaseError):
                load_greeting_messages(path)


class EligibilityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = EligibilityPolicy(
            schools=("浙江大学", "中国科学院大学", "上海交通大学"),
            aliases={"浙大": "浙江大学", "国科大": "中国科学院大学"},
            majors=("人工智能", "计算机科学与技术", "集成电路工程"),
        )

    def test_accepts_candidate_when_every_gate_is_visible(self):
        result = self.policy.evaluate(candidate())
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "浙江大学")
        self.assertEqual(result.major, "人工智能")
        self.assertEqual(result.degree, "博士")

    def test_rejects_unknown_school(self):
        result = self.policy.evaluate(
            candidate(experience="某大学 人工智能", advantage="大模型方向")
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "school_unknown_or_ineligible")

    def test_rejects_wrong_graduation_year(self):
        result = self.policy.evaluate(candidate(base_info="28年应届生 / 硕士"))
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "graduation_year")

    def test_rejects_major_not_in_knowledge_base(self):
        result = self.policy.evaluate(candidate(experience="浙江大学 气象学"))
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "major_unknown_or_ineligible")

    def test_rejects_target_bachelor_school_when_final_master_school_is_not_target(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                experience="本科-浙江大学-人工智能 / 硕士-某大学-人工智能",
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "school_unknown_or_ineligible")

    def test_accepts_target_final_master_school(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                experience="本科-某大学-数学 / 硕士-上海交通大学-计算机科学与技术",
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "上海交通大学")

    def test_uses_compact_card_summary_when_no_education_sequence_is_visible(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                experience="",
                advantage="上海交通大学人工智能方向，2027年毕业",
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "上海交通大学")


class CampaignRunnerTests(unittest.TestCase):
    def setUp(self):
        self.policy = EligibilityPolicy(
            schools=("浙江大学",),
            aliases={},
            majors=("人工智能",),
        )
        self.messages = ("知识库一", "知识库二", "知识库三")
        self.now = lambda: datetime(2026, 7, 23, 10, 0, tzinfo=SHANGHAI)

    def runner(self, boss, store, target=150, max_scans=150):
        return CampaignRunner(
            boss=boss,
            store=store,
            policy=self.policy,
            messages=self.messages,
            job="ai应用研发工程师",
            target=target,
            max_scans=max_scans,
            now=self.now,
        )

    def test_refreshes_after_ten_distinct_unqualified_candidates(self):
        unqualified = [
            candidate(
                geek_id=f"bad-{index}",
                name=f"不合格{index}",
                experience="某大学 气象学",
            )
            for index in range(10)
        ]
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([unqualified, [good]])
        store = FakeStore()

        result = self.runner(boss, store, target=1).run()

        self.assertEqual(result.final_count, 1)
        self.assertEqual(
            boss.recommend_calls,
            [
                ("ai应用研发工程师", False),
                ("ai应用研发工程师", True),
            ],
        )

    def test_sends_only_the_three_knowledge_base_messages_in_order(self):
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[good]])
        store = FakeStore()

        result = self.runner(boss, store, target=1).run()

        self.assertEqual(result.final_count, 1)
        self.assertEqual(boss.sent, list(self.messages))
        self.assertEqual(len(boss.chat_calls), 6)
        self.assertEqual(store.states[0][1], "waiting_resume")

    def test_keeps_unprocessed_candidates_available_after_one_greeting(self):
        first = candidate(geek_id="first", name="第一位")
        second = candidate(geek_id="second", name="第二位")
        boss = FakeBoss([[first, second], [first, second]])
        store = FakeStore()

        result = self.runner(boss, store, target=2).run()

        self.assertEqual(result.final_count, 2)
        self.assertEqual(
            [item[0] for item in boss.greeted],
            ["first", "second"],
        )

    def test_deduped_candidate_is_not_greeted(self):
        old = candidate(geek_id="old", name="已经联系")
        good = candidate(geek_id="good", name="新候选人")
        boss = FakeBoss([[old, good]])
        store = FakeStore(deduped={"old"})

        self.runner(boss, store, target=1).run()

        self.assertEqual([item[0] for item in boss.greeted], ["good"])

    def test_existing_daily_count_is_respected(self):
        boss = FakeBoss([])
        store = FakeStore(count=150)

        result = self.runner(boss, store, target=150).run()

        self.assertEqual(result.final_count, 150)
        self.assertEqual(boss.recommend_calls, [])

    def test_send_failure_stops_before_later_messages(self):
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[good]])
        boss.fail_send_at = 1
        store = FakeStore()

        with self.assertRaises(CampaignError):
            self.runner(boss, store, target=1).run()

        self.assertEqual(boss.sent, ["知识库一"])
        self.assertEqual(store.count, 1)
        self.assertEqual(store.states, [])

    def test_scan_limit_is_a_hard_stop(self):
        bad = [
            candidate(
                geek_id=f"bad-{index}",
                name=f"不合格{index}",
                experience="某大学 气象学",
            )
            for index in range(11)
        ]
        boss = FakeBoss([bad])
        store = FakeStore()

        with self.assertRaisesRegex(CampaignError, "检查候选人上限"):
            self.runner(boss, store, target=1, max_scans=10).run()

        self.assertEqual(boss.greeted, [])

    def test_scan_limit_cannot_exceed_policy_cap(self):
        with self.assertRaisesRegex(CampaignError, "1 到 150"):
            self.runner(FakeBoss([]), FakeStore(), max_scans=151)

    def test_repeated_empty_refreshes_stop_instead_of_looping_forever(self):
        boss = FakeBoss([[], [], [], []])
        store = FakeStore()

        with self.assertRaisesRegex(CampaignError, "连续刷新"):
            self.runner(boss, store, target=1, max_scans=20).run()

        self.assertLessEqual(len(boss.recommend_calls), 3)

    def test_candidate_without_greet_button_is_skipped(self):
        unavailable = replace(candidate(geek_id="no-button"), can_greet=False)
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[unavailable, good]])
        store = FakeStore()

        self.runner(boss, store, target=1).run()

        self.assertEqual([item[0] for item in boss.greeted], ["good"])

    def test_same_name_candidates_are_skipped_before_opening_a_name_based_chat(self):
        duplicate_a = candidate(geek_id="same-a", name="同名候选人")
        duplicate_b = candidate(geek_id="same-b", name="同名候选人")
        good = candidate(geek_id="good", name="唯一姓名")
        boss = FakeBoss([[duplicate_a, duplicate_b, good]])
        store = FakeStore()

        self.runner(boss, store, target=1).run()

        self.assertEqual([item[0] for item in boss.greeted], ["good"])


if __name__ == "__main__":
    unittest.main()
