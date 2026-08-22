# Two-Message Proactive Greeting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将主动招呼后的三条固定消息改为两条用户批准的纯文本，取消附件简历请求语义，并在发送成功后进入 `waiting_application_status`。

**Architecture:** `scripts/greet_only.py` 继续从仓库 skill 镜像读取固定话术，并通过一次 `boss send-sequence` 在精确会话中顺序发送。Boss CLI 把消息序列约束从恰好三条改为恰好两条；已安装的 `boss-zhaopin` 源 skill 先更新并通过契约测试，再由同步脚本生成仓库镜像。运行数据库无需迁移，因为 `waiting_application_status` 已是现有阶段。

**Tech Stack:** Python 3 `unittest`、TypeScript、Node.js test runner、Markdown/YAML Codex skill、Git

---

## Scope

包含：

- 第一、二段合并为已批准的压缩介绍。
- 原第三段替换为已批准的匹配与转投提示。
- 平台默认招呼后只发送两条固定纯文本。
- 主动招呼流程不触发 `request-attachment-resume` 或 `--request-resume`。
- 两条消息验证成功后写入 `waiting_application_status`。
- 更新 macOS 源 skill、仓库镜像、Python、Boss CLI 和当前使用说明。

不包含：

- 不启动 Boss、不登录、不发送真实消息。
- 不删除 Boss CLI 供其他人工流程使用的求简历能力。
- 不迁移或重写历史 `waiting_resume` 数据。
- 不调用 `boss preview`；新文案中的“在线简历”指推荐页当前可见资料。
- 不修改求职期望黑名单、学校、学历、毕业年份、专业和去重规则。
- 不改写历史设计文档和历史实施计划。

## File Map

- `scripts/test_greet_only.py`：两条知识库消息、CLI 参数、流程状态的回归测试。
- `scripts/greet_only.py`：两段知识库解析、两消息验证和状态流转。
- `tools/boss-cli/test/send-sequence.test.mjs`：两消息序列约束测试。
- `tools/boss-cli/src/toolset/send.ts`：恰好两条消息的运行时校验。
- `tools/boss-cli/src/cli/cliRouter.ts`、`tools/boss-cli/README.md`、`tools/boss-cli/docs/boss-url-map.md`：两消息命令说明。
- `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`：源 skill 的失败优先契约测试。
- `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md` 与相关 `references/`：唯一业务来源。
- `skills/boss-zhaopin/`：由同步脚本生成的仓库镜像。
- `README.md`、`docs/windows-setup.md`：当前用户运行说明。
- `docs/superpowers/specs/2026-08-22-proactive-greeting-transfer-message-design.md`：已批准设计。

### Task 1: Lock the new behavior with failing tests

**Files:**

- Modify: `scripts/test_greet_only.py`
- Modify: `tools/boss-cli/test/send-sequence.test.mjs`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py`

- [ ] **Step 1: Update the Python expectations before production code**

Use these exact approved messages:

```python
expected = (
    "我们团队正在探索AI时代的下一代智能应用，围绕大语言模型（LLM）、AI Agent、RAG、知识增强、智能工作流和多Agent协同，打造能理解任务、主动分析并自动执行的企业级应用。目前已覆盖智能助手、自动化决策、智能分析、企业知识管理和AIOps等场景，加入后可参与从模型应用设计、Agent架构搭建到生产落地的完整流程，积累AI时代的核心技术能力。",
    "我看了一下你的背景和在线简历，和我们AI应用研发方向有一定匹配度。欢迎你了解一下我们的技术方向和发展机会。我们这边相对wlb一些，自盈利部门，年终奖可以保证，日常加班可以随意申报，也不会强制要求来。部门整体氛围好，新老员工无断层现象，跳槽到外面的员工都有很大幅度的涨薪，不需要担心个人竞争力。如果你现在已投递的话，也开始对比下现在投递的部门，看是否想转投，现在还可以转，后面正式进流程就没办法在转投了",
)
```

Change test fixtures to headings `技术与岗位介绍` and `匹配与转投提示`, change fake messages to two items, expect `messagesVerified: 2`, assert the `send-sequence` arguments contain neither `--request-resume` nor `request-attachment-resume`, and expect the final state `waiting_application_status`.

Add failure cases for malformed JSON and `messagesVerified != 2`; both must leave the candidate at `greeted` and must not write `waiting_application_status`. Keep the existing send interruption test so a failure before the second message also cannot advance state.

- [ ] **Step 2: Update the CLI test before CLI production code**

```javascript
test('accepts exactly two distinct non-empty knowledge-base messages', () => {
  assert.deepEqual(validateMessageSequence(['第一条', '第二条']), ['第一条', '第二条']);
});

test('rejects incomplete, empty, duplicate, or oversized message sequences', () => {
  assert.throws(() => validateMessageSequence(['第一条']), /恰好两条/);
  assert.throws(() => validateMessageSequence(['第一条', ' ']), /不能为空/);
  assert.throws(() => validateMessageSequence(['第一条', '第一条']), /不能重复/);
  assert.throws(() => validateMessageSequence(['第一条', '第二条', '第三条']), /恰好两条/);
});
```

- [ ] **Step 3: Update the source skill contract before skill content**

Require exactly the two headings and messages, require `waiting_application_status`, and require statements that the proactive flow does not request an attachment resume. Replace active contract phrases `不发送后续三条` and `精确会话/三条消息及状态记录` with their two-message equivalents.

- [ ] **Step 4: Run focused RED checks**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.GreetingKnowledgeBaseTests \
  scripts.test_greet_only.BossCliTests \
  scripts.test_greet_only.CampaignRunnerTests
cd tools/boss-cli && npm run build && \
  node --test --test-name-pattern='message sequence' test/send-sequence.test.mjs
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
```

Expected: all three checks fail specifically because current production code and current skill still require three messages, the old copy, and `waiting_resume`.

### Task 2: Implement the Python two-message workflow

**Files:**

- Modify: `scripts/greet_only.py`

- [ ] **Step 1: Change knowledge-base headings and pair types**

```python
REQUIRED_MESSAGE_HEADINGS = (
    "技术与岗位介绍",
    "匹配与转投提示",
)
```

Change `load_greeting_messages`, `BossCli.send_sequence`, and `CampaignRunner.messages` annotations to `Tuple[str, str]`. Validate `len(messages) == 2`, require `messagesVerified == 2`, and update user-facing errors/help from three messages to two.

- [ ] **Step 2: Change the post-send state**

Rename `RuntimeStoreCli.mark_waiting_resume` to `mark_waiting_application_status`, pass `--stage waiting_application_status`, and invoke it only after both messages have been read back successfully.

- [ ] **Step 3: Run focused GREEN tests**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.GreetingKnowledgeBaseTests.test_loads_exact_messages_in_required_order \
  scripts.test_greet_only.GreetingKnowledgeBaseTests.test_missing_message_fails_instead_of_generating_text \
  scripts.test_greet_only.BossCliTests \
  scripts.test_greet_only.RuntimeStoreCliTests \
  scripts.test_greet_only.CampaignRunnerTests
```

Expected: all listed Python logic tests pass. The repository knowledge-base content test remains intentionally RED until the mirror is synchronized in Task 4.

### Task 3: Implement the Boss CLI two-message sequence

**Files:**

- Modify: `tools/boss-cli/src/toolset/send.ts`
- Modify: `tools/boss-cli/src/cli/cliRouter.ts`
- Modify: `tools/boss-cli/test/send-sequence.test.mjs`
- Modify: `tools/boss-cli/README.md`
- Modify: `tools/boss-cli/docs/boss-url-map.md`

- [ ] **Step 1: Change the validator to a pair**

```typescript
export function validateMessageSequence(messages: string[]): [string, string] {
  if (messages.length !== 2) {
    throw new Error(`消息序列必须恰好两条，当前为 ${messages.length} 条。`);
  }
  const normalized = messages.map((message) => message.trim());
  if (normalized.some((message) => !message)) {
    throw new Error('消息序列中的消息不能为空。');
  }
  if (new Set(normalized).size !== normalized.length) {
    throw new Error('消息序列中的消息不能重复。');
  }
  return normalized as [string, string];
}
```

- [ ] **Step 2: Update active CLI descriptions**

Describe `send-sequence` as opening one exact chat and verifying two messages. Keep the standalone `boss send --request-resume` and `boss action request-attachment-resume` commands because they serve other authorized flows; do not call them from `send-sequence`.

- [ ] **Step 3: Run CLI GREEN tests**

Run:

```bash
cd tools/boss-cli && npm test
```

Expected: TypeScript build succeeds and all configured Node tests pass.

### Task 4: Update the authoritative source skill and synchronize it

**Files:**

- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/greetings.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/auto_greet.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/candidate_conversion.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/recruiter_voice.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/risk_policy.yaml`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/school_policy.yaml`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/boss_cli.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/automation_runtime.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_salary.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_worktime.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/followups.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py`
- Generate: `skills/boss-zhaopin/`

- [ ] **Step 1: Replace the source greeting knowledge base**

Store exactly two inline-code messages under headings `技术与岗位介绍` and `匹配与转投提示`. State that neither text nor a separate action requests an attachment resume. Keep the bonuses, work-life balance, overtime and career statements approved only as part of the complete second message.

- [ ] **Step 2: Align active workflow references**

Change current proactive-flow text from three messages to two, change `waiting_resume` to `waiting_application_status` only for the proactive path, and preserve the inbound attachment-resume branch. Update the salary/worktime references from “第三条” to “第二条”. State explicitly that “在线简历” means visible recommendation-page profile data and does not authorize `boss preview`.

Define deterministic due-follow-up routing for the full workflow without changing greet-only behavior:

```text
waiting_application_status + followup_count 0 -> 同学你投的哪个部门呀？简历编号有给过别人吗？
waiting_application_status + followup_count 1 -> 同学你还没说投没投递过呢，简历编号有给过别人嘛？
waiting_application_status + followup_count 2 -> stopped/application_status_unanswered
greeted or waiting_resume -> retain the existing general follow-up branch for historical rows
```

The new fixed second message is an opportunity introduction, not a counted application-status follow-up. Also state that “现在还可以转” is not an eligibility decision: every reply still requires `application_target`, `psych_status`, `interview_status`, and `written_status`, followed by `evaluate-transfer`; only `exchange_wechat` permits the WeChat action.

Add a runtime-store regression case showing `waiting_application_status` is eligible for due follow-up and stops after its existing two-question limit. Keep the historical `waiting_resume` cases intact.

- [ ] **Step 3: Run source validation**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/yuyu/.codex/skills/boss-zhaopin
```

Expected: runtime tests, skill contract tests and quick validation all pass.

- [ ] **Step 4: Synchronize the repository mirror**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin
```

Expected: the mirror is regenerated from the installed source skill; no local runtime state is copied.

- [ ] **Step 5: Close the repository knowledge-base GREEN check**

Run:

```bash
python3 -m unittest \
  scripts.test_greet_only.GreetingKnowledgeBaseTests.test_repository_knowledge_base_loads_approved_plain_text_messages
```

Expected: the synchronized mirror yields exactly the two approved messages.

### Task 5: Update current user documentation

**Files:**

- Modify: `README.md`
- Modify: `docs/windows-setup.md`
- Modify: `docs/superpowers/specs/2026-08-22-proactive-greeting-transfer-message-design.md`

- [ ] **Step 1: Update current usage wording**

Replace current references to three post-greeting messages with two. Explicitly state that greet-only sends the two approved texts, does not request an attachment resume, and records `waiting_application_status` only after both are verified.

Document that greet-only still does not process unread chats or due follow-ups, and that `--validate-only` performs only read-only configuration validation with `messageCount: 2` and no lock, runtime init/purge, login, recommendation, preview, or send action.

- [ ] **Step 2: Leave historical artifacts unchanged**

Do not rewrite earlier dated specs or plans; they document the behavior that existed at those dates.

### Task 6: Full verification, review, commit and push

**Files:**

- Verify all files changed by Tasks 1–5.

- [ ] **Step 1: Run complete non-live verification**

Run:

```bash
python3 -m unittest scripts.test_greet_only
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_sync_repo_copy.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /Users/yuyu/.codex/skills/boss-zhaopin
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin --check
python3 scripts/greet_only.py --validate-only
(cd tools/boss-cli && npm test)
test "$(python3 -c 'import os, shutil; print(os.path.realpath(shutil.which("boss") or ""))')" = \
  "/Users/yuyu/Documents/boss招聘/tools/boss-cli/dist/cli/index.js"
git diff --check
```

Expected: every command exits zero; validate-only reports two knowledge-base messages and performs no login or live Boss action; the `boss` command resolves to the just-built repository CLI. Existing regression tests continue to prove the exact nine expectation keywords, 2027 graduation year, allowed degrees and schools, default strict major policy, one-run major exception, long-term dedupe, 150/1500 limits, current default job, Shanghai send window, risk stops, canonical/blank major persistence, and omission of the full expectation text from local state.

- [ ] **Step 2: Run independent code review**

Review correctness, regression risk, state transitions, sensitive-data handling, absence of attachment requests, missing tests and source/mirror drift. Fix all Critical and Important findings, then rerun the affected tests.

- [ ] **Step 3: Commit only task files**

```bash
git status --short
git add -- \
  README.md docs/windows-setup.md \
  docs/superpowers/specs/2026-08-22-proactive-greeting-transfer-message-design.md \
  docs/superpowers/plans/2026-08-22-two-message-proactive-greeting.md \
  scripts/greet_only.py scripts/test_greet_only.py \
  tools/boss-cli/src/toolset/send.ts tools/boss-cli/src/cli/cliRouter.ts \
  tools/boss-cli/test/send-sequence.test.mjs tools/boss-cli/README.md \
  tools/boss-cli/docs/boss-url-map.md skills/boss-zhaopin
git commit -m "feat: send two proactive greeting messages"
```

- [ ] **Step 4: Push the current branch**

```bash
git push origin codex/ai-greet-only-python
```

Expected: remote branch advances to the verified implementation commit.
