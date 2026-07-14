#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = read(SKILL_ROOT / "SKILL.md")
        cls.reference_text = {
            path.name: read(path)
            for path in REFERENCES.iterdir()
            if path.is_file() and path.suffix in {".md", ".yaml"}
        }
        cls.all_text = cls.skill + "\n" + "\n".join(cls.reference_text.values())

    def test_description_uses_trigger_only_style(self):
        match = re.search(r"^description:\s*(.+)$", self.skill, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertTrue(match.group(1).strip('"').startswith("Use when"))

    def test_approved_opening_is_present(self):
        expected = (
            "我这边主要是华为数据库业务相关团队，方向包括TaurusDB、RDS、GaussDB、GeminiDB、Redis等，"
            "岗位主要偏数据库内核和管理系统研发和测试。数据库业务是公司重点投入方向，目前也在拓展海外市场，"
            "后续业务空间比较大。这个领域本身比较垂直，技术积累会比较深，长期做下来也更容易形成自己的技术护城河。"
        )
        self.assertIn(expected, self.reference_text["greetings.md"])

    def test_resume_and_application_status_copy_is_exact(self):
        self.assertIn("收到同学，我先看下你的简历，稍等一下。", self.all_text)
        self.assertIn(
            "我看了下，你的简历和我们这边方向挺匹配的。同学你这边是不是还没有投递呀？",
            self.all_text,
        )
        self.assertIn("同学你投的哪个部门呀？简历编号有给过别人吗？", self.all_text)

    def test_recruiting_start_question_replies_then_requests_wechat(self):
        application = self.reference_text["application.md"]
        expected = "同学已经开始了哈，再过几天就可以投递了，可以先加我微信我跟下流程"
        self.assertIn(expected, application)
        self.assertIn("`boss action wechat`", application)
        self.assertLess(application.index(expected), application.index("`boss action wechat`"))
        self.assertIn("投递链接", self.reference_text["auto_reply.md"])
        self.assertIn("招聘/秋招是否开始", self.reference_text["auto_reply.md"])

    def test_candidate_filter_is_2027_final_school_stem_and_silent_on_unknown(self):
        policy = self.reference_text["school_policy.yaml"]
        self.assertIn("graduation_year: 2027", policy)
        self.assertIn('match_field: "final_education_school"', policy)
        self.assertIn('major_mode: "stem_only"', policy)
        self.assertIn('unknown_profile_action: "no_reply"', policy)
        self.assertIn("不要求技术经历", policy)

    def test_transfer_stop_and_exchange_rules_are_present(self):
        flow = self.reference_text["candidate_conversion.md"]
        self.assertIn("已投递 ICT 下云软件研发部", flow)
        self.assertIn("心理测评未通过", flow)
        self.assertIn("已参加过任一轮面试", flow)
        self.assertIn("笔试未通过", flow)
        self.assertIn("无等待期", flow)
        self.assertIn("说不清组织", flow)

    def test_approved_chance_wording_is_auto_sendable(self):
        expected = "我看了下机会挺大的，只要你性格测评和笔试通过了，这个帮不了你，到后面面评不差的话offer概率还是很大的"
        self.assertIn(expected, self.all_text)
        risk = self.reference_text["risk_policy.yaml"]
        self.assertIn("approved_opportunity_wording", risk)
        self.assertNotIn('    - "录用概率"', risk)

    def test_runtime_limits_and_path_are_configured(self):
        agent = self.reference_text["agent.yaml"]
        self.assertIn("max_auto_greetings_per_day: 150", agent)
        self.assertIn("followup_interval_hours: 6", agent)
        self.assertIn("max_no_reply_followups: 8", agent)
        self.assertIn("temporary_state_retention_days: 3", agent)
        self.assertIn("/Users/yuyu/.codex/state/boss-zhaopin/state.sqlite3", agent)
        self.assertTrue((REFERENCES / "automation_runtime.md").exists())

    def test_eight_distinct_followup_variants_exist(self):
        followups = self.reference_text["followups.md"]
        variants = re.findall(r"^\d+\. `([^`]+)`$", followups, re.MULTILINE)
        self.assertGreaterEqual(len(set(variants)), 8)

    def test_known_facts_are_filled(self):
        self.assertNotIn("请填写", self.all_text)
        self.assertNotIn("请填写默认岗位关键词", self.all_text)
        self.assertIn("北京、西安、上海、成都、东莞、深圳、南京、杭州", self.all_text)
        self.assertIn("两轮技术面试", self.all_text)
        self.assertIn("一轮主管面试", self.all_text)

    def test_obsolete_copy_and_conflicting_direction_are_absent(self):
        self.assertNotIn("数据库没有受到当下AI的太多冲击", self.all_text)
        self.assertNotIn("数据库/软件研发/测试开发方向比较匹配", self.all_text)
        self.assertNotIn("统一按开发/AI 开发方向沟通", self.all_text)

    def test_local_state_privacy_rules_are_explicit(self):
        runtime_path = REFERENCES / "automation_runtime.md"
        self.assertTrue(runtime_path.exists())
        runtime = read(runtime_path)
        self.assertIn("不得提交到 Git", runtime)
        self.assertIn("不保存简历正文", runtime)
        self.assertIn("Boss 显示姓名", runtime)
        self.assertIn("2027-12-31", runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
