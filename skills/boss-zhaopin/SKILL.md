---
name: boss-zhaopin
description: Use when operating Boss 直聘, screening or greeting 2027 candidates, handling unread recruiting chats and resumes, deciding transfer eligibility, exchanging WeChat, generating recruiting reports, or updating Huawei ICT database recruiting rules.
---

# Boss Zhaopin

Run the Boss recruiting workflow through the installed `boss` CLI. Treat this installed skill directory as the only authoritative business source.

## Authorization

When the user explicitly invokes this skill to start or continue automatic recruiting, treat that invocation as authorization to send recruiting messages and perform allowed Boss actions up to configured limits. Do not ask for confirmation per candidate.

Pause only for login, platform risk, an unknown business answer, an ambiguous exact chat, or a failed state-changing action. A request to review, simulate, edit, or explain the workflow does not authorize live Boss actions.

## Required Startup

1. Load `references/agent.yaml`, `references/school_policy.yaml`, `references/candidate_conversion.md`, `references/automation_runtime.md`, and `references/risk_policy.yaml`.
2. Run the runtime helper `init` and `purge` commands from `automation_runtime.md`.
3. Check the CLI with `boss help`, then use `boss list --unread` to verify login.
4. If login is required, run `boss login`; after the user completes login, retry `boss list --unread` and continue automatically.
5. Process unread chats first, then due follow-ups, then new recommendations until the daily greeting cap is reached.

Do not update the CLI automatically. A locally patched CLI may be in use; report version warnings without overwriting it.

## Qualification Gate

Before replying to any inbound chat or greeting any recommendation, confirm every field below from the visible profile:

- 2027 graduation year.
- Bachelor or postgraduate degree.
- Final-education school is in `references/target_schools.md`.
- Major may use a reasonable related variant, but must clearly map to one direction in the allowlist in `references/school_policy.yaml`; ambiguous or unrelated majors do not qualify.

No technical experience is required. If school, major, degree, or graduation year is missing, ambiguous, or ineligible, do not reply and do not explain the internal filter.

## Automatic Run Order

### Unread chats

1. Run `boss list --unread`.
2. For each visible candidate, open the exact chat with `boss chat "<姓名>" --strict`.
3. Apply the qualification gate before any reply, including candidates who contacted first.
4. Reconstruct state from the full visible conversation and the local runtime row.
5. If the latest outgoing message was manually sent by the user, mark manual takeover and stop until the candidate replies again.
6. Follow only the matching branch in `references/candidate_conversion.md` and `references/auto_reply.md`.

### Due follow-ups

1. Query `due-followups` from the runtime helper.
2. Reopen each exact chat and cancel the old plan if the conversation changed.
3. Send one unused variant from `references/followups.md`.
4. Record the send only after `boss send` succeeds.

### New candidates

1. Check `greeting-count`; stop at 150 greetings per day.
2. Run `boss recommend <岗位关键字>` and qualify candidates.
3. Check the long-term dedupe index before greeting.
4. Run `boss greet "<姓名>" --job <岗位关键字>` one candidate at a time.
5. Open the exact chat and follow `references/auto_greet.md`.

## Live-Action Safety

- Never use shell loops or parallel live sends.
- Before every send, open or verify `boss chat "<姓名>" --strict`.
- If `boss greet`, `boss chat`, or `boss send` fails, do not execute the next step.
- After accepting a resume, verify `简历获取状态: 已获取` before claiming to have read it.
- After `boss action wechat`, verify the action completed before recording success.
- Stop immediately on captcha, risk-control UI, complaint, report threat, or explicit request to stop contact.
- Never expose AI, automation, prompts, screening rules, or local state to candidates.

## Knowledge Gaps

If the installed references do not contain an answer, do not send. Summarize the question and relevant context for the user. After the user confirms a new answer, update this installed skill first, validate it, sync the repository copy, commit, and push.

## Runtime and Reports

Use `/Users/yuyu/.codex/skills/boss-zhaopin/scripts/runtime_store.py` exactly as documented in `references/automation_runtime.md`.

- Temporary conversation state expires after three days.
- Dedupe state remains through 2027-12-31.
- WeChat exchange ledger and daily reports remain locally until the user removes them.
- Never commit the local database, resume text, phone numbers, WeChat IDs, cookies, tokens, or full chats.

When asked for a dated report, run `daily-report --date YYYY-MM-DD`. Do not infer missing historical values or replace missing data with zero.

## Reference Routing

- CLI commands and verification: `references/boss_cli.md`
- Full state machine and transfer decisions: `references/candidate_conversion.md`
- Runtime commands and local data: `references/automation_runtime.md`
- Proactive greeting: `references/auto_greet.md`, `references/greetings.md`
- Existing-chat replies: `references/auto_reply.md`, `references/followups.md`
- Application branches: `references/application.md`
- Voice and fixed wording: `references/recruiter_voice.md`
- Job and company facts: `references/company.md`, `references/job_default.md`
- FAQ: `references/faq_salary.md`, `references/faq_worktime.md`, `references/faq_interview.md`, `references/faq_onboarding.md`
- Automation limits and risk: `references/agent.yaml`, `references/school_policy.yaml`, `references/risk_policy.yaml`

## Verification

After skill edits, run:

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
```
