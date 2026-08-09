# AI Greeting Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three post-greeting messages with the approved AI application R&D copy, keep them plain-text and exact, and synchronize the authoritative installed skill into the repository mirror.

**Architecture:** The installed `boss-zhaopin` skill remains the only business source. Its Markdown knowledge base stores exactly three single-line inline-code messages; the existing Python runner dynamically parses those messages, so no runtime code change is needed. Contract tests pin the exact copy and consistency rules explicitly scope the approved compensation and work-pattern claims without allowing generated extensions.

**Tech Stack:** Markdown/YAML knowledge files, Python 3 `unittest`, existing `sync_repo_copy.py`, Git.

## Global Constraints

- Send exactly three messages in the approved order and as plain text; do not include Markdown `**` markers.
- Treat the complete third message as approved fixed copy, including “年终奖可以保证”; do not reuse, rewrite, split, or expand its compensation, overtime, or career claims elsewhere.
- Do not modify `scripts/greet_only.py` or Boss CLI behavior; they already load and verify knowledge-base copy dynamically.
- Modify the installed source skill first, validate it, and only then synchronize `skills/boss-zhaopin/`.
- Do not run `boss`, open a live recruiting session, or send any candidate message during implementation or testing.
- Do not stage local state, candidate data, chat text, credentials, or unrelated files.

---

### Task 1: Update and validate the authoritative source skill

**Files:**
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py:32-38`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/greetings.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/recruiter_voice.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/risk_policy.yaml`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_salary.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_worktime.md`
- Test: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`

**Interfaces:**
- Consumes: the three approved messages in `docs/superpowers/specs/2026-08-09-ai-greeting-copy-design.md`.
- Produces: a validated installed skill whose `references/greetings.md` exposes exactly three ordered, single-line inline-code messages to `load_greeting_messages(path) -> Tuple[str, str, str]`.

- [ ] **Step 1: Replace the old opening assertion with an exact three-message contract test**

Use this test body in place of `test_approved_opening_is_present`:

```python
def test_approved_proactive_greetings_are_exact_plain_text(self):
    expected = (
        (
            "真人化说明",
            "我们团队正在探索AI时代下一代智能应用形态，围绕大语言模型（LLM）、AI Agent、RAG、知识增强、智能工作流、多Agent协同等技术方向，打造能够理解任务、主动分析、自动执行的企业级智能应用，让AI真正进入实际业务场景。",
        ),
        (
            "一条合并岗位介绍",
            "目前AI Agent方向处于快速发展阶段，团队持续投入前沿技术探索和产品落地，覆盖智能助手、自动化决策、智能分析、企业知识管理、AIOps等多个场景。加入团队后可以深入参与从模型应用设计、Agent架构搭建到生产系统落地的完整流程，积累AI时代核心技术能力。",
        ),
        (
            "索要附件简历",
            "我看了一下你的背景，和我们AI应用研发方向有一定匹配度。如果方便的话，辛苦发我一份附件简历，我可以进一步帮你评估岗位匹配情况，也欢迎你了解一下我们的技术方向和发展机会。我们这边相对wlb一些，自盈利部门，年终奖可以保证，日常加班可以随意申报，也不会强制要求来。部门整体氛围好，新老员工无断层现象，跳槽到外面的员工都有很大幅度的涨薪，不需要担心个人竞争力。",
        ),
    )
    greetings = self.reference_text["greetings.md"]
    positions = []
    for heading, message in expected:
        section = re.search(
            rf"^###\s+{re.escape(heading)}\s*$"
            rf"(?P<body>.*?)(?=^###\s+|\Z)",
            greetings,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(section)
        snippets = re.findall(r"`([^`\r\n]+)`", section.group("body"))
        self.assertEqual(snippets, [message])
        self.assertNotIn("**", snippets[0])
        positions.append(greetings.index(message))
    self.assertEqual(positions, sorted(positions))
```

- [ ] **Step 2: Run the new contract test and verify the red state**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
```

Expected: FAIL only in `test_approved_proactive_greetings_are_exact_plain_text` because `greetings.md` still contains the old database introduction.

- [ ] **Step 3: Replace the three messages in the source knowledge base**

Keep the three existing `###` headings and place these exact single-line values under them:

```markdown
### 真人化说明

`我们团队正在探索AI时代下一代智能应用形态，围绕大语言模型（LLM）、AI Agent、RAG、知识增强、智能工作流、多Agent协同等技术方向，打造能够理解任务、主动分析、自动执行的企业级智能应用，让AI真正进入实际业务场景。`

### 一条合并岗位介绍

`目前AI Agent方向处于快速发展阶段，团队持续投入前沿技术探索和产品落地，覆盖智能助手、自动化决策、智能分析、企业知识管理、AIOps等多个场景。加入团队后可以深入参与从模型应用设计、Agent架构搭建到生产系统落地的完整流程，积累AI时代核心技术能力。`

### 索要附件简历

`我看了一下你的背景，和我们AI应用研发方向有一定匹配度。如果方便的话，辛苦发我一份附件简历，我可以进一步帮你评估岗位匹配情况，也欢迎你了解一下我们的技术方向和发展机会。我们这边相对wlb一些，自盈利部门，年终奖可以保证，日常加班可以随意申报，也不会强制要求来。部门整体氛围好，新老员工无断层现象，跳槽到外面的员工都有很大幅度的涨薪，不需要担心个人竞争力。`
```

Retain the existing eligibility precondition. Replace the old instruction that forbids proactive schedule or compensation details with an exact-copy rule: the three messages are approved only as complete fixed strings and cannot be rewritten or extended.

- [ ] **Step 4: Align recruiter voice and risk policy with the approved exception**

In `recruiter_voice.md`:

- Replace the two old database fixed-opening strings with the three exact messages from Step 3.
- Replace the broad “不提 AI、Agent、自动回复、知识库、内部筛选或系统判断” rule with: `不得向候选人说明消息由 AI、Agent、自动化、知识库或系统代为处理；批准岗位介绍中的 AI、Agent 技术名词不在此限。`
- Scope the long-copy restriction as: `除 greetings.md 的三条批准固定话术外，不使用公告腔、客服腔或自行生成的大段营销文案。`

In `risk_policy.yaml`, add this note without weakening any stop condition:

```yaml
  - "references/greetings.md 的三条主动话术已由用户批准，允许按原文完整发送；其中奖金、作息和职业发展描述不得拆分复用、改写或扩写为新的承诺。"
```

- [ ] **Step 5: Align salary and worktime FAQ boundaries**

Add to `faq_salary.md`:

```markdown
主动打招呼时，允许将 `greetings.md` 第三条完整原样发送，其中“年终奖可以保证”视为已批准固定口径。不得单独抽取、改写或扩展为奖金金额、月数、比例、发放条件或其他待遇承诺；候选人继续追问这些细节时仍使用下述保守回复。
```

Add to `faq_worktime.md`:

```markdown
主动打招呼时，允许将 `greetings.md` 第三条完整原样发送，其中 WLB、加班申报和“不强制要求来”的描述视为已批准固定口径。不得据此扩写成永不加班、固定调休、远程办公或其他未记录安排；候选人继续追问时仍使用下述统一口径。
```

- [ ] **Step 6: Run the authoritative source validation suite and verify green**

Run each command separately:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
```

Expected: every unittest reports `OK`; `quick_validate.py` reports `Skill is valid!`.

### Task 2: Synchronize, verify, commit, and publish the repository mirror

**Files:**
- Modify: `skills/boss-zhaopin/scripts/test_skill_contract.py`
- Modify: `skills/boss-zhaopin/references/greetings.md`
- Modify: `skills/boss-zhaopin/references/recruiter_voice.md`
- Modify: `skills/boss-zhaopin/references/risk_policy.yaml`
- Modify: `skills/boss-zhaopin/references/faq_salary.md`
- Modify: `skills/boss-zhaopin/references/faq_worktime.md`

**Interfaces:**
- Consumes: the green, authoritative source skill produced by Task 1.
- Produces: a byte-identical repository mirror consumed by `scripts/greet_only.py`, with a pushed Git commit on `codex/ai-greet-only-python`.

- [ ] **Step 1: Synchronize the complete source skill into the repository mirror**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin
```

Expected: the command reports that the repository copy was synchronized. It must not copy SQLite state, credentials, chats, resumes, or cache files.

- [ ] **Step 2: Confirm the diff is limited to the six approved mirror files**

Run:

```bash
git status --short
git diff -- skills/boss-zhaopin
git diff --check
```

Expected: only the six files listed under Task 2 are modified, with no whitespace errors and no unrelated source, state, or candidate files.

- [ ] **Step 3: Run repository-mirror and runner tests**

Run each command separately:

```bash
python3 skills/boss-zhaopin/scripts/test_runtime_store.py
python3 skills/boss-zhaopin/scripts/test_skill_contract.py
python3 skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 scripts/test_greet_only.py
python3 scripts/greet_only.py --validate-only
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin --check
```

Expected: every unittest reports `OK`; `--validate-only` returns JSON with `"validated": true` and `"messageCount": 3`; sync check reports `Skill mirror is in sync.` No command opens Boss or sends a message.

- [ ] **Step 4: Stage only the approved mirror changes and inspect the staged patch**

Run:

```bash
git add skills/boss-zhaopin/scripts/test_skill_contract.py skills/boss-zhaopin/references/greetings.md skills/boss-zhaopin/references/recruiter_voice.md skills/boss-zhaopin/references/risk_policy.yaml skills/boss-zhaopin/references/faq_salary.md skills/boss-zhaopin/references/faq_worktime.md
git diff --cached --check
git diff --cached --stat
```

Expected: six files staged, no whitespace errors, and no design/plan/state/privacy files accidentally added.

- [ ] **Step 5: Commit the verified implementation**

Run:

```bash
git commit -m "feat: update proactive AI greeting copy"
```

Expected: one commit containing only the six mirror files.

- [ ] **Step 6: Push and verify the branch state**

Run:

```bash
git push origin codex/ai-greet-only-python
git status --short --branch
git log -2 --oneline --decorate
```

Expected: local and remote `codex/ai-greet-only-python` point to the implementation commit and the working tree is clean.
