# Boss 直聘自动招聘 Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the installed `boss-zhaopin` skill into an on-demand end-to-end Boss recruiting workflow with deterministic local state, deduplication, WeChat ledger, and daily reports.

**Architecture:** Keep natural-language screening and live Boss CLI orchestration in the skill. Add a standard-library Python SQLite helper for timing, counters, state recovery, transfer decisions, deduplication, WeChat completion, and reports. Treat `/Users/yuyu/.codex/skills/boss-zhaopin` as authoritative and sync it deterministically into the repository.

**Tech Stack:** Markdown/YAML skill resources, Python 3.9 standard library (`argparse`, `sqlite3`, `zoneinfo`, `unittest`), existing `boss` CLI, Git.

---

### Task 1: Capture failing skill behavior

**Files:**
- Read: `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md`
- Read: `/Users/yuyu/.codex/skills/boss-zhaopin/references/*.md`

- [x] **Step 1: Run the 2026 inbound candidate scenario against the old skill**

Expected failure: the old skill replies instead of silently skipping a non-2027 candidate.

- [x] **Step 2: Run the already-interviewed transfer scenario against the old skill**

Expected failure: the old skill initiates WeChat instead of stopping a candidate who has already attended an interview.

- [x] **Step 3: Run the dated daily-report scenario against the old skill**

Expected failure: the old skill has no deterministic local data source and cannot assemble the requested report.

### Task 2: Write failing tests for deterministic runtime state

**Files:**
- Create: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py`
- Create later: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/runtime_store.py`

- [x] **Step 1: Write tests for transfer decisions**

Cover these exact inputs and results:

```python
self.assertEqual(evaluate_transfer("cloud_software", "passed", "not_started", "passed").action, "stop")
self.assertEqual(evaluate_transfer("other", "failed", "not_started", "not_taken").reason, "psychological_assessment_failed")
self.assertEqual(evaluate_transfer("other", "passed", "started", "passed").reason, "interview_already_started")
self.assertEqual(evaluate_transfer("other", "passed", "not_started", "failed").action, "exchange_wechat")
self.assertEqual(evaluate_transfer("none", "not_taken", "not_started", "not_taken").action, "exchange_wechat")
self.assertEqual(evaluate_transfer("other", "passed", "unknown", "passed").action, "ask_process_stage")
```

- [x] **Step 2: Write tests for follow-up timing and manual takeover**

Create candidates at fixed Asia/Shanghai timestamps and assert that `due_followups()`:

- excludes candidates contacted less than six hours ago;
- includes candidates at six hours;
- excludes candidates with eight follow-ups;
- excludes `manual_takeover` and terminal candidates.

- [x] **Step 3: Write tests for retention and deduplication**

Assert that `purge_runtime()` removes candidate runtime rows older than three days while preserving the dedupe table, events, and WeChat ledger. Assert that a contacted candidate remains deduped until `2027-12-31`.

- [x] **Step 4: Write tests for WeChat completion and reports**

Assert that `complete_wechat()` atomically updates candidate state, dedupe status, ledger, and event. Assert that `daily_report("2026-07-10")` includes the candidate name and all required funnel counters.

- [x] **Step 5: Run tests and verify RED**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
```

Expected: fail because `runtime_store` does not exist.

### Task 3: Implement deterministic runtime state

**Files:**
- Create: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/runtime_store.py`
- Test: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py`

- [x] **Step 1: Implement SQLite initialization and permissions**

Use `/Users/yuyu/.codex/state/boss-zhaopin/state.sqlite3` by default. Create the parent directory with mode `0700` and database with mode `0600`. Create focused tables:

```sql
candidates(candidate_id, display_name, stage, school, major, degree, grad_year,
           application_status, original_department, last_contact_at,
           followup_count, followup_variant, manual_takeover, updated_at, expires_at)
dedupe(candidate_id, first_contact_at, final_status, expires_at)
events(id, event_type, occurred_at, candidate_id, payload_json)
wechat_ledger(candidate_id, display_name, exchanged_at, school, major, degree,
              application_status, original_department, note)
```

- [x] **Step 2: Implement the transfer decision function**

Define:

```python
@dataclass(frozen=True)
class TransferDecision:
    action: str
    reason: str

def evaluate_transfer(application_target, psych_status, interview_status, written_status):
    ...
```

Apply the priority from the approved design: cloud software history, failed psychological assessment, and any started interview stop; missing interview stage asks; otherwise unsubmitted/other/unknown departments can exchange, with written-test failure marked as eligible for immediate retest.

- [x] **Step 3: Implement candidate state and follow-up queries**

Implement `upsert_candidate`, `get_candidate`, `due_followups`, `mark_followup_sent`, `mark_manual_takeover`, and `purge_runtime`. Refresh temporary expiry to three days after each update. Cap follow-ups at eight and require six elapsed hours.

- [x] **Step 4: Implement events, dedupe, WeChat ledger, and reporting**

Implement `record_event`, `mark_deduped`, `is_deduped`, `complete_wechat`, `greeting_count`, and `daily_report`. Store no resume text, phone number, WeChat ID, cookies, tokens, or full chat transcript.

- [x] **Step 5: Add an argparse CLI**

Expose these subcommands:

```text
init
purge
candidate-upsert
candidate-get
due-followups
followup-sent
manual-takeover
dedupe-check
dedupe-add
record-event
evaluate-transfer
wechat-complete
greeting-count
daily-report
```

All machine-readable commands output JSON except `daily-report`, which outputs readable Markdown.

- [x] **Step 6: Run tests and verify GREEN**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
```

Expected: all tests pass.

### Task 4: Write failing skill contract tests

**Files:**
- Create: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py`
- Modify later: `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md`
- Modify later: `/Users/yuyu/.codex/skills/boss-zhaopin/references/*.md`

- [x] **Step 1: Assert required exact copy and policies**

Test for the approved opening, resume response, status question, chance answer, WeChat sequence, 2027-only filter, final-school filter, STEM-only filter, daily cap 150, six-hour/eight-follow-up limits, and the state directory.

- [x] **Step 2: Assert obsolete rules are absent**

Reject `请填写默认岗位关键词`, `数据库没有受到当下AI的太多冲击`, the old two-message direction conflict, and the old rule that any ICT application can still enter WeChat tracking.

- [x] **Step 3: Run tests and verify RED**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
```

Expected: failures against the current skill.

### Task 5: Rewrite the installed skill as the authoritative workflow

**Files:**
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/SKILL.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/agents/openai.yaml`
- Create: `/Users/yuyu/.codex/skills/boss-zhaopin/references/automation_runtime.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/agent.yaml`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/application.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/auto_greet.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/auto_reply.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/candidate_conversion.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/company.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/daily_run.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_interview.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_salary.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/faq_worktime.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/followups.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/greetings.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/job_default.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/recruiter_voice.md`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/risk_policy.yaml`
- Modify: `/Users/yuyu/.codex/skills/boss-zhaopin/references/school_policy.yaml`

- [x] **Step 1: Make `SKILL.md` a concise executable entrypoint**

Start the description with `Use when`. Treat explicit auto-recruit invocation as authorization for live sends up to policy limits. Require login recovery, unread-first processing, eligibility before every reply, state initialization, exact-chat verification, one-at-a-time live actions, and final reporting.

- [x] **Step 2: Consolidate screening and application state rules**

Put the full decision table in `candidate_conversion.md` and keep other references linking to it instead of copying divergent logic. Encode 2027, bachelor/master, final-school allowlist, STEM, no experience requirement, silent skip on unknown, transfer before interview only, psychological-assessment failure stop, and cloud software history stop.

- [x] **Step 3: Update approved candidate-facing copy**

Replace the opening, resume handling, status question, opportunity response, salary, cities, worktime, overseas collaboration, and WeChat completion text exactly as approved. Add eight distinct follow-up variants that do not add facts.

- [x] **Step 4: Align risk and runtime policies**

Remove the contradiction that automatically blocks the approved opportunity wording. Keep knowledge gaps, precise unapproved compensation, complaints, legal risk, platform risk, failed exact chat, and failed state verification as blocking conditions.

- [x] **Step 5: Document runtime helper commands**

In `automation_runtime.md`, specify the database path, command examples, three-day temporary retention, 2027 dedupe, long-term WeChat ledger, daily report fields, and local-only privacy constraints.

- [x] **Step 6: Regenerate `agents/openai.yaml`**

Run the skill-creator generator with a short description and a default prompt that explicitly includes `$boss-zhaopin`.

- [x] **Step 7: Run contract tests and validate GREEN**

Run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
```

Expected: all checks pass.

### Task 6: Add deterministic repository synchronization

**Files:**
- Create: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py`
- Test: `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py`
- Modify: `/Users/yuyu/.codex/worktrees/c58b/boss招聘/AGENTS.md`
- Modify: `/Users/yuyu/.codex/worktrees/c58b/boss招聘/boss-recruiting-agent/README.md`
- Replace mirror contents: `/Users/yuyu/.codex/worktrees/c58b/boss招聘/skills/boss-zhaopin/`

- [x] **Step 1: Write a failing sync test**

Create temporary source/destination trees, assert sync copies new files, removes stale files, ignores `__pycache__`, `.pyc`, `.DS_Store`, and never includes `/Users/yuyu/.codex/state`.

- [x] **Step 2: Implement sync and check modes**

Expose:

```bash
python3 scripts/sync_repo_copy.py --destination /path/to/repo/skills/boss-zhaopin
python3 scripts/sync_repo_copy.py --destination /path/to/repo/skills/boss-zhaopin --check
```

- [x] **Step 3: Remove duplicated runtime instructions from repository guidance**

Keep CLI installation notes, but make `AGENTS.md` and `boss-recruiting-agent/README.md` state that the installed skill is authoritative and the repository skill folder is its mirror. Do not leave conflicting conversation rules in `AGENTS.md`.

- [x] **Step 4: Sync and verify**

Run the sync command, then `--check`. Expected: no differences.

### Task 7: Forward-test and deploy

**Files:**
- Verify: `/Users/yuyu/.codex/skills/boss-zhaopin/`
- Verify: `/Users/yuyu/.codex/worktrees/c58b/boss招聘/skills/boss-zhaopin/`

- [x] **Step 1: Re-run the three baseline scenarios with the updated skill**

Expected:

- 2026 inbound candidate receives no reply.
- Candidate who attended a technical interview is stopped and does not receive WeChat.
- Dated daily report reads the local database and never invents missing data.

- [x] **Step 2: Run full local verification**

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py --destination /Users/yuyu/.codex/worktrees/c58b/boss招聘/skills/boss-zhaopin --check
git diff --check
```

- [x] **Step 3: Scan for secrets and candidate data**

Search the staged skill and guidance changes for tokens, cookies, phone numbers, WeChat IDs, and candidate resume content. Expected: no private production data.

- [x] **Step 4: Commit only relevant files and push**

Stage the plan, `AGENTS.md`, `boss-recruiting-agent/README.md`, and `skills/boss-zhaopin/`. Do not stage unrelated `tools/boss-cli` changes. Commit and push `HEAD:main`.
