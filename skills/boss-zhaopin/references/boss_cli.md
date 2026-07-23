# Boss CLI Reference

The command is `boss` and must be available on `PATH`.

```text
macOS / Linux: command -v boss
Windows PowerShell: Get-Command boss
```

It is a local Boss 直聘 automation CLI using the user's Chrome/CDP login state.

## General

```bash
boss help
boss login
```

`boss login` opens Boss 直聘 for manual login.

## Chat Lists

```bash
boss list
boss list --unread
```

Use `--unread` to inspect unread candidates first.

## Candidate Chat

```bash
boss chat <姓名>
boss chat <姓名> --strict
```

Use `--strict` for exact matches before sending. The command shows candidate summary, resume status, and full visible chat messages.

## Send Message

```bash
boss send --text "同学，方便发一下简历吗？"
boss send -t "同学，方便沟通一下这个岗位吗？"
boss send --text "同学，辛苦发一下附件简历。" --request-resume
```

`--request-resume` attempts to trigger Boss's attachment-resume request after sending. Boss may reject it until both sides have sent at least one message.

## Actions In Current Chat

```bash
boss action resume
boss action not-fit
boss action remark --remark "候选人已沟通，关注 Java 后端岗位"
boss action agree-resume
boss action request-attachment-resume
boss action history
boss action wechat
```

Important actions:

- `agree-resume`: accept a candidate's attachment resume request.
- `request-attachment-resume`: request an attachment resume from the toolbar.
- `wechat`: send the Boss WeChat exchange entrance.

## Positions and JD

```bash
boss positions
boss jd <岗位名称>
```

Use `boss jd <岗位名称>` to refresh local JD cache when a candidate asks for job details.

## Recommendations and Greeting

```bash
boss recommend [岗位关键字]
boss recommend [岗位关键字] --refresh
boss preview <姓名> --job <岗位关键字>
boss greet <姓名> --job <岗位关键字>
boss deep-search [岗位关键字]
```

Notes:

- `recommend --refresh` waits one to two seconds, explicitly reloads the recommendation page, and then reads the new list.
- `recommend` enters through the Boss sidebar recommendation link with a browser mouse event so the SPA mounts `recommendFrame`; do not replace this with direct URL navigation or DOM `.click()`.
- `recommend` and `greet --job` reuse the current selected job when its label already matches the keyword instead of reopening the job dropdown.
- `preview` may consume online resume view quota.
- `greet` consumes greeting quota.
- `deep-search` depends on Boss UI routes and may fail if the platform changes.
- After `boss greet`, immediately open the chat and send the required follow-up messages from `greetings.md`.

## Reliability Practices

- Avoid chaining many live sends in one shell command.
- After `boss greet`, confirm the chat with `boss chat "<姓名>" --strict`.
- After accepting a resume, confirm `简历获取状态: 已获取`.
- If CDP disconnects or a send fails, reopen the chat before retrying.
