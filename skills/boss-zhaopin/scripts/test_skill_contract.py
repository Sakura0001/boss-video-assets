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

    def test_application_paths_and_links_are_exact(self):
        application = self.reference_text["application.md"]
        expected = (
            "https://career.huawei.com",
            "https://career.huawei.com/reccampportal/portal5/campus-recruitment.html",
            "软件开发工程师 → 通用软件/数据库",
            "AI应用工程师 → AI技术应用/AI系统软件",
            "网络安全与隐私保护工程师 → 网络安全",
            "部门意向选择“ICT BG”“云软件研发部”",
            "投递后，把简历编码发给我即可。",
        )
        for text in expected:
            self.assertIn(text, application)
        self.assertNotIn("不发送投递链接", application)
        self.assertNotIn("再过几天就可以投递了", application)
        self.assertIn("`boss action wechat`", application)
        self.assertIn("投递链接", self.reference_text["auto_reply.md"])
        self.assertIn("招聘/秋招是否开始", self.reference_text["auto_reply.md"])

    def test_job_catalog_and_written_exam_formats_are_present(self):
        job = self.reference_text["job_default.md"]
        self.assertIn("软件测试类岗位/通用软件开发岗位", job)
        self.assertIn("AI应用工程师", job)
        self.assertIn("网络安全与隐私保护工程师", job)

        interview = self.reference_text["faq_interview.md"]
        self.assertIn("三道大题", interview)
        self.assertIn("600 分", interview)
        self.assertIn("180 分及格", interview)
        self.assertIn("1 至 2 道大题", interview)
        self.assertIn("AI 相关选择题", interview)
        self.assertIn("全部为选择题", interview)

    def test_candidate_filter_is_2027_any_visible_school_stem_and_silent_on_unknown(self):
        policy = self.reference_text["school_policy.yaml"]
        self.assertIn("graduation_year: 2027", policy)
        self.assertIn('match_field: "visible_education_schools"', policy)
        self.assertIn('require_any_education_school_match: true', policy)
        self.assertIn('major_mode: "semantic_related_allowlist"', policy)
        self.assertIn('allowed_majors:', policy)
        self.assertIn('automation_major_mode: "canonical_or_explicit_alias"', policy)
        self.assertIn('major_aliases:', policy)
        self.assertIn('"控制工程": "自动化"', policy)
        self.assertIn('"网络空间安全": "网络安全"', policy)
        self.assertIn('"微电子学与固体电子学": "电子科学与技术"', policy)
        self.assertIn('确定性自动化只允许直接命中 allowed_majors', policy)
        self.assertIn('不得由脚本自由猜测', policy)
        self.assertIn('计算机科学与技术', policy)
        self.assertIn('专业名称不要求逐字命中', policy)
        self.assertIn('语义上能明确判断为计算机类', policy)
        self.assertIn('必须作为独立字段完整命中', policy)
        self.assertIn('吉林大学交通学院不得按吉林大学命中', policy)
        self.assertIn('任意一所命中目标名单即可', policy)
        self.assertIn('unknown_profile_action: "no_reply"', policy)
        self.assertIn("不要求技术经历", policy)

    def test_base_hc_and_role_presence_answer_and_pending_offer_log_are_present(self):
        reply = self.reference_text["auto_reply.md"]
        self.assertIn("某个 base 是否有 HC", reply)
        self.assertIn("统一回复：`有`", reply)
        self.assertIn("还可以，和往年持平，有几十个", reply)
        self.assertIn("可以先投递，先投递先进流程", reply)
        self.assertIn("offer_questions_pending.md", reply)
        self.assertIn("offer_questions_pending.md", self.all_text)

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
        self.assertIn("recommendation_qualification_batch_size: 10", agent)
        self.assertIn("refresh_recommendations_when_batch_has_no_match: true", agent)
        self.assertIn("recommendation_refresh_interval_seconds:", agent)
        self.assertIn("followup_interval_hours: 6", agent)
        self.assertIn("max_no_reply_followups: 8", agent)
        self.assertIn("temporary_state_retention_days: 3", agent)
        self.assertIn("~/.codex/state/boss-zhaopin/state.sqlite3", agent)
        self.assertIn("BOSS_ZHAOPIN_STATE_DIR", agent)
        self.assertTrue((REFERENCES / "automation_runtime.md").exists())

    def test_runtime_instructions_cover_windows_and_posix(self):
        runtime = self.reference_text["automation_runtime.md"]
        self.assertIn("Windows PowerShell", runtime)
        self.assertIn("py -3", runtime)
        self.assertIn("macOS / Linux", runtime)
        self.assertIn("python3", runtime)
        self.assertNotIn("/Users/yuyu/", self.skill + "\n" + runtime)

    def test_knowledge_gap_wechat_handoff_is_guarded_by_transfer_eligibility(self):
        flow = self.reference_text["candidate_conversion.md"]
        risk = self.reference_text["risk_policy.yaml"]
        self.assertIn("知识缺口转微信", flow)
        self.assertIn("exchange_wechat", flow)
        self.assertIn("approved_knowledge_gap_wechat_handoff", risk)
        self.assertIn("不得绕过资格门槛", flow)

    def test_recommendation_refreshes_after_ten_unqualified_candidates(self):
        greet = self.reference_text["auto_greet.md"]
        cli = self.reference_text["boss_cli.md"]
        self.assertIn("每批检查 10 名不同候选人", greet)
        self.assertIn("随机等待 1 至 2 秒", greet)
        self.assertIn("boss recommend <岗位关键字> --refresh", greet)
        self.assertIn("max_candidates_per_run: 150", greet)
        self.assertIn("不得无限循环或快速重试", greet)
        self.assertIn("只打开一次精确会话", greet)
        self.assertIn("不得重复离开并重新进入会话", greet)
        self.assertIn("boss recommend [岗位关键字] --refresh", cli)

    def test_greeting_success_is_recorded_atomically(self):
        runtime = self.reference_text["automation_runtime.md"]
        greet = self.reference_text["auto_greet.md"]
        self.assertIn("greeting-complete", runtime)
        self.assertIn("原子", runtime)
        self.assertIn("greeting-complete", greet)

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
        self.assertNotIn('major_mode: "exact_allowlist"', self.all_text)
        self.assertNotIn("专业名称必须逐字命中", self.all_text)

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
