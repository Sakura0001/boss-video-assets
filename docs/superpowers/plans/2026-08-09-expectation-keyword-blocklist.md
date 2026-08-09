# 推荐牛人期望关键词拦截 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在主动打招呼前硬编码拦截求职期望包含“算法、通信、硬件、前端、unity、电气”任一关键词的候选人。

**Architecture:** Boss CLI 继续负责把推荐卡片的 `expect` 字段放入 JSON；顶层 Python 执行器在资格判断入口使用固定关键词元组做不区分大小写的子串匹配。业务说明仍先更新已安装的 `boss-zhaopin` skill，再通过现有同步脚本覆盖仓库镜像，但 Python 不从知识库动态加载这组关键词。

**Tech Stack:** Python 3.9 标准库、`unittest`、YAML/Markdown skill references、Git。

## Global Constraints

- 固定关键词必须恰好为：`算法`、`通信`、`硬件`、`前端`、`unity`、`电气`。
- 对 `expect` 移除空白并转换为小写后做子串匹配。
- `expect` 为空或未命中时继续现有资格判断；不得放宽毕业年份、学历、学校、专业或去重门槛。
- 命中时返回内部原因 `expectation_blocked`，不得进入 `boss greet`，不得发送三条固定消息。
- 不把候选人的完整求职期望写入本地状态或 Git。
- 先改已安装 source skill，再同步 `skills/boss-zhaopin/`；不独立维护仓库镜像。
- 验证期间只使用测试和 `--validate-only`，不得执行真实 Boss 招呼。

---

### Task 1: 用失败测试固定 Python 拦截行为

**Files:**
- Modify: `scripts/test_greet_only.py`
- Test: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: `Candidate.expect: str`、`EligibilityPolicy.evaluate(candidate) -> EligibilityResult`、`CampaignRunner.run()`。
- Produces: 默认不受限的候选人夹具，以及覆盖六个关键词和执行器跳过行为的回归测试。

- [ ] **Step 1: 调整候选人夹具并添加资格判断测试**

给 `candidate()` 增加 `expect="上海 后端开发"` 参数，并把构造 `Candidate` 时的固定值替换为 `expect=expect`。在 `EligibilityPolicyTests` 中加入：

```python
def test_rejects_blocked_expectation_keywords(self):
    cases = (
        "上海 算法工程师",
        "上海 电子/通信（行业）",
        "上海 硬件工程师",
        "上海 Web前端",
        "上海 Unity3D开发",
        "上海 电气工程师",
    )
    for expectation in cases:
        with self.subTest(expectation=expectation):
            result = self.policy.evaluate(candidate(expect=expectation))
            self.assertFalse(result.eligible)
            self.assertEqual(result.reason, "expectation_blocked")

def test_allows_expectation_without_blocked_keyword(self):
    result = self.policy.evaluate(candidate(expect="上海 后端开发"))
    self.assertTrue(result.eligible)

def test_allows_empty_expectation_to_continue_existing_gate(self):
    result = self.policy.evaluate(candidate(expect=""))
    self.assertTrue(result.eligible)
```

- [ ] **Step 2: 添加执行器级跳过测试**

在 `CampaignRunnerTests` 中构造先命中黑名单、后正常的两个候选人，运行到目标数 1，并断言只有正常候选人进入 `boss.greet`：

```python
def test_skips_blocked_expectation_before_greeting(self):
    blocked = candidate(geek_id="blocked", name="拦截候选人", expect="上海 算法工程师")
    allowed = candidate(geek_id="allowed", name="正常候选人", expect="上海 后端开发")
    boss = FakeBoss([[blocked, allowed]])
    store = FakeStore()

    result = self.runner(boss, store, target=1).run()

    self.assertEqual(result.final_count, 1)
    self.assertEqual([item[0] for item in boss.greeted], ["allowed"])
    self.assertNotIn("blocked", store.deduped)
```

- [ ] **Step 3: 运行新增测试并确认 RED**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.EligibilityPolicyTests.test_rejects_blocked_expectation_keywords \
  scripts.test_greet_only.CampaignRunnerTests.test_skips_blocked_expectation_before_greeting
```

Expected: FAIL；资格判断仍把黑名单期望视为合格，执行器会先对 `blocked` 调用打招呼。

### Task 2: 实现 Python 硬编码拦截

**Files:**
- Modify: `scripts/greet_only.py`
- Test: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: `_normalize(value: str) -> str` 和 `Candidate.expect`。
- Produces: `BLOCKED_EXPECTATION_KEYWORDS: Tuple[str, ...]` 以及 `EligibilityResult(False, "expectation_blocked")`。

- [ ] **Step 1: 添加固定关键词元组**

在顶层常量区加入：

```python
BLOCKED_EXPECTATION_KEYWORDS = (
    "算法",
    "通信",
    "硬件",
    "前端",
    "unity",
    "电气",
)
```

- [ ] **Step 2: 在资格判断入口拦截**

在 `EligibilityPolicy.evaluate()` 第一行资格检查前加入：

```python
normalized_expectation = _normalize(candidate.expect)
if any(
    _normalize(keyword) in normalized_expectation
    for keyword in BLOCKED_EXPECTATION_KEYWORDS
):
    return EligibilityResult(False, "expectation_blocked")
```

- [ ] **Step 3: 运行新增测试并确认 GREEN**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.EligibilityPolicyTests.test_rejects_blocked_expectation_keywords \
  scripts.test_greet_only.EligibilityPolicyTests.test_allows_expectation_without_blocked_keyword \
  scripts.test_greet_only.EligibilityPolicyTests.test_allows_empty_expectation_to_continue_existing_gate \
  scripts.test_greet_only.CampaignRunnerTests.test_skips_blocked_expectation_before_greeting
```

Expected: `Ran 4 tests` and `OK`。

- [ ] **Step 4: 运行完整顶层测试**

Run: `python3 -m unittest scripts.test_greet_only`

Expected: 全部通过且无错误或警告。

### Task 3: 用契约测试固定 source skill 规则

**Files:**
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/school_policy.yaml`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/auto_greet.md`
- Test: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`

**Interfaces:**
- Consumes: 已安装 skill 作为唯一业务说明来源。
- Produces: 明确、可检索的六关键词拦截规则，以及验证三处规则一致性的契约测试。

- [ ] **Step 1: 先添加 source skill 契约测试**

在 `test_skill_contract.py` 中加入：

```python
def test_expectation_keyword_blocklist_is_documented(self):
    documents = (
        self.skill_text,
        self.reference_text["school_policy.yaml"],
        self.reference_text["auto_greet.md"],
    )
    for document in documents:
        for keyword in ("算法", "通信", "硬件", "前端", "unity", "电气"):
            self.assertIn(keyword, document)
        self.assertIn("求职期望", document)
        self.assertIn("不打招呼", document)
```

- [ ] **Step 2: 运行契约测试并确认 RED**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
```

Expected: FAIL；现有 skill 未完整声明求职期望黑名单及“不打招呼”行为。

- [ ] **Step 3: 最小更新 source skill**

- 在 `SKILL.md` 的 Qualification Gate 增加：求职期望出现六个固定关键词之一时不回复、不打招呼。
- 在 `school_policy.yaml` 的 `rules` 增加同一条完整规则，注明 Python 使用硬编码、大小写不敏感的子串匹配。
- 在 `auto_greet.md` 的资格检查步骤中把求职期望黑名单放在学校、专业等判断之前。

- [ ] **Step 4: 运行 source skill 测试和校验**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
```

Expected: 四项均通过。

### Task 4: 同步镜像并完成全量验证

**Files:**
- Modify via sync: `skills/boss-zhaopin/SKILL.md`
- Modify via sync: `skills/boss-zhaopin/references/school_policy.yaml`
- Modify via sync: `skills/boss-zhaopin/references/auto_greet.md`
- Modify via sync: `skills/boss-zhaopin/scripts/test_skill_contract.py`
- Verify: `scripts/greet_only.py`
- Verify: `scripts/test_greet_only.py`

**Interfaces:**
- Consumes: 已通过 source skill 测试的文件。
- Produces: 与 source skill 字节一致的仓库镜像和可在 macOS/Windows 使用的 Python 执行器。

- [ ] **Step 1: 同步 source skill 到仓库镜像**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin
```

Expected: 输出同步成功；只改变本任务涉及的镜像文件。

- [ ] **Step 2: 验证镜像、Python 和只读启动校验**

Run:

```bash
python3 skills/boss-zhaopin/scripts/test_runtime_store.py
python3 skills/boss-zhaopin/scripts/test_skill_contract.py
python3 skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 -m unittest scripts.test_greet_only
python3 scripts/greet_only.py --validate-only
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/boss-zhaopin
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin --check
```

Expected: 所有测试和校验通过；`--validate-only` 输出 `messageCount: 3`，同步检查输出 `Skill mirror is in sync.`。

- [ ] **Step 3: 审查差异和隐私边界**

Run:

```bash
git diff --check
git status --short
git diff -- scripts/greet_only.py scripts/test_greet_only.py skills/boss-zhaopin
```

Expected: 无空白错误；差异仅包含固定关键词、资格判断、测试和对应 skill 镜像，不包含状态数据库、候选人资料、Cookie 或聊天内容。

- [ ] **Step 4: 独立代码审查**

让审查者重点检查：六个关键词是否恰好一致、`Unity` 大小写行为、黑名单是否在任何 `boss greet` 前生效、未命中者是否保持原行为、source/mirror 是否一致。

- [ ] **Step 5: 提交并推送**

Run:

```bash
git add scripts/greet_only.py scripts/test_greet_only.py \
  skills/boss-zhaopin/SKILL.md \
  skills/boss-zhaopin/references/school_policy.yaml \
  skills/boss-zhaopin/references/auto_greet.md \
  skills/boss-zhaopin/scripts/test_skill_contract.py \
  docs/superpowers/plans/2026-08-09-expectation-keyword-blocklist.md
git commit -m "feat: block greetings by candidate expectation"
git push origin codex/ai-greet-only-python
```

Expected: 提交成功，远端 `codex/ai-greet-only-python` 指向新提交。
