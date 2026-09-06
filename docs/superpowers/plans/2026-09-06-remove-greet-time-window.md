# Remove Greet Time Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `scripts/greet_only.py` to run at any Shanghai time while preserving all other recruiting limits and risk stops.

**Architecture:** Keep `_now()` as the single timezone-normalization helper. Remove only the hour gate and replace its call sites with `_now()`; update current user documentation to match.

**Tech Stack:** Python 3, `unittest`, Markdown.

---

### Task 1: Remove the runner time gate

**Files:**
- Modify: `scripts/test_greet_only.py`
- Modify: `scripts/greet_only.py`

- [ ] **Step 1: Add the failing regression test**

Add `test_runs_outside_previous_send_window` to `CampaignRunnerTests`; set `self.now` to `2026-09-06 22:00 +08:00`, run one eligible candidate, and assert `final_count == 1` plus one verified message sequence.

- [ ] **Step 2: Verify the regression test fails**

Run: `python3 -m unittest scripts.test_greet_only.CampaignRunnerTests.test_runs_outside_previous_send_window`

Expected: failure with `当前不在 Asia/Shanghai 09:00–21:00 招聘时段`.

- [ ] **Step 3: Implement the minimal change**

Delete `_assert_send_window()`. Remove its call from `_send_messages()`, use `_now()` for the run date, and use `_now().isoformat()` for each greeting event time.

- [ ] **Step 4: Run the focused test file**

Run: `python3 -m unittest scripts.test_greet_only`

Expected: all tests pass.

### Task 2: Align current documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/windows-setup.md`

- [ ] **Step 1: Remove current time-window statements**

Remove the 09:00–21:00 stop condition from the active runner documentation. Historical design and plan files remain unchanged as records of their original decisions.

- [ ] **Step 2: Check the diff**

Run: `git diff --check && rg -n "09:00|21:00|招聘时段" scripts/greet_only.py README.md docs/windows-setup.md`

Expected: `git diff --check` succeeds and `rg` returns no matches in active files.

### Task 3: Commit and run

- [ ] **Step 1: Commit only task files**

Stage the runner, focused test, current docs, and this plan; commit with `fix: remove greet time window`.

- [ ] **Step 2: Push the branch**

Run `git push` and report any failure.

- [ ] **Step 3: Start the live runner**

Run with the current account state directory: `python3 scripts/greet_only.py --target 150 --max-scans 1500` under `caffeinate`; stop on existing platform-risk conditions.
