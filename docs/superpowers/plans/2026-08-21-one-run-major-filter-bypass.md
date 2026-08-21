# 单次主动招呼忽略专业筛选 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为主动打招呼执行器增加非持久化的 `--skip-major-filter`，使本次新推荐候选人的专业为空、缺失或无法识别时仍可通过，同时保留其余资格门槛并实跑当前账号当日 150 个已确认招呼。

**Architecture:** 命令行参数只在当前进程内转换为 `require_major`，由 `CampaignRunner` 显式传给 `EligibilityPolicy.evaluate()`；默认值始终为 `True`。已安装 `boss-zhaopin` skill 仍是业务唯一来源，先更新源规则和契约测试，再通过同步脚本生成仓库镜像；真实 Boss 动作只在全部离线验证、审查、提交和推送完成后串行执行。

**Tech Stack:** Python 3 标准库、`argparse`、`unittest`、Markdown/YAML skill 规则、SQLite、Boss CLI、Git。

> **状态：** Tasks 1–6 已完成；Task 7 正在执行；Task 8 待执行。最终独立审查无 Critical/Important 问题，结论为可进入真实执行。

## 文件与职责

- `scripts/greet_only.py`：解析单次参数、执行资格判断、输出可审计模式并串行打招呼。
- `scripts/test_greet_only.py`：锁定默认模式、放宽模式、其余门槛、去重和审计输出。
- `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md`：声明资格规则和单次例外的总入口。
- `/Users/yuyu/.codex/skills/boss-zhaopin/references/school_policy.yaml`：声明专业默认门槛和非持久化例外。
- `/Users/yuyu/.codex/skills/boss-zhaopin/references/auto_greet.md`：限定例外只作用于新候选人主动招呼。
- `/Users/yuyu/.codex/skills/boss-zhaopin/references/greetings.md`：使三条固定话术的前置条件与例外一致。
- `/Users/yuyu/.codex/skills/boss-zhaopin/references/risk_policy.yaml`：使默认未知专业阻断和单次主动招呼例外不矛盾。
- `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`：验证上述规则范围一致。
- `skills/boss-zhaopin/`：由源 skill 同步生成的仓库镜像，不独立编辑。

## 全局约束

- `--skip-major-filter` 默认关闭，不写配置、不写运行状态；进程结束后自动恢复默认专业门槛。
- 放宽模式仍按顺序检查期望九词、2027 届、学历、学校和长期去重。
- 放宽模式下可识别专业仍保存规范名，无法识别、为空或缺失时保存空字符串，不保存原始专业文本。
- 未读聊天、已有会话回复、简历评估和后续运行继续使用默认专业规则。
- 保持 Boss 当前默认岗位、三条固定纯文本话术、Asia/Shanghai 09:00–21:00、150 次日上限和 1500 人检查上限。
- 不并行发送，不使用 shell 循环发送；验证码、风控、投诉、岗位变化或状态修改失败时立即停止。
- 不提交候选人资料、聊天内容、本地 SQLite、Cookie、Token 或凭据。

---

### Task 1: 用失败测试锁定资格策略的双模式行为

**Files:**
- Modify: `scripts/test_greet_only.py:1-15`
- Modify: `scripts/test_greet_only.py:207-390`
- Test: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: `EligibilityPolicy.evaluate(candidate, *, require_major: bool = True)`。
- Produces: 默认严格、单次放宽、规范专业保留和其余门槛不变的回归契约。

- [ ] **Step 1: 添加放宽模式的资格测试**

在 `EligibilityPolicyTests` 中加入：

```python
def test_skip_major_filter_allows_unknown_empty_or_missing_current_major(self):
    cases = (
        (
            "unknown",
            (
                EducationRecord(
                    "2024", "2027", "浙江大学", "气象学", "博士"
                ),
            ),
        ),
        (
            "empty",
            (
                EducationRecord("2024", "2027", "浙江大学", "", "博士"),
            ),
        ),
        (
            "missing-current-degree",
            (
                EducationRecord(
                    "2020", "2024", "浙江大学", "人工智能", "本科"
                ),
                EducationRecord("2024", "2027", "某大学", "", "硕士"),
            ),
        ),
    )
    for label, education in cases:
        with self.subTest(label=label):
            base_info = (
                "27年应届生 / 硕士"
                if label == "missing-current-degree"
                else "27年应届生 / 博士"
            )
            result = self.policy.evaluate(
                candidate(base_info=base_info, education=education),
                require_major=False,
            )
            self.assertTrue(result.eligible)
            self.assertEqual(result.reason, "eligible")
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
```

- [ ] **Step 2: 添加默认行为和非专业门槛测试**

加入：

```python
def test_major_filter_is_required_by_default_for_unknown_and_empty_major(self):
    for raw_major in ("气象学", ""):
        with self.subTest(raw_major=raw_major):
            result = self.policy.evaluate(
                candidate(
                    education=(
                        EducationRecord(
                            "2024", "2027", "浙江大学", raw_major, "博士"
                        ),
                    ),
                )
            )
            self.assertFalse(result.eligible)
            self.assertEqual(result.reason, "major_unknown_or_ineligible")

def test_skip_major_filter_does_not_bypass_other_qualification_gates(self):
    cases = (
        ("expectation_blocked", candidate(expect="上海 数据工程师")),
        ("graduation_year", candidate(base_info="28年应届生 / 博士")),
        ("degree", candidate(base_info="27年应届生 / 大专")),
        (
            "school_unknown_or_ineligible",
            candidate(
                education=(
                    EducationRecord(
                        "2024", "2027", "某大学", "气象学", "博士"
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
```

- [ ] **Step 3: 运行新增资格测试并确认 RED**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.EligibilityPolicyTests.test_skip_major_filter_allows_unknown_empty_or_missing_current_major \
  scripts.test_greet_only.EligibilityPolicyTests.test_skip_major_filter_preserves_recognized_canonical_major \
  scripts.test_greet_only.EligibilityPolicyTests.test_major_filter_is_required_by_default_for_unknown_and_empty_major \
  scripts.test_greet_only.EligibilityPolicyTests.test_skip_major_filter_does_not_bypass_other_qualification_gates
```

Expected: ERROR，旧 `EligibilityPolicy.evaluate()` 不接受 `require_major`；默认模式测试可以通过，但整个命令非零退出。

---

### Task 2: 最小实现资格策略的单次专业例外

**Files:**
- Modify: `scripts/greet_only.py:381-409`
- Test: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: `require_major`，默认 `True`。
- Produces: `EligibilityResult`；放宽模式下未知专业的 `major` 为 `""`。

- [ ] **Step 1: 扩展资格判断签名和专业拒绝条件**

将签名和专业判断改为：

```python
def evaluate(
    self,
    candidate: Candidate,
    *,
    require_major: bool = True,
) -> EligibilityResult:
    normalized_expectation = _normalize(candidate.expect)
    if any(
        _normalize(keyword) in normalized_expectation
        for keyword in BLOCKED_EXPECTATION_KEYWORDS
    ):
        return EligibilityResult(False, "expectation_blocked")
    base = candidate.base_info
    if not re.search(r"(?:27年应届生|2027(?:年|届)?)", base):
        return EligibilityResult(False, "graduation_year")
    degree_match = re.search(r"(博士|硕士|研究生|本科)", base)
    if not degree_match:
        return EligibilityResult(False, "degree")
    school = self._find_school(candidate.education)
    if not school:
        return EligibilityResult(False, "school_unknown_or_ineligible")
    major = self._find_current_major(
        candidate.education, degree_match.group(1)
    )
    if require_major and not major:
        return EligibilityResult(False, "major_unknown_or_ineligible")
    return EligibilityResult(
        True,
        "eligible",
        school=school,
        major=major,
        degree=degree_match.group(1),
        grad_year=2027,
    )
```

- [ ] **Step 2: 运行 Task 1 的同一命令并确认 GREEN**

Expected: `Ran 4 tests`，`OK`。

- [ ] **Step 3: 运行完整资格测试**

Run:

```bash
python3 -m unittest scripts.test_greet_only.EligibilityPolicyTests
```

Expected: 全部 PASS，现有默认专业测试无回归。

- [ ] **Step 4: 提交资格策略和测试**

```bash
git add scripts/greet_only.py scripts/test_greet_only.py
git commit -m "feat: support optional greeting major gate"
```

Expected: 提交成功；不包含 skill、状态或候选人数据。

---

### Task 3: 用失败测试锁定 CLI、执行器、去重和审计输出

**Files:**
- Modify: `scripts/test_greet_only.py:1-15`
- Modify: `scripts/test_greet_only.py:760-1000`
- Test: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: `build_parser()`、`main(argv)`、`CampaignRunner(require_major=...)`。
- Produces: `skip_major_filter: bool`、`majorFilterMode: "required"|"skipped"` 和执行器双模式契约。

- [ ] **Step 1: 添加测试依赖和导入**

在测试文件顶部加入：

```python
import io
import json
from contextlib import redirect_stdout
```

并从 `scripts.greet_only` 导入 `main`。

- [ ] **Step 2: 扩展测试执行器工厂**

把 `CampaignRunnerTests.runner()` 改为：

```python
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
```

- [ ] **Step 3: 添加解析、验证输出和执行器测试**

在解析器测试中加入：

```python
def test_parser_major_filter_defaults_to_required_and_can_be_skipped(self):
    default_args = build_parser().parse_args([])
    skipped_args = build_parser().parse_args(["--skip-major-filter"])

    self.assertFalse(default_args.skip_major_filter)
    self.assertTrue(skipped_args.skip_major_filter)

def test_validate_only_reports_major_filter_mode(self):
    cases = (
        (["--validate-only"], "required"),
        (["--validate-only", "--skip-major-filter"], "skipped"),
    )
    for argv, expected_mode in cases:
        with self.subTest(expected_mode=expected_mode):
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(argv)
            payload = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["majorFilterMode"], expected_mode)
```

在 `CampaignRunnerTests` 中加入：

```python
def test_skip_major_filter_allows_unknown_major_and_preserves_dedupe(self):
    deduped = candidate(
        geek_id="old",
        name="已联系候选人",
        education=(
            EducationRecord("2024", "2027", "浙江大学", "气象学", "博士"),
        ),
    )
    fresh = candidate(
        geek_id="fresh",
        name="新候选人",
        education=(
            EducationRecord("2024", "2027", "浙江大学", "", "博士"),
        ),
    )
    boss = FakeBoss([[deduped, fresh]])
    store = FakeStore(deduped={"old"})
    output = io.StringIO()

    with redirect_stdout(output):
        result = self.runner(
            boss,
            store,
            target=1,
            require_major=False,
        ).run()

    events = [json.loads(line) for line in output.getvalue().splitlines()]
    selected = next(item for item in events if item["event"] == "job-selected")
    self.assertEqual(result.final_count, 1)
    self.assertEqual([item[0] for item in boss.greeted], ["fresh"])
    self.assertEqual(selected["majorFilterMode"], "skipped")
```

- [ ] **Step 4: 运行新增测试并确认 RED**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.BossCliTests.test_parser_major_filter_defaults_to_required_and_can_be_skipped \
  scripts.test_greet_only.BossCliTests.test_validate_only_reports_major_filter_mode \
  scripts.test_greet_only.CampaignRunnerTests.test_skip_major_filter_allows_unknown_major_and_preserves_dedupe
```

Expected: FAIL 或 ERROR；旧解析器没有参数、`main()` 没有输出模式、执行器也不接受 `require_major`。

---

### Task 4: 实现 CLI 到资格策略的显式数据流

**Files:**
- Modify: `scripts/greet_only.py:785-819`
- Modify: `scripts/greet_only.py:884-900`
- Modify: `scripts/greet_only.py:930-950`
- Modify: `scripts/greet_only.py:1060-1095`
- Modify: `scripts/greet_only.py:1122-1150`
- Test: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: `--skip-major-filter`。
- Produces: `CampaignRunner.require_major`、资格判断参数和 `majorFilterMode` 审计字段。

- [ ] **Step 1: 给执行器增加默认严格模式**

在 `CampaignRunner.__init__()` 的 `now` 后加入 `require_major: bool = True`，并保存：

```python
self.require_major = require_major
```

把候选人资格判断改为：

```python
eligibility = self.policy.evaluate(
    item,
    require_major=self.require_major,
)
```

- [ ] **Step 2: 给岗位选择事件增加审计模式**

在 `job-selected` JSON 对象中加入：

```python
"majorFilterMode": (
    "required" if self.require_major else "skipped"
),
```

- [ ] **Step 3: 新增命令行参数并贯通 main()**

在 `build_parser()` 中加入：

```python
parser.add_argument(
    "--skip-major-filter",
    action="store_true",
    help=(
        "仅本次主动招呼忽略专业门槛；"
        "期望、年份、学历、学校和去重规则仍生效"
    ),
)
```

在 `--validate-only` JSON 中加入：

```python
"majorFilterMode": (
    "skipped" if args.skip_major_filter else "required"
),
```

创建执行器时加入：

```python
require_major=not args.skip_major_filter,
```

- [ ] **Step 4: 运行 Task 3 的同一命令并确认 GREEN**

Expected: `Ran 3 tests`，`OK`。

- [ ] **Step 5: 运行完整顶层测试**

Run:

```bash
python3 -m unittest scripts.test_greet_only
```

Expected: 全部 PASS，0 failures，0 errors。

- [ ] **Step 6: 提交 CLI、执行器和测试**

```bash
git add scripts/greet_only.py scripts/test_greet_only.py
git commit -m "feat: expose one-run major filter bypass"
```

Expected: 提交成功；默认模式仍为严格专业筛选。

---

### Task 5: 用契约测试驱动源 skill 的例外范围

**Files:**
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py:80-145`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md:25-45`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/school_policy.yaml:50-65`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/auto_greet.md:3-19`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/greetings.md:3-10`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/risk_policy.yaml:14-38`
- Generated by sync: `skills/boss-zhaopin/`

**Interfaces:**
- Consumes: 已安装 source skill 作为唯一业务来源。
- Produces: 五处一致声明的单次主动招呼例外，以及同步后的仓库镜像。

- [ ] **Step 1: 先运行未修改 skill 的独立行为基线（RED）**

派发一个不继承本会话结论的只读子代理，给它当前安装的
`/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md` 及其必需引用，并只提供下面的现实请求：

```text
用户要求：本次在 Boss 推荐牛人中打 150 个招呼，专业字段完全不参与筛选，
但求职期望黑名单、2027 届、学历、学校和去重仍须生效；以后运行和未读回复
恢复原专业规则。请说明应使用什么确定性入口和参数，并判断专业为空的候选人
本次能否通过。不要执行任何真实 Boss 动作。
```

Expected: 当前 skill 没有单次专业例外或对应参数，子代理无法从权威规则得出
`--skip-major-filter`，或仍按默认规则拒绝空专业。记录它的实际结论作为 RED 证据，
不得向它泄露计划中的预期实现。

> 2026-08-21 RED 证据：独立只读子代理只依据当前安装 skill，结论为“没有支持
> 本次忽略专业的确定性参数或入口；专业为空时不能通过；规则对未读回复和推荐
> 招呼统一生效；任何临时参数都只能是臆造”。未执行任何真实 Boss 动作。

- [ ] **Step 2: 先增加源 skill 契约测试**

在 `test_skill_contract.py` 中加入：

```python
def test_one_run_major_filter_bypass_is_explicitly_scoped(self):
    documents = (
        self.skill,
        self.reference_text["school_policy.yaml"],
        self.reference_text["auto_greet.md"],
        self.reference_text["greetings.md"],
        self.reference_text["risk_policy.yaml"],
    )
    required_semantics = (
        "--skip-major-filter",
        "专业为空、缺失或无法识别",
        "仅适用于本次主动打招呼",
        "不适用于未读聊天",
        "不得绕过求职期望、2027 届、学历、学校和去重门槛",
    )
    for document in documents:
        for semantic in required_semantics:
            self.assertIn(semantic, document)
```

- [ ] **Step 3: 运行源契约测试并确认 RED**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
```

Expected: FAIL；当前源规则尚未声明 `--skip-major-filter`。

- [ ] **Step 4: 在五处源规则中加入同一范围声明**

把以下完整语义分别放入 `SKILL.md` 的 Qualification Gate、`school_policy.yaml` 的 rules、`auto_greet.md` 的资格步骤后、`greetings.md` 的前置条件和 `risk_policy.yaml` 的 notes：

```text
仅当用户明确要求本次主动打招呼不限制专业且执行器显式携带 --skip-major-filter 时，专业为空、缺失或无法识别也可继续；该例外仅适用于本次主动打招呼，不持久化，不适用于未读聊天、已有会话回复、简历评估或后续运行，也不得绕过求职期望、2027 届、学历、学校和去重门槛。
```

同时把 `risk_policy.yaml` 的默认未知字段阻断项改为不矛盾的完整说明：

```yaml
- "学校、学历或毕业年份不符合或无法识别；专业不符合或无法识别时默认阻断，仅本次主动打招呼显式携带 --skip-major-filter 的已批准例外除外"
```

- [ ] **Step 5: 运行源 skill 测试并确认 GREEN**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/yuyu/.codex/skills/boss-zhaopin
```

Expected: 四项全部退出 0。

- [ ] **Step 6: 运行修改后 skill 的独立行为验证（GREEN）**

派发一个全新的只读子代理，仍只给它已更新的 source skill、必需引用和 Step 1
中的同一现实请求；不提供设计文档、实现计划、RED 结果或预期答案。

Expected: 子代理明确选择 `scripts/greet_only.py --skip-major-filter --target 150`；
允许专业为空、缺失或无法识别；仍拦截期望九词并要求 2027 届、合格学历、目标学校
和长期去重；明确该例外不持久化且不适用于未读聊天或后续运行。不得执行真实动作。

> 2026-08-21 首次前向评估实际发现：更新后的规则已正确限定空专业仅可在本次主动打招呼例外中继续，并保留其余门槛；但权威文档没有给出完整的确定性执行器入口或 150 人单命令。评估者因此无法确定 `--skip-major-filter` 属于顶层 runner，并推断它可能传给 `boss greet`。该结果不构成最终 GREEN。
>
> 契约驱动修复：新增 source contract，要求 macOS/Linux 与 Windows 的完整 `scripts/greet_only.py` 入口，并锁定“该参数属于 runner、不得传给 `boss greet`”。随后在 `SKILL.md`、`auto_greet.md` 与 `boss_cli.md` 中补充入口说明。须由新的独立评估者重新执行本步骤后，才能记录最终行为 GREEN。
>
> 2026-08-21 第二次前向评估实际发现：已能识别完整命令、参数归属及核心单次范围，但仍无法从文档确定省略 `--job` 时使用 Boss 推荐页当前默认岗位，而非 `agent.yaml` 的默认关键词或强制覆盖；也未能确认 skip 模式下已识别专业的规范名保留，以及未知、为空或缺失专业以空字符串写入本地状态且不保存原始文本。该结果仍不构成最终 GREEN。
>
> 契约驱动修复：新增 source contract，锁定当前默认岗位和专业状态规范化/隐私语义；随后在 `SKILL.md`、`auto_greet.md`、`boss_cli.md` 和 `school_policy.yaml` 中补充相同约束。须由新的独立评估者重新执行本步骤后，才能记录最终行为 GREEN。
>
> 2026-08-21 第三次独立前向评估 GREEN：评估者检索到完整的 macOS/Linux 和 Windows 命令，正确识别 `--skip-major-filter` 属于 `scripts/greet_only.py` 而非 `boss greet`；省略 `--job` 时使用 Boss 推荐页当前默认岗位，而非 `agent.yaml` 关键词。评估者还确认已识别专业保留批准的规范名称，未知、为空或缺失专业写入空字符串且不保存原始文本；九项求职期望黑名单、2027 届、学历、目标学校、去重、150/1500 上限及风险门槛继续生效；例外不持久化，且不适用于未读聊天、已有会话回复、简历评估或后续运行。评估者仅指出下游报告/展示行为未作规定；该项超出本功能的资格与状态契约，无需扩展规则。

- [ ] **Step 7: 从源 skill 同步仓库镜像**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin --check
```

Expected: 首条同步成功；第二条输出 `Skill mirror is in sync.`。

- [ ] **Step 8: 提交源规则的仓库镜像和计划**

```bash
git add skills/boss-zhaopin \
  docs/superpowers/plans/2026-08-21-one-run-major-filter-bypass.md
git commit -m "docs: scope one-run greeting major bypass"
```

Expected: 提交只包含同步镜像和本实施计划；源安装目录本身不属于仓库。

---

### Task 6: 完整验证、独立审查、提交状态检查和推送

**Files:**
- Verify: `scripts/greet_only.py`
- Verify: `scripts/test_greet_only.py`
- Verify: `skills/boss-zhaopin/`
- Verify: `docs/superpowers/specs/2026-08-21-one-run-major-filter-bypass-design.md`
- Verify: `docs/superpowers/plans/2026-08-21-one-run-major-filter-bypass.md`

**Interfaces:**
- Consumes: Tasks 1–5 的代码、测试和规则镜像。
- Produces: 可用于真实运行的已验证、已审查、已推送版本。

> 最终审查发现 greet-only runner 的预检文档与实现不一致；代码提交 `88cda35` 已在执行锁内实现自动 `init`、`purge`、CLI/login 验证及首个推荐批次。对应 source skill 契约与文档已补充。本 Task 仍待最终复审和推送，不标记完成。

- [ ] **Step 1: 运行完整离线验证**

Run:

```bash
python3 -m unittest scripts.test_greet_only
python3 skills/boss-zhaopin/scripts/test_runtime_store.py
python3 skills/boss-zhaopin/scripts/test_skill_contract.py
python3 skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 scripts/greet_only.py --validate-only
python3 scripts/greet_only.py --validate-only --skip-major-filter
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/yuyu/.codex/skills/boss-zhaopin
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin --check
git diff --check
```

Expected: 全部退出 0；默认校验输出 `majorFilterMode: required`，放宽校验输出 `majorFilterMode: skipped`，两者 `messageCount` 均为 3。

- [ ] **Step 2: 审查变更和隐私范围**

Run:

```bash
git status --short
git log -5 --oneline --decorate
git show --stat --oneline HEAD~2..HEAD
git diff origin/codex/ai-greet-only-python...HEAD -- \
  scripts/greet_only.py scripts/test_greet_only.py skills/boss-zhaopin \
  docs/superpowers/specs/2026-08-21-one-run-major-filter-bypass-design.md \
  docs/superpowers/plans/2026-08-21-one-run-major-filter-bypass.md
```

Expected: 仅包含本功能代码、测试、规则镜像和设计文档；没有 SQLite、候选人资料、聊天内容、Cookie 或凭据。

- [ ] **Step 3: 独立代码审查**

审查者逐项确认：默认 `require_major=True`；开关只从 CLI 进入当前 `CampaignRunner`；九项期望黑名单先于专业判断；放宽模式仍执行年份、学历、学校和去重；未知专业只保存空字符串；验证输出与 `job-selected` 一致；source/mirror 无漂移。

Expected: 无阻断问题；若发现问题，先补失败测试、修复并重跑 Step 1。

- [ ] **Step 4: 确认工作树并推送**

Run:

```bash
git status --short
git push origin codex/ai-greet-only-python
git status --short
```

Expected: 推送成功，工作树为空，当前 HEAD 与远端分支同步。

---

### Task 7: 初始化当前账号并验证真实运行前置条件

**Files:**
- Read/write local runtime only: `/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4/state.sqlite3`
- Execute: `scripts/greet_only.py`

**Interfaces:**
- Consumes: 当前 Boss 登录态、account-4 独立状态和已验证参数。
- Produces: 当日初始计数、登录校验和明确的 `skipped` 运行模式。

- [ ] **Step 1: 初始化、清理并读取本地状态**

Run:

```bash
export BOSS_ZHAOPIN_STATE_DIR="/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4"
export BOSS_SKILL_ROOT="/Users/yuyu/.codex/skills/boss-zhaopin"
export BOSS_RUN_DATE="2026-08-21"
export BOSS_RUN_NOW="$(date -Iseconds)"
python3 "$BOSS_SKILL_ROOT/scripts/runtime_store.py" init
python3 "$BOSS_SKILL_ROOT/scripts/runtime_store.py" purge --as-of "$BOSS_RUN_NOW"
python3 "$BOSS_SKILL_ROOT/scripts/runtime_store.py" greeting-count --date "$BOSS_RUN_DATE"
python3 "$BOSS_SKILL_ROOT/scripts/runtime_store.py" due-followups --as-of "$BOSS_RUN_NOW"
```

Expected: 初始化和清理成功；`greeting-count` 为 0。`due-followups` 只用于启动审计，本次不处理未读或跟进消息。

- [ ] **Step 2: 校验 CLI、登录和本次参数**

Run:

```bash
command -v boss
boss help
boss list --unread
python3 scripts/greet_only.py \
  --validate-only --skip-major-filter --target 150 --max-scans 1500
```

Expected: `boss` 可通过 PATH 解析，登录有效；只读校验输出 `majorFilterMode: skipped`、`jobMode: current-default`、`target: 150`、`messageCount: 3`。`boss list --unread` 仅验证登录，不回复聊天。

- [ ] **Step 3: 核对运行时互斥和设备唤醒条件**

Run:

```bash
pgrep -af "scripts/greet_only.py" || true
test ! -e "$BOSS_ZHAOPIN_STATE_DIR/greet-only.lock"
pmset -g batt
```

Expected: 没有另一实例、没有遗留锁，设备有电或接通电源。若发现活跃实例或无法确认锁归属，不删除锁并停止启动。

---

### Task 8: 串行实跑 150 个招呼并验证结果

**Files:**
- Write local runtime only: `/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4/state.sqlite3`
- Execute: `scripts/greet_only.py`

**Interfaces:**
- Consumes: 当前默认岗位、放宽专业模式及其他默认资格门槛。
- Produces: 最多 150 个当日 `greeted` 事件、去重记录和 `waiting_resume` 状态。

- [ ] **Step 1: 启动临时防休眠和单一执行器**

在独立受控终端会话启动：

```bash
caffeinate -dimsu -t 14400
```

再启动唯一真实执行器：

```bash
BOSS_ZHAOPIN_STATE_DIR="/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4" \
python3 scripts/greet_only.py \
  --skip-major-filter --target 150 --max-scans 1500
```

Expected: 首个 `job-selected` 事件包含 `majorFilterMode: skipped`，并说明使用 Boss 当前默认岗位；随后每个成功周期只增加一个已确认招呼。

- [ ] **Step 2: 持续监控但不并行发送**

每次只轮询执行器输出和只读计数，不启动第二个 runner，也不使用 shell 循环发送：

```bash
BOSS_ZHAOPIN_STATE_DIR="/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4" \
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/runtime_store.py \
  greeting-count --date 2026-08-21
```

Expected: 计数单调增加且不超过 150。验证码、风控、投诉、岗位变化、send/chat/greet 状态修改失败或平台权益上限出现时立即终止 runner，以数据库已确认计数为准；仅“按钮仍可用、无法确认成功”可跳过单人继续。

- [ ] **Step 3: 验证最终计数、状态、去重和数据库完整性**

Run:

```bash
export BOSS_ZHAOPIN_STATE_DIR="/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4"
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/runtime_store.py \
  greeting-count --date 2026-08-21
sqlite3 "$BOSS_ZHAOPIN_STATE_DIR/state.sqlite3" \
  "SELECT COUNT(*), COUNT(DISTINCT candidate_id) FROM events WHERE event_type='greeted' AND substr(occurred_at,1,10)='2026-08-21'; SELECT COUNT(*) FROM candidates WHERE stage='waiting_resume' AND substr(last_contact_at,1,10)='2026-08-21'; SELECT COUNT(*) FROM events e LEFT JOIN dedupe d ON d.candidate_id=e.candidate_id WHERE e.event_type='greeted' AND substr(e.occurred_at,1,10)='2026-08-21' AND d.candidate_id IS NULL; PRAGMA integrity_check;"
pgrep -af "scripts/greet_only.py" || true
test ! -e "$BOSS_ZHAOPIN_STATE_DIR/greet-only.lock"
```

Expected on full completion: `greeting-count` 为 150；当日 greeted 总数与不同 candidate_id 均为 150；当日 `waiting_resume` 为 150；缺失 dedupe 为 0；`integrity_check` 为 `ok`；runner 已退出且锁已释放。

- [ ] **Step 4: 同步新增长期去重到其余账号状态**

仅在 Step 3 数据库完整性通过后，把 account-4 的长期去重并入其余已存在账号数据库；保留各账号原有记录：

```bash
sqlite3 /Users/yuyu/.codex/state/boss-zhaopin/state.sqlite3 \
  "ATTACH DATABASE '/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4/state.sqlite3' AS source; INSERT OR IGNORE INTO dedupe SELECT * FROM source.dedupe; PRAGMA integrity_check;"
sqlite3 /Users/yuyu/.codex/state/boss-zhaopin/accounts/account-2/state.sqlite3 \
  "ATTACH DATABASE '/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4/state.sqlite3' AS source; INSERT OR IGNORE INTO dedupe SELECT * FROM source.dedupe; PRAGMA integrity_check;"
sqlite3 /Users/yuyu/.codex/state/boss-zhaopin/accounts/account-3/state.sqlite3 \
  "ATTACH DATABASE '/Users/yuyu/.codex/state/boss-zhaopin/accounts/account-4/state.sqlite3' AS source; INSERT OR IGNORE INTO dedupe SELECT * FROM source.dedupe; PRAGMA integrity_check;"
```

Expected: 三个目标数据库均返回 `ok`，只新增缺失的去重行，不覆盖已有记录。随后比较四个数据库的 dedupe 总数，确认一致。

- [ ] **Step 5: 停止本次防休眠会话并报告结果**

只终止 Task 8 Step 1 启动的 `caffeinate` 进程，不影响用户其他进程。报告已验证完成数、专业模式、仍生效的期望九词与其他门槛；不报告候选人姓名或资料。若平台限制提前停止，报告实际已确认数量和停止原因，不把未确认动作计入完成数。
