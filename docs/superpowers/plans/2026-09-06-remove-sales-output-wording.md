# Greeting Wording Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the exact sentence `部门没有输出到销售的情况，外界风评很好，` from the third approved proactive greeting without changing any other recruiting behavior.

**Architecture:** Update the installed `boss-zhaopin` skill as the authoritative source, prove the contract change with a red/green test, then use the existing synchronization script to regenerate the repository mirror. No runtime code or filtering rules change.

**Tech Stack:** Markdown skill references, Python `unittest`, existing skill synchronization and validation scripts, Git.

---

### Task 1: Update the approved greeting contract

**Files:**
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/greetings.md`

- [ ] **Step 1: Write the failing contract expectation**

Change the expected third greeting so its opening is exactly:

```text
在华为，投递一个好的部门远好于投递一个非常热门的业务，请同学慎重考虑投递的部门，
```

- [ ] **Step 2: Run the contract test to verify RED**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
```

Expected: FAIL because `references/greetings.md` still contains the removed sentence.

- [ ] **Step 3: Apply the minimal source edit**

In the third fixed greeting, replace:

```text
在华为，投递一个好的部门远好于投递一个非常热门的业务，部门没有输出到销售的情况，外界风评很好，请同学慎重考虑投递的部门，
```

with:

```text
在华为，投递一个好的部门远好于投递一个非常热门的业务，请同学慎重考虑投递的部门，
```

- [ ] **Step 4: Run the contract test to verify GREEN**

Run the same test. Expected: all contract tests pass.

### Task 2: Validate, synchronize, and publish

**Files:**
- Modify through sync: `skills/boss-zhaopin/references/greetings.md`
- Modify through sync: `skills/boss-zhaopin/scripts/test_skill_contract.py`

- [ ] **Step 1: Run required source-skill validation**

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
```

Expected: all tests pass and the validator reports the skill is valid.

- [ ] **Step 2: Synchronize the repository mirror**

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py --destination /Users/yuyu/Documents/boss招聘/skills/boss-zhaopin
```

Expected: the mirror is updated from the installed source skill.

- [ ] **Step 3: Verify exact removal and no unrelated wording changes**

Search both skill trees for the removed text; expected: no matches. Inspect `git diff` and confirm only the fixed greeting and matching contract expectation changed, apart from this plan.

- [ ] **Step 4: Commit and push**

```bash
git add docs/superpowers/plans/2026-09-06-remove-sales-output-wording.md skills/boss-zhaopin/references/greetings.md skills/boss-zhaopin/scripts/test_skill_contract.py
git commit -m "fix: remove sales output wording"
git push
```

Expected: commit succeeds and the current branch is pushed.
