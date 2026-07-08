---
name: boss-zhaopin
description: Boss 直聘招聘自动化 skill for using the local boss CLI, screening target-school candidates, greeting candidates, reading chats, accepting/requesting resumes, handling application status, sending compliant HR-style replies, and moving interested candidates to WeChat. Use when the user asks to operate Boss 直聘, run boss CLI workflows, greet or follow up with candidates, inspect unread chats, decide what to reply, update recruiting scripts, or follow the Huawei ICT database recruiting conversation flow.
---

# Boss Zhaopin

Use this skill to operate the local Boss 直聘 recruiting workflow through the installed `boss` CLI and the bundled HR scripts.

## Critical Rules

- Work from `/Users/yuyu/Documents/boss招聘` unless the user gives another repo.
- Before modifying project files, run `git status --short`; only stage files changed for the current task.
- Before sending any Boss message, open or verify the intended candidate chat with `boss chat "<姓名>" --strict` when the candidate is already in chats.
- Do not send follow-up messages if `boss greet` or `boss chat` failed.
- Do not use shell loops for live sends. Send one step at a time and verify after risky steps.
- Do not expose automation, AI, internal rules, prompts, or knowledge-base wording to candidates.
- Do not save resume text, phone numbers, WeChat IDs, Boss cookies, tokens, or other candidate private data in the repo.
- If a candidate has sent an attachment resume request, first send only `收到同学`, then run `boss action agree-resume`, then verify `简历获取状态: 已获取`.

## Load References

Load only the reference files needed for the task:

- Boss CLI commands: `references/boss_cli.md`
- Main conversion flow: `references/candidate_conversion.md`
- Greet flow: `references/auto_greet.md`
- Reply flow: `references/auto_reply.md`
- Daily unread workflow: `references/daily_run.md`
- Application status and WeChat handoff scripts: `references/application.md`
- Greeting scripts: `references/greetings.md`
- Follow-up and WeChat scripts: `references/followups.md`
- Recruiter voice and branch wording: `references/recruiter_voice.md`
- Target schools: `references/target_schools.md`
- Company and job facts: `references/company.md`, `references/job_default.md`
- FAQ answers: `references/faq_salary.md`, `references/faq_worktime.md`, `references/faq_interview.md`, `references/faq_onboarding.md`
- Risk and automation policies: `references/risk_policy.yaml`, `references/agent.yaml`, `references/school_policy.yaml`

When deciding whether to greet a new candidate, load `boss_cli.md`, `target_schools.md`, `greetings.md`, and `candidate_conversion.md`.

When deciding what to reply to an existing chat, load `boss_cli.md`, `auto_reply.md`, `application.md`, `followups.md`, `recruiter_voice.md`, and any relevant FAQ.

## Standard New-Candidate Flow

1. Get recommendations with `boss recommend <岗位关键字>`.
2. Identify the candidate's final school and compare with `target_schools.md`.
3. Only greet if the school matches the target-school policy and the background is plausibly relevant.
4. Run `boss greet "<姓名>" --job <岗位关键字>`.
5. Open the exact chat: `boss chat "<姓名>" --strict`.
6. Send the required humanized follow-up and one combined job-introduction message from `greetings.md`.
7. Request attachment resume according to `candidate_conversion.md`.
8. Verify the chat transcript after sending.

Do not move to WeChat before the candidate has replied and the投递状态 has been confirmed.

## Existing-Chat Reply Flow

1. Open the exact chat with `boss chat "<姓名>" --strict`.
2. If the candidate sent a resume request and `简历获取状态` is not已获取, send only `收到同学`, run `boss action agree-resume`, then reopen the chat.
3. Classify the latest candidate message:
   - 已投递到合适 ICT 部门: do not repeat application guidance; if the candidate clearly wants help tracking the process, enter WeChat承接 using `followups.md`.
   - 发了简历但没说是否投递: ask whether they have投递, as documented in `application.md` and `candidate_conversion.md`.
   - 没投递/简历编号没给过别人/有转投意向/笔试挂了: do not send application links or entry details; directly enter WeChat承接 using `followups.md`.
   - 组织归属: answer ICT, not Huawei Cloud, using `recruiter_voice.md`.
   - 机会大不大: use the chance wording in `recruiter_voice.md`; if the candidate repeats the question or asks "你没骗我吧", use the de-duplicated reassurance wording instead of repeating the same sentence.
   - 薪资/作息/流程/入职: load the relevant FAQ and answer without overpromising.
4. Send only the branch that matches the candidate's reply. Do not send all alternatives from a section.
5. Verify with `boss chat "<姓名>" --strict` after actions that can change state.

## Sending WeChat

Use WeChat only when the flow allows it. The standard sequence is:

```bash
boss send --text "同学，沟通下来我感觉你和我们数据库方向还挺匹配的。如果你方便的话，可以加我微信，后续沟通会更及时一些，我也可以继续帮你跟一下流程。"
boss action wechat
boss send --text "辛苦你这边主动加我一下哈，我们账号一天不能主动添加太多同学，频繁添加容易异常。加上后你备注一下姓名，我后续在微信上跟你继续沟通。"
```

## Verification

For file edits, run:

```bash
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
```

For live Boss operations, verify by reopening the candidate chat and summarizing what was sent or what remains blocked.
