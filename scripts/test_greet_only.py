import io
import json
import scripts.greet_only as greet_only
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.greet_only import (
    BLOCKED_EXPECTATION_KEYWORDS,
    BossCli,
    CampaignError,
    CampaignRunner,
    Candidate,
    EducationRecord,
    EligibilityResult,
    EligibilityPolicy,
    GreetNotConfirmedError,
    GreetingKnowledgeBaseError,
    RecommendationBatch,
    RuntimeStoreCli,
    build_parser,
    load_greeting_messages,
    main,
)


SHANGHAI = timezone(timedelta(hours=8), "Asia/Shanghai")


class FakeBoss:
    def __init__(self, batches, job="ai应用研发工程师"):
        self.batches = list(batches)
        self.job = job
        self.recommend_calls = []
        self.greeted = []
        self.chat_calls = []
        self.sequence_calls = []
        self.sent = []
        self.fail_send_at = None
        self.sequence_error = None
        self.unconfirmed_greet_ids = set()

    def recommend(self, job, refresh):
        self.recommend_calls.append((job, refresh))
        if not self.batches:
            return RecommendationBatch(self.job, ())
        batch = self.batches.pop(0)
        if isinstance(batch, RecommendationBatch):
            return batch
        return RecommendationBatch(self.job, tuple(batch))

    def greet(self, candidate, job):
        self.greeted.append((candidate.geek_id, candidate.name, job))
        if candidate.geek_id in self.unconfirmed_greet_ids:
            raise GreetNotConfirmedError("按钮仍可用，无法确认操作成功")

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

    def send_sequence(self, candidate, job, messages):
        self.sequence_calls.append((candidate.geek_id, candidate.name, job, messages))
        if self.sequence_error is not None:
            raise self.sequence_error
        for message in messages:
            self.send(message)


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
        self.events.append((candidate.geek_id, job, at, eligibility.major))

    def mark_waiting_application_status(self, candidate, eligibility, at):
        self.states.append(
            (candidate.geek_id, "waiting_application_status", at, eligibility.major)
        )


def candidate(
    geek_id="c1",
    name="候选人",
    base_info="27年应届生 / 博士",
    experience="浙江大学 人工智能",
    expect="上海 后端开发",
    advantage="",
    highlights=None,
    education=None,
    can_greet=True,
):
    degree_match = next(
        (
            value
            for value in ("博士", "硕士", "研究生", "本科")
            if value in base_info
        ),
        "本科",
    )
    if education is None:
        education = (
            EducationRecord(
                start_year="2024",
                end_year="2027",
                school="浙江大学",
                major="人工智能",
                degree=degree_match,
            ),
        )
    return Candidate(
        geek_id=geek_id,
        name=name,
        base_info=base_info,
        expect=expect,
        experience=experience,
        advantage=advantage,
        highlights=tuple(highlights or ()),
        education=tuple(education),
        can_greet=can_greet,
        has_history_chat=False,
        has_viewed=False,
    )


class GreetingKnowledgeBaseTests(unittest.TestCase):
    def test_repository_knowledge_base_loads_approved_plain_text_messages(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "boss-zhaopin"
            / "references"
            / "greetings.md"
        )
        expected = (
            "我们是华为GaussDB国产数据库的研发团队，当前主要进攻海外市场，市场仍有几十亿的增量空间，数据库业务在今年6月在公司向全体董事进行汇报，未来前景巨大，感兴趣可以投递我们，今年目标hc相比去年扩充一倍，招聘要求放低，有任何问题可以发消息了解一下。",
            "我看了一下你的背景和在线简历，和我们的研发方向有一定匹配度，我们主要是有三种岗位，内核开发，需要较高的技术能力，部门允许零基础进来学习，参与Gaussdb的核心技术研发工作，此外还有智能agent开发管控工作，与传统开发相同，技术栈与互联网公司一致，也有测试团队的hc，测试hc整体难度要低很多，offer更好开出，投递后具体的岗位在面试和offer阶段会具体说明，我们这边相对wlb一些，自盈利部门，年终奖可以保证，日常加班可以随意申报，也不会强制要求来。部门整体氛围好，新老员工无断层现象，跳槽到外面的员工都有很大幅度的涨薪，不需要担心个人竞争力。",
            "在华为，投递一个好的部门远好于投递一个非常热门的业务，部门没有输出到销售的情况，外界风评很好，请同学慎重考虑投递的部门，当前如果还没进入简历筛选环节或者投递的不是云软件研发部，还可以撤销原投递转投我们部门，投递方式如下，AI应用工程师投递：校园招聘->校招生职位->AI应用工程师->AI技术应用/AI系统软件->选择工作地点->部门意向选择“ICT BG” “云软件研发部” 或者 软件开发工程师投递：校园招聘->校招生职位->软件开发工程师->通用软件/数据库->选择工作地点->部门意向选择“ICT BG” “云软件研发部” 两个岗位仅在笔试环节不同，可以选择自己擅长的笔试方向投递，投递后我会发你一些笔试/测评攻略。并加我微信后续跟踪流程。",
        )

        messages = load_greeting_messages(path)

        self.assertEqual(messages, expected)
        self.assertTrue(all("**" not in message for message in messages))

    def test_loads_exact_messages_in_required_order(self):
        content = """# 主动打招呼话术

### 技术与岗位介绍

`第一条原文`

### 匹配与转投提示

`第二条原文`

### 投递方式与流程提示

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
            path.write_text("### 技术与岗位介绍\n\n`只有一条`\n", encoding="utf-8")
            with self.assertRaises(GreetingKnowledgeBaseError):
                load_greeting_messages(path)


class EligibilityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = EligibilityPolicy(
            schools=("浙江大学", "中国科学院大学", "上海交通大学", "吉林大学"),
            aliases={"浙大": "浙江大学", "国科大": "中国科学院大学"},
            majors=(
                "人工智能",
                "计算机科学与技术",
                "自动化",
                "网络安全",
            ),
            major_aliases={
                "控制工程": "自动化",
                "网络空间安全": "网络安全",
            },
        )

    def test_accepts_candidate_when_every_gate_is_visible(self):
        result = self.policy.evaluate(candidate())
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "浙江大学")
        self.assertEqual(result.major, "人工智能")
        self.assertEqual(result.degree, "博士")

    def test_skip_major_filter_allows_unknown_empty_or_missing_current_major(self):
        previous_zhejiang_education = EducationRecord(
            "2020", "2024", "浙江大学", "计算机科学与技术", "本科"
        )
        cases = (
            (
                "unknown",
                (
                    previous_zhejiang_education,
                    EducationRecord("2024", "2027", "某大学", "气象学", "博士"),
                ),
            ),
            (
                "empty",
                (
                    previous_zhejiang_education,
                    EducationRecord("2024", "2027", "某大学", "", "博士"),
                ),
            ),
            ("missing", (previous_zhejiang_education,)),
        )
        for label, education in cases:
            with self.subTest(label=label):
                result = self.policy.evaluate(
                    candidate(education=education), require_major=False
                )
                self.assertTrue(result.eligible)
                self.assertEqual(result.major, "")

    def test_skip_major_filter_preserves_recognized_canonical_major(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord(
                        "2024", "2027", "浙江大学", "控制工程", "硕士"
                    ),
                ),
            ),
            require_major=False,
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.major, "自动化")

    def test_major_filter_is_required_by_default_for_unknown_and_empty_major(self):
        cases = (
            EducationRecord("2024", "2027", "浙江大学", "气象学", "博士"),
            EducationRecord("2024", "2027", "浙江大学", "", "博士"),
        )
        for education in cases:
            with self.subTest(major=education.major):
                result = self.policy.evaluate(candidate(education=(education,)))
                self.assertFalse(result.eligible)
                self.assertEqual(result.reason, "major_unknown_or_ineligible")

    def test_skip_major_filter_does_not_bypass_other_qualification_gates(self):
        cases = (
            (
                "expectation_blocked",
                candidate(expect="上海 数据工程师"),
            ),
            (
                "graduation_year",
                candidate(base_info="28年应届生 / 硕士"),
            ),
            (
                "degree",
                candidate(base_info="27年应届生 / 大专"),
            ),
            (
                "school_unknown_or_ineligible",
                candidate(
                    education=(
                        EducationRecord(
                            "2024", "2027", "某大学", "人工智能", "博士"
                        ),
                    ),
                ),
            ),
        )
        for reason, item in cases:
            with self.subTest(reason=reason):
                result = self.policy.evaluate(item, require_major=False)
                self.assertFalse(result.eligible)
                self.assertEqual(result.reason, reason)

    def test_rejects_blocked_expectation_keywords(self):
        cases = (
            "上海 算法工程师",
            "上海 电子/通信（行业）",
            "上海 通信工程师",
            "上海 硬件工程师",
            "上海 Web前端",
            "上海 Unity3D开发",
            "上海 u N i T y3D开发",
            "上海 U\tN\nI\u3000T y3D开发",
            "上海 电气工程师",
            "上海 数据工程师",
            "上海 产品经理",
            "上海 商业分析",
        )
        for expectation in cases:
            with self.subTest(expectation=expectation):
                result = self.policy.evaluate(candidate(expect=expectation))
                self.assertFalse(result.eligible)
                self.assertEqual(result.reason, "expectation_blocked")

    def test_blocked_expectation_keywords_are_exact(self):
        self.assertEqual(
            BLOCKED_EXPECTATION_KEYWORDS,
            (
                "算法",
                "通信",
                "硬件",
                "前端",
                "unity",
                "电气",
                "数据",
                "产品",
                "分析",
            ),
        )

    def test_allows_expectation_without_blocked_keyword(self):
        result = self.policy.evaluate(candidate(expect="上海 后端开发"))
        self.assertTrue(result.eligible)

    def test_allows_empty_expectation_to_continue_existing_gate(self):
        result = self.policy.evaluate(candidate(expect=""))
        self.assertTrue(result.eligible)

    def test_empty_expectation_preserves_existing_rejection_reasons(self):
        cases = (
            (
                "graduation_year",
                candidate(expect="", base_info="28年应届生 / 硕士"),
            ),
            (
                "degree",
                candidate(expect="", base_info="27年应届生 / 大专"),
            ),
            (
                "school_unknown_or_ineligible",
                candidate(
                    expect="",
                    education=(
                        EducationRecord(
                            "2024", "2027", "某大学", "人工智能", "博士"
                        ),
                    ),
                ),
            ),
            (
                "major_unknown_or_ineligible",
                candidate(
                    expect="",
                    education=(
                        EducationRecord(
                            "2024", "2027", "浙江大学", "气象学", "博士"
                        ),
                    ),
                ),
            ),
        )
        for reason, item in cases:
            with self.subTest(reason=reason):
                result = self.policy.evaluate(item)
                self.assertFalse(result.eligible)
                self.assertEqual(result.reason, reason)

    def test_rejects_unknown_school(self):
        result = self.policy.evaluate(
            candidate(
                education=(
                    EducationRecord("2024", "2027", "某大学", "人工智能", "博士"),
                )
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "school_unknown_or_ineligible")

    def test_rejects_wrong_graduation_year(self):
        result = self.policy.evaluate(candidate(base_info="28年应届生 / 硕士"))
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "graduation_year")

    def test_rejects_major_not_in_knowledge_base(self):
        result = self.policy.evaluate(
            candidate(
                education=(
                    EducationRecord("2024", "2027", "浙江大学", "气象学", "博士"),
                )
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "major_unknown_or_ineligible")

    def test_accepts_explicit_major_aliases(self):
        cases = (
            ("控制工程", "自动化"),
            ("网络空间安全", "网络安全"),
        )
        for source, canonical in cases:
            with self.subTest(source=source):
                result = self.policy.evaluate(
                    candidate(
                        base_info="27年应届生 / 硕士",
                        education=(
                            EducationRecord(
                                "2024",
                                "2027",
                                "浙江大学",
                                source,
                                "硕士",
                            ),
                        ),
                    )
                )
                self.assertTrue(result.eligible)
                self.assertEqual(result.major, canonical)

    def test_direct_major_match_takes_priority_over_alias(self):
        policy = replace(
            self.policy,
            major_aliases={"控制工程": "计算机科学与技术"},
        )
        result = policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord(
                        "2024",
                        "2027",
                        "浙江大学",
                        "人工智能与控制工程",
                        "硕士",
                    ),
                ),
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.major, "人工智能")

    def test_unknown_semantic_neighbor_is_not_guessed(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord(
                        "2024",
                        "2027",
                        "浙江大学",
                        "材料与化工",
                        "硕士",
                    ),
                ),
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "major_unknown_or_ineligible")

    def test_from_files_rejects_alias_to_unapproved_major(self):
        schools = """# 目标学校

## 目标学校

1. 浙江大学

## 学校别名

| 标准名称 | 别名 |
| --- | --- |
"""
        policy = """policy:
  allowed_majors:
    - "人工智能"
  major_aliases:
    "智能科学与技术": "未批准方向"
  require_technical_experience: false
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schools_path = root / "target_schools.md"
            policy_path = root / "school_policy.yaml"
            schools_path.write_text(schools, encoding="utf-8")
            policy_path.write_text(policy, encoding="utf-8")
            with self.assertRaisesRegex(
                CampaignError,
                "专业近义映射指向未批准专业",
            ):
                EligibilityPolicy.from_files(schools_path, policy_path)

    def test_from_files_accepts_structured_school_table(self):
        schools = """# 目标学校

## 目标学校（允许投递）

| 适用范围 | 学校 | 类别 |
| --- | --- | --- |
| 国内通用院校 | 南京航空航天大学 | 211 |
| 海外通用院校 | 曼彻斯特大学 | 海外其他院校 |

## 学校别名

| 标准名称 | 常见别名 |
| --- | --- |
| 南京航空航天大学 | 南航 |
"""
        policy = """policy:
  allowed_majors:
    - "人工智能"
  major_aliases:
    "智能科学与技术": "人工智能"
  require_technical_experience: false
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schools_path = root / "target_schools.md"
            policy_path = root / "school_policy.yaml"
            schools_path.write_text(schools, encoding="utf-8")
            policy_path.write_text(policy, encoding="utf-8")
            parsed = EligibilityPolicy.from_files(schools_path, policy_path)

        self.assertEqual(
            parsed.schools,
            ("南京航空航天大学", "曼彻斯特大学"),
        )
        self.assertEqual(parsed.aliases["南航"], "南京航空航天大学")

    def test_accepts_target_bachelor_school_when_master_school_is_not_target(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord("2024", "2027", "某大学", "人工智能", "硕士"),
                    EducationRecord("2020", "2024", "浙江大学", "数学", "本科"),
                ),
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "浙江大学")
        self.assertEqual(result.major, "人工智能")

    def test_accepts_target_final_master_school(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord(
                        "2024",
                        "2027",
                        "上海交通大学",
                        "计算机科学与技术",
                        "硕士",
                    ),
                    EducationRecord("2020", "2024", "某大学", "数学", "本科"),
                ),
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "上海交通大学")

    def test_rejects_longer_school_name_that_contains_target_school(self):
        for school_text in ("吉林大学交通学院", "吉大交通学院"):
            result = self.policy.evaluate(
                candidate(
                    base_info="27年应届生 / 本科",
                    education=(
                        EducationRecord(
                            "2023", "2027", school_text, "人工智能", "本科"
                        ),
                    ),
                )
            )
            self.assertFalse(result.eligible)
            self.assertEqual(result.reason, "school_unknown_or_ineligible")

    def test_accepts_exact_school_name_as_an_independent_field(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 本科",
                education=(
                    EducationRecord(
                        "2023", "2027", "吉林大学", "人工智能", "本科"
                    ),
                ),
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(result.school, "吉林大学")

    def test_rejects_compact_summary_when_structured_education_is_missing(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                experience="",
                advantage="上海交通大学 / 人工智能方向，2027年毕业",
                education=(),
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "school_unknown_or_ineligible")

    def test_uses_only_current_degree_major(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord("2024", "2027", "某大学", "气象学", "硕士"),
                    EducationRecord(
                        "2020", "2024", "浙江大学", "人工智能", "本科"
                    ),
                ),
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "major_unknown_or_ineligible")

    def test_alias_in_previous_degree_does_not_qualify_current_degree(self):
        result = self.policy.evaluate(
            candidate(
                base_info="27年应届生 / 硕士",
                education=(
                    EducationRecord("2024", "2027", "某大学", "气象学", "硕士"),
                    EducationRecord(
                        "2020",
                        "2024",
                        "浙江大学",
                        "网络空间安全",
                        "本科",
                    ),
                ),
            )
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.reason, "major_unknown_or_ineligible")

    def test_candidate_parses_structured_education_from_recommend_json(self):
        item = Candidate.from_mapping(
            {
                "geekId": "stable-id",
                "name": "候选人",
                "baseInfo": "27年应届生 / 硕士",
                "education": [
                    {
                        "startYear": "2024",
                        "endYear": "2027",
                        "school": "中国科学院大学",
                        "major": "人工智能",
                        "degree": "硕士",
                    },
                    {
                        "startYear": "2020",
                        "endYear": "2024",
                        "school": "某大学",
                        "major": "数学",
                        "degree": "本科",
                    },
                ],
                "canGreet": True,
            }
        )

        self.assertEqual(len(item.education), 2)
        self.assertEqual(item.education[0].school, "中国科学院大学")
        self.assertEqual(item.education[1].degree, "本科")


class BossCliTests(unittest.TestCase):
    class CapturingBossCli(BossCli):
        def __init__(self, outputs):
            super().__init__(
                executable="boss",
                retry_sleep=lambda _: None,
            )
            self.outputs = list(outputs)
            self.calls = []

        def _run(self, arguments):
            self.calls.append(list(arguments))
            value = self.outputs.pop(0)
            if isinstance(value, Exception):
                raise value
            return value

    def test_automation_commands_use_fast_pacing_and_one_message_sequence(self):
        item = candidate(geek_id="stable-id", name="候选人")
        cli = self.CapturingBossCli(
            [
                '{"job":"ai应用研发工程师","candidates":[]}',
                '{"job":"ai应用研发工程师","name":"候选人","geekId":"stable-id"}',
                '{"job":"ai应用研发工程师","name":"候选人","messagesVerified":3}',
            ]
        )

        cli.recommend("ai应用研发工程师", refresh=False)
        cli.greet(item, "ai应用研发工程师")
        cli.send_sequence(
            item,
            "ai应用研发工程师",
            ("知识库一", "知识库二", "知识库三"),
        )

        self.assertEqual(cli.calls[0][-2:], ["--json", "--automation"])
        self.assertIn("--automation", cli.calls[1])
        self.assertNotIn("--job", cli.calls[1])
        self.assertEqual(cli.calls[2][0], "send-sequence")
        self.assertEqual(cli.calls[2].count("send-sequence"), 1)
        self.assertNotIn("--request-resume", cli.calls[2])
        self.assertNotIn("request-attachment-resume", cli.calls[2])

    def test_recommend_without_job_uses_current_default_job(self):
        cli = self.CapturingBossCli(
            ['{"job":"用户当前岗位","candidates":[]}']
        )

        batch = cli.recommend(None, refresh=False)

        self.assertEqual(batch.job, "用户当前岗位")
        self.assertEqual(
            cli.calls,
            [["recommend", "--json", "--automation"]],
        )

    def test_transient_recommend_timeout_retries_with_refresh(self):
        cli = self.CapturingBossCli(
            [
                CampaignError(
                    "boss recommend --json 失败："
                    "读取推荐列表失败：Waiting failed: 18000ms exceeded"
                ),
                '{"job":"用户当前岗位","candidates":[]}',
            ]
        )

        batch = cli.recommend(None, refresh=False)

        self.assertEqual(batch.job, "用户当前岗位")
        self.assertNotIn("--refresh", cli.calls[0])
        self.assertIn("--refresh", cli.calls[1])

    def test_login_failure_does_not_retry_as_recommend_timeout(self):
        login_required = CampaignError(
            "Boss 当前未登录，无法执行该命令。请先运行 boss login"
        )
        cli = self.CapturingBossCli([login_required])

        with self.assertRaises(CampaignError):
            cli.recommend(None, refresh=False)

        self.assertEqual(len(cli.calls), 1)

    def test_send_sequence_strips_recommendation_location_and_salary(self):
        item = candidate(geek_id="stable-id", name="候选人")
        cli = self.CapturingBossCli(
            [
                '{"job":"ai应用研发工程师","name":"候选人",'
                '"messagesVerified":3}'
            ]
        )

        cli.send_sequence(
            item,
            "ai应用研发工程师 _ 上海 25-30K",
            ("知识库一", "知识库二", "知识库三"),
        )

        job_index = cli.calls[0].index("--job")
        self.assertEqual(cli.calls[0][job_index + 1], "ai应用研发工程师")

    def test_send_sequence_rejects_invalid_json(self):
        item = candidate(geek_id="stable-id", name="候选人")
        cli = self.CapturingBossCli(["not-json"])

        with self.assertRaisesRegex(CampaignError, "无效 JSON"):
            cli.send_sequence(
                item,
                "ai应用研发工程师",
                ("知识库一", "知识库二", "知识库三"),
            )

    def test_send_sequence_rejects_incomplete_verification(self):
        item = candidate(geek_id="stable-id", name="候选人")
        cli = self.CapturingBossCli(
            [
                '{"job":"ai应用研发工程师","name":"候选人",'
                '"messagesVerified":2}'
            ]
        )

        with self.assertRaisesRegex(CampaignError, "三条知识库消息未全部验证"):
            cli.send_sequence(
                item,
                "ai应用研发工程师",
                ("知识库一", "知识库二", "知识库三"),
            )

    def test_login_is_skipped_when_session_is_ready(self):
        cli = self.CapturingBossCli(
            [
                "help",
                "未读聊天输出",
                '{"job":"用户当前岗位","candidates":[]}',
            ]
        )

        batch = cli.ensure_logged_in(sleep=lambda _: None)

        self.assertEqual(batch.job, "用户当前岗位")
        self.assertEqual(
            cli.calls,
            [
                ["help"],
                ["list", "--unread"],
                ["recommend", "--json", "--automation"],
            ],
        )

    def test_login_opens_browser_and_waits_until_session_is_ready(self):
        login_required = CampaignError(
            "Boss 当前未登录，无法执行该命令。请先运行 boss login"
        )
        cli = self.CapturingBossCli(
            [
                "help",
                login_required,
                "Boss 登录页已打开",
                login_required,
                "未读聊天输出",
                '{"job":"用户当前岗位","candidates":[]}',
            ]
        )
        clock_values = iter((0.0, 1.0, 2.0))

        cli.ensure_logged_in(
            timeout_seconds=10,
            poll_interval_seconds=1,
            sleep=lambda _: None,
            monotonic=lambda: next(clock_values),
        )

        self.assertEqual(
            cli.calls,
            [
                ["help"],
                ["list", "--unread"],
                ["login"],
                ["list", "--unread"],
                ["list", "--unread"],
                ["recommend", "--json", "--automation"],
            ],
        )

    def test_non_login_error_does_not_open_login_page(self):
        cli = self.CapturingBossCli(
            ["help", CampaignError("boss list 失败：页面结构异常")]
        )

        with self.assertRaisesRegex(CampaignError, "页面结构异常"):
            cli.ensure_logged_in(sleep=lambda _: None)

        self.assertNotIn(["login"], cli.calls)
        self.assertEqual(cli.calls, [["help"], ["list", "--unread"]])

    def test_login_wait_has_a_hard_timeout(self):
        login_required = CampaignError(
            "Boss 当前未登录，无法执行该命令。请先运行 boss login"
        )
        cli = self.CapturingBossCli(["help", login_required, "登录页已打开"])
        clock_values = iter((0.0, 11.0))

        with self.assertRaisesRegex(CampaignError, "等待 Boss 登录超过 10 秒"):
            cli.ensure_logged_in(
                timeout_seconds=10,
                poll_interval_seconds=1,
                sleep=lambda _: None,
                monotonic=lambda: next(clock_values),
            )

    def test_parser_defaults_to_live_current_job_mode(self):
        args = build_parser().parse_args([])

        self.assertIsNone(args.job)
        self.assertFalse(args.validate_only)
        self.assertEqual(args.target, 150)

    def test_parser_major_filter_defaults_to_required_and_can_be_skipped(self):
        required = build_parser().parse_args([])
        skipped = build_parser().parse_args(["--skip-major-filter"])

        self.assertFalse(required.skip_major_filter)
        self.assertTrue(skipped.skip_major_filter)

    def test_validate_only_reports_major_filter_mode(self):
        for argv, expected_mode in (
            (["--validate-only"], "required"),
            (["--validate-only", "--skip-major-filter"], "skipped"),
        ):
            with self.subTest(argv=argv):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = main(argv)

                self.assertEqual(result, 0)
                payload = json.loads(output.getvalue())
                self.assertEqual(payload["majorFilterMode"], expected_mode)
                self.assertEqual(payload["messageCount"], 3)

    def test_validate_only_skips_live_preflight(self):
        with patch("scripts.greet_only.BossCli") as boss_class, patch(
            "scripts.greet_only.RuntimeStoreCli"
        ) as store_class:
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(["--validate-only"])

        self.assertEqual(result, 0)
        boss_class.assert_not_called()
        store_class.assert_not_called()


class RuntimeStoreCliTests(unittest.TestCase):
    class CapturingRuntimeStoreCli(RuntimeStoreCli):
        def __init__(self):
            super().__init__(Path("runtime_store.py"))
            self.calls = []

        def _run_json(self, arguments):
            self.calls.append(list(arguments))
            return {}

    def test_initialize_and_purge_use_exact_runtime_store_arguments(self):
        store = self.CapturingRuntimeStoreCli()
        as_of = "2026-08-21T10:11:12+08:00"

        store.initialize()
        store.purge(as_of)

        self.assertEqual(
            store.calls,
            [
                ["init"],
                ["purge", "--as-of", as_of],
            ],
        )

    def test_persists_only_canonical_eligibility_major(self):
        item = candidate(
            geek_id="raw-unknown-major",
            name="未知专业候选人",
            education=(
                EducationRecord("2024", "2027", "浙江大学", "气象学", "博士"),
            ),
        )

        for persisted_major in ("", "人工智能"):
            with self.subTest(persisted_major=persisted_major):
                store = self.CapturingRuntimeStoreCli()
                eligibility = EligibilityResult(
                    eligible=True,
                    reason="eligible",
                    school="浙江大学",
                    major=persisted_major,
                    degree="博士",
                    grad_year=2027,
                )
                store.record_greeted(
                    item,
                    eligibility,
                    "ai应用研发工程师",
                    "2026-07-23T10:00:00+08:00",
                )
                store.mark_waiting_application_status(
                    item,
                    eligibility,
                    "2026-07-23T10:00:01+08:00",
                )

                major_values = [
                    call[call.index("--major") + 1] for call in store.calls
                ]
                self.assertEqual(major_values, [persisted_major, persisted_major])
                greeting_call = store.calls[0]
                self.assertEqual(
                    greeting_call[greeting_call.index("--manual-takeover") + 1],
                    "true",
                )
                stage_call = store.calls[1]
                self.assertEqual(
                    stage_call[stage_call.index("--stage") + 1],
                    "waiting_application_status",
                )
                self.assertEqual(
                    stage_call[stage_call.index("--manual-takeover") + 1],
                    "false",
                )
                self.assertNotIn("--followup-count", stage_call)
                self.assertNotIn(
                    "气象学",
                    [argument for call in store.calls for argument in call],
                )


class LivePreflightTests(unittest.TestCase):
    def test_preflight_orders_store_lifecycle_before_login_verification(self):
        calls = []
        expected_batch = RecommendationBatch("用户当前岗位", ())
        as_of = datetime(2026, 8, 21, 10, 11, 12, tzinfo=SHANGHAI)

        class CapturingStore:
            def initialize(self):
                calls.append(("initialize",))

            def purge(self, value):
                calls.append(("purge", value))

        class CapturingBoss:
            def ensure_logged_in(self, **kwargs):
                calls.append(("ensure_logged_in", kwargs))
                return expected_batch

        result = greet_only.prepare_live_run(
            store=CapturingStore(),
            boss=CapturingBoss(),
            job=None,
            now=lambda: as_of,
            login_timeout_seconds=17,
            login_poll_interval_seconds=2.5,
        )

        self.assertIs(result, expected_batch)
        self.assertEqual(
            calls,
            [
                ("initialize",),
                ("purge", "2026-08-21T10:11:12+08:00"),
                (
                    "ensure_logged_in",
                    {
                        "job": None,
                        "timeout_seconds": 17,
                        "poll_interval_seconds": 2.5,
                    },
                ),
            ],
        )


class CampaignRunnerTests(unittest.TestCase):
    def setUp(self):
        self.policy = EligibilityPolicy(
            schools=("浙江大学",),
            aliases={},
            majors=("人工智能",),
            major_aliases={},
        )
        self.messages = ("知识库一", "知识库二", "知识库三")
        self.now = lambda: datetime(2026, 7, 23, 10, 0, tzinfo=SHANGHAI)
        self.delays = []

    def runner(
        self,
        boss,
        store,
        target=150,
        max_scans=150,
        job="ai应用研发工程师",
        require_major=True,
    ):
        return CampaignRunner(
            boss=boss,
            store=store,
            policy=self.policy,
            messages=self.messages,
            job=job,
            target=target,
            max_scans=max_scans,
            now=self.now,
            require_major=require_major,
            sleep=self.delays.append,
            random_delay=lambda low, high: 1.25,
            monotonic=lambda: 10.0,
        )

    def test_skip_major_filter_allows_unknown_major_and_preserves_dedupe(self):
        deduped_unknown = candidate(
            geek_id="old-unknown",
            name="已经联系未知专业",
            education=(
                EducationRecord("2024", "2027", "浙江大学", "气象学", "博士"),
            ),
        )
        fresh_empty = candidate(
            geek_id="fresh-empty",
            name="新空专业",
            education=(
                EducationRecord("2024", "2027", "浙江大学", "", "博士"),
            ),
        )
        boss = FakeBoss([[deduped_unknown, fresh_empty]])
        store = FakeStore(deduped={"old-unknown"})
        output = io.StringIO()

        with redirect_stdout(output):
            result = self.runner(
                boss,
                store,
                target=1,
                require_major=False,
            ).run()

        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([item[0] for item in boss.greeted], ["fresh-empty"])
        self.assertEqual(result.final_count, 1)
        self.assertEqual(store.events[0][3], "")
        self.assertEqual(store.states[0][3], "")
        job_selected = next(
            event for event in events if event["event"] == "job-selected"
        )
        self.assertEqual(job_selected["majorFilterMode"], "skipped")

    def test_skip_major_filter_persists_canonical_major_for_alias(self):
        self.policy = replace(
            self.policy,
            major_aliases={"控制工程": "人工智能"},
        )
        aliased = candidate(
            geek_id="aliased-major",
            name="别名专业候选人",
            education=(
                EducationRecord("2024", "2027", "浙江大学", "控制工程", "博士"),
            ),
        )
        boss = FakeBoss([[aliased]])
        store = FakeStore()

        result = self.runner(
            boss,
            store,
            target=1,
            require_major=False,
        ).run()

        self.assertEqual(result.final_count, 1)
        self.assertEqual(store.events[0][3], "人工智能")
        self.assertEqual(store.states[0][3], "人工智能")

    def test_refreshes_after_ten_distinct_unqualified_candidates(self):
        unqualified = [
            candidate(
                geek_id=f"bad-{index}",
                name=f"不合格{index}",
                education=(
                    EducationRecord("2024", "2027", "某大学", "气象学", "博士"),
                ),
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

    def test_skips_blocked_expectation_before_greeting(self):
        blocked = [
            candidate(
                geek_id="blocked-data",
                name="数据候选人",
                expect="上海 数据工程师",
            ),
            candidate(
                geek_id="blocked-product",
                name="产品候选人",
                expect="上海 产品经理",
            ),
            candidate(
                geek_id="blocked-analysis",
                name="分析候选人",
                expect="上海 商业分析",
            ),
        ]
        allowed = candidate(
            geek_id="allowed",
            name="正常候选人",
            expect="上海 后端开发",
        )
        boss = FakeBoss([[*blocked, allowed]])
        store = FakeStore()

        result = self.runner(boss, store, target=1).run()

        self.assertEqual(result.final_count, 1)
        self.assertEqual([item[0] for item in boss.greeted], ["allowed"])
        blocked_ids = {item.geek_id for item in blocked}
        self.assertTrue(blocked_ids.isdisjoint(store.deduped))
        self.assertEqual([item[0] for item in store.events], ["allowed"])
        self.assertEqual([item[0] for item in store.states], ["allowed"])
        self.assertEqual([item[0] for item in boss.sequence_calls], ["allowed"])
        self.assertEqual(len(boss.sent), 3)
        self.assertEqual(boss.sent, list(self.messages))
        self.assertTrue(
            blocked_ids.isdisjoint(item[0] for item in boss.sequence_calls)
        )

    def test_default_job_is_discovered_once_and_used_for_all_actions(self):
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[good]], job="用户当前岗位")
        store = FakeStore()

        result = self.runner(boss, store, target=1, job=None).run()

        self.assertEqual(result.job, "用户当前岗位")
        self.assertEqual(boss.recommend_calls, [(None, False)])
        self.assertEqual(boss.greeted[0][2], "用户当前岗位")
        self.assertEqual(boss.sequence_calls[0][2], "用户当前岗位")
        self.assertEqual(store.events[0][1], "用户当前岗位")

    def test_initial_login_batch_is_reused_without_second_recommend(self):
        good = candidate(geek_id="good", name="合格同学")
        initial_batch = RecommendationBatch("用户当前岗位", (good,))
        boss = FakeBoss([], job="用户当前岗位")
        store = FakeStore()

        result = self.runner(boss, store, target=1, job=None).run(
            initial_batch=initial_batch
        )

        self.assertEqual(result.final_count, 1)
        self.assertEqual(boss.recommend_calls, [])

    def test_stops_if_current_default_job_changes_during_run(self):
        first = candidate(geek_id="first", name="第一位")
        second = candidate(geek_id="second", name="第二位")
        boss = FakeBoss(
            [
                RecommendationBatch("岗位甲", (first,)),
                RecommendationBatch("岗位乙", (first, second)),
            ]
        )
        store = FakeStore()

        with self.assertRaisesRegex(CampaignError, "岗位发生变化"):
            self.runner(boss, store, target=2, job=None).run()

        self.assertEqual(store.count, 1)

    def test_sends_only_the_three_knowledge_base_messages_in_order(self):
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[good]])
        store = FakeStore()

        result = self.runner(boss, store, target=1).run()

        self.assertEqual(result.final_count, 1)
        self.assertEqual(boss.sent, list(self.messages))
        self.assertEqual(len(boss.sequence_calls), 1)
        self.assertEqual(boss.chat_calls, [])
        self.assertEqual(store.states[0][1], "waiting_application_status")
        self.assertEqual(self.delays, [1.25])

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

    def test_third_message_failure_keeps_greeted_without_advancing_stage(self):
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[good]])
        boss.fail_send_at = 2
        store = FakeStore()

        with self.assertRaises(CampaignError):
            self.runner(boss, store, target=1).run()

        self.assertEqual(boss.sent, ["知识库一", "知识库二"])
        self.assertEqual(store.count, 1)
        self.assertEqual(store.states, [])

    def test_first_message_failure_keeps_greeted_without_advancing_stage(self):
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[good]])
        boss.fail_send_at = 0
        store = FakeStore()

        with self.assertRaises(CampaignError):
            self.runner(boss, store, target=1).run()

        self.assertEqual(boss.sent, [])
        self.assertEqual(store.count, 1)
        self.assertEqual(store.states, [])

    def test_sequence_result_failures_keep_greeted_without_advancing_stage(self):
        for message in (
            "boss send-sequence --json 返回了无效 JSON",
            "三条知识库消息未全部验证",
        ):
            with self.subTest(message=message):
                good = candidate(geek_id="good", name="合格同学")
                boss = FakeBoss([[good]])
                boss.sequence_error = CampaignError(message)
                store = FakeStore()

                with self.assertRaisesRegex(CampaignError, message):
                    self.runner(boss, store, target=1).run()

                self.assertEqual(store.count, 1)
                self.assertEqual(store.events[0][0], "good")
                self.assertIn("good", store.deduped)
                self.assertEqual(store.states, [])
                self.assertEqual(boss.sent, [])

    def test_unconfirmed_greet_skips_candidate_and_continues(self):
        failed = candidate(geek_id="failed", name="未确认候选人")
        good = candidate(geek_id="good", name="合格同学")
        boss = FakeBoss([[failed, good], [failed, good]])
        boss.unconfirmed_greet_ids.add("failed")
        store = FakeStore()

        result = self.runner(boss, store, target=1).run()

        self.assertEqual(result.final_count, 1)
        self.assertEqual(
            [item[0] for item in boss.greeted],
            ["failed", "good"],
        )
        self.assertEqual(store.events[0][0], "good")
        self.assertEqual(len(boss.sequence_calls), 1)
        self.assertEqual(boss.sequence_calls[0][0], "good")

    def test_scan_limit_is_a_hard_stop(self):
        bad = [
            candidate(
                geek_id=f"bad-{index}",
                name=f"不合格{index}",
                education=(
                    EducationRecord("2024", "2027", "某大学", "气象学", "博士"),
                ),
            )
            for index in range(11)
        ]
        boss = FakeBoss([bad])
        store = FakeStore()

        with self.assertRaisesRegex(CampaignError, "检查候选人上限"):
            self.runner(boss, store, target=1, max_scans=10).run()

        self.assertEqual(boss.greeted, [])

    def test_scan_limit_cannot_exceed_policy_cap(self):
        with self.assertRaisesRegex(CampaignError, "1 到 1500"):
            self.runner(FakeBoss([]), FakeStore(), max_scans=1501)

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
