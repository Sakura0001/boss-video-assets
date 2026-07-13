# Boss Global Pacing and Circuit Breaker Design

## Objective

Add one mode-independent pacing and circuit-breaker layer for every automated Boss page operation. The layer reduces sustained request density and stops automation when the platform reports risk. It does not claim to prevent platform restrictions.

The worker remains long-running: unread candidates have priority, and new greetings continue whenever the unread queue is empty until the existing daily greeting cap of 150 is reached. After the cap, the worker continues monitoring and replying to unread candidates.

## Confirmed Timing Profiles

All automated waits use a newly sampled inclusive random value. No workflow uses a fixed sleep.

| Profile | Range | Applies to |
| --- | --- | --- |
| `initial_outreach` | 4-6 seconds | The first-contact sequence from `greet` through the initial messages and attachment-resume request |
| `normal` | 6-10 seconds | Unread handling, replies, resume acceptance, application-status questions, WeChat exchange, list/recommend reads, and other Boss page operations |
| `idle_unread_check` | 30-60 seconds | Waiting for unread work when there is no immediately actionable candidate |

Business deadlines are separate from pacing. The six-hour follow-up rule and daily greeting cap keep their existing meaning.

## Scope and Ownership

### CLI

The CLI owns enforcement that must not be bypassed by separate one-shot processes:

- global serialization;
- persisted completion-to-next-start pacing;
- timing-profile validation;
- persisted risk circuit breaker;
- risk-page classification;
- diagnostic status and explicit manual reset.

### Recruiting Skill

The installed `boss-zhaopin` skill remains the only business source for qualification, wording, transfer rules, unread priority, and the daily cap. The skill selects `initial_outreach` only while executing the approved first-contact sequence; every other page operation uses the safer `normal` default.

The installed skill is not changed during branch development. After offline verification and user acceptance, it is updated first and then synced into the repository mirror according to `AGENTS.md`.

## Persistent Global Pacing

The CLI stores pacing metadata under the existing private Boss application-data directory. The file is user-only and contains no candidate or message data.

Required fields:

```json
{
  "schemaVersion": 1,
  "lastCompletedAt": "2026-07-13T12:00:00.000Z",
  "nextAllowedAt": "2026-07-13T12:00:08.123Z",
  "lastProfile": "normal",
  "lastCommand": "chat"
}
```

For a page operation:

1. Acquire the existing Boss session lock.
2. Check the persisted circuit breaker.
3. Read pacing state.
4. Wait until `nextAllowedAt` when necessary.
5. Execute exactly one serialized page operation.
6. In `finally`, sample the next delay for the current profile and atomically persist completion state.
7. Inspect the resulting page and error for risk signals before releasing the lock.

The delay is measured from the prior operation's completion to the next operation's start. A failed operation also schedules the next delay, so an immediate retry cannot bypass pacing. Browser mode changes and process restarts do not clear pacing state.

Random values use the existing cryptographic timing utility. Tests inject a fake clock, sleeper, and random source; production does not expose an environment variable that disables pacing.

## Operation Classification

The paced page commands include:

- `login`
- `list`
- `chat`
- `send`
- `action`
- `positions`
- `jd`
- `recommend`
- `preview`
- `greet`
- `deep-search`

Local-only commands are excluded:

- `help` and `version`
- `browser status/start/stop/restart`
- local runtime-store and reporting commands
- circuit-breaker status

The default profile is always `normal`. Initial outreach must be selected explicitly by the recruiting orchestrator. Unknown profiles fail before browser access.

Compound commands must pace separate business actions. In particular, `send --request-resume` performs one paced send and then a second paced attachment-resume request. DOM polling, rendering waits, and local state reads are not treated as independent business operations.

## Continuous Scheduler

The recruiting loop is strictly serial:

```text
startup and user-confirmed login
  -> check circuit breaker
  -> inspect unread work
  -> while unread exists: process the next eligible unread candidate
  -> when unread is empty: process one due follow-up, if any
  -> when unread and due follow-ups are empty and greetings < 150: process one new candidate
  -> inspect unread work again
  -> after 150 greetings: monitor unread and process due follow-ups, but do not greet
  -> continue until manual stop or circuit trip
```

Unread priority is evaluated at candidate boundaries. The worker does not interrupt an in-progress state-changing action, but it checks unread work before selecting another new candidate.

When no work is available, the worker samples `idle_unread_check` and inspects already-loaded page state without forcing a refresh. If the page is disconnected or invalid, the next real page read uses the `normal` profile. The idle loop never performs parallel polling.

Headful and headless modes use the same queue, state file, timing profiles, and scheduler. In headful mode, detected manual outgoing activity pauses automation for that candidate under the existing manual-takeover rule.

## Persisted Circuit Breaker

The circuit trips on any confirmed platform-risk condition, including:

- captcha or human-verification UI;
- `code=36`;
- HTTP 403 or `code=32`;
- known risk-control or abnormal-operation pages;
- a state-changing action whose result cannot be verified because the page moved to a risk state.

Trip state contains only timestamp, reason code, mode, and command. It contains no candidate data.

Once tripped:

- the current operation reports the risk condition;
- the continuous scheduler stops;
- all later business commands fail before browser access;
- switching mode, restarting Chrome, restarting the CLI, or crossing midnight does not clear the trip;
- browser lifecycle commands and risk status remain available for recovery;
- recovery is performed manually in the visible browser; automated `login` remains blocked while the circuit is tripped;
- reset requires an explicit user-confirmed command after the account is restored.

Ordinary selector or timeout failures do not silently retry. They stop the current candidate path and surface the error. Repeated global failures are not converted into alternate navigation paths.

## Observability and Privacy

Each paced operation may log:

- command category;
- selected profile;
- sampled wait duration;
- start and completion timestamps;
- success, ordinary failure, or circuit trip.

Logs and state must not contain names, message text, resumes, contact details, cookies, or tokens. Runtime state remains local and is never committed.

## Verification

Offline automated tests cover:

- inclusive random bounds for all three profiles;
- no fixed-delay path;
- completion-to-next-start waiting;
- persisted timing across separate process simulations;
- shared pacing across headful and headless modes;
- global serialization;
- failures still scheduling the next delay;
- unknown profiles failing before browser access;
- lifecycle commands remaining local and unpaced;
- compound send/resume actions receiving two pacing gates;
- risk classification for captcha, `code=36`, HTTP 403, and `code=32`;
- trip persistence across process and mode restarts;
- business commands blocked before browser access while tripped;
- explicit reset and status behavior;
- scheduler priority: unread, due conversation work, then new greeting;
- greeting cap switching the worker to unread-only operation;
- idle unread checks sampling 30-60 seconds without parallel polling.

Because the account is currently restricted, implementation verification must not access Boss. Live validation is deferred until the user confirms that the account is restored. The first live validation is read-only and headful; state-changing tests require separate user authorization and stop on the first risk signal.

## Rollout

1. Implement and verify the CLI and repository flow documents on `feature/boss-background-browser`.
2. Do not install the branch globally or modify the installed skill during offline development.
3. After account recovery, perform the explicitly authorized read-only headful validation.
4. Let the user review the branch behavior.
5. Only after acceptance, merge the branch and update the installed `boss-zhaopin` skill.
6. Validate the installed skill, sync its repository mirror, commit, and push.
