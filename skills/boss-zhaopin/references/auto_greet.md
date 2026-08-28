# 自动打招呼

## 单次确定性执行器入口

仅本次主动打招呼需要放宽专业门槛时，从仓库根目录执行：

```bash
python3 scripts/greet_only.py --skip-major-filter --target 150 --max-scans 1500
```

Windows PowerShell 使用：

```powershell
py -3 .\scripts\greet_only.py --skip-major-filter --target 150 --max-scans 1500
```

`--skip-major-filter` 属于 `scripts/greet_only.py` 的参数，不得传给 `boss greet`。未提供 --job 时使用 Boss 推荐页当前默认岗位，不把 `agent.yaml` 的 `default_job_keyword` 当作所选岗位，也不强制覆盖岗位。不带该参数时，执行器继续使用默认专业门槛。该命令是完整流程：执行锁内、推荐前自动运行 runtime `init`、runtime `purge --as-of <Shanghai ISO>`、`boss help` 和 `boss list --unread`。`boss list --unread` 仅用于验证登录，不处理或回复未读聊天，也不处理到期跟进。如需登录，runner 自动打开并轮询登录；登录后获取首个推荐批次。使用 runner 时不得手工运行这些预检命令。runner 内部完成计数、推荐、资格筛选、去重、打招呼、精确会话/三条消息及状态记录。三条固定纯文本均读回验证成功后，状态设为 `waiting_application_status`；主动招呼流程不执行附件简历请求，不使用 `--request-resume`，不执行 `request-attachment-resume`。新文案中的“在线简历”仅指推荐页当前可见的候选人资料，不调用 `boss preview`。第三条中的转投和加微信内容仅为固定纯文本，不直接执行微信动作，后续仍按转投资格规则判断。该开关及其配置不持久化；招呼、去重和候选人阶段仍按运行时规则记录。启动 runner 后不得执行手工流程分支或另行调用 `boss greet`。

## Runner 内部流程与手工参考

下列步骤说明 runner 的内部顺序，并仅供未启动 runner 的手工流程参考；启动 runner 后不得按下列步骤另行执行命令。

1. 读取 `agent.yaml`、`school_policy.yaml`、`target_schools.md`、`greetings.md` 和 `automation_runtime.md`。
2. 查询当日 `greeting-count`，达到 150 时停止。
3. 使用 `boss recommend <岗位关键字>` 获取候选人。
4. 按页面顺序每批检查 10 名不同候选人；重复卡片、已检查过的稳定候选人标识不计入这 10 名。
5. 先移除求职期望中的全部空白并转为小写，再对固定硬编码列表做子串匹配；固定列表仅为九项：算法、通信、硬件、前端、unity、电气、数据、产品、分析。命中时内部原因 `expectation_blocked`，不回复、不打招呼、不发送后续三条消息，完整求职期望不得写入本地状态或 Git。为空或未命中时，继续毕业年份、学历、学校、专业和去重门槛。其余资格、专业例外与本地状态规则以 `school_policy.yaml` 为准；随后从页面右侧结构化教育经历读取每一条学校、专业和学历。
6. 一批 10 名候选人中没有任何人符合条件时，随机等待 1 至 2 秒，再执行 `boss recommend <岗位关键字> --refresh` 显式刷新推荐页，并从新列表继续按批检查，直到找到符合条件的候选人。
7. 刷新查找仍受 `max_candidates_per_run: 1500`、当日 150 次打招呼上限及风险策略约束；达到检查上限、出现验证码或风控、推荐读取失败时停止，不得无限循环或快速重试。
8. 检查长期去重；已联系过的不再打招呼。如果符合条件的候选人已在长期去重索引中，继续检查当前批次中的下一人，而不是向其重复打招呼。
9. 未启动 runner 的手工流程逐个执行 `boss greet "<姓名>" --job <岗位关键字>`。runner 内部在前一步 `boss recommend <岗位关键字>` 已确认岗位后，使用稳定候选人 ID 执行 `boss greet "<姓名>" --id <候选人ID> --json`，不得再次传入 `--job` 重复切换岗位；必须校验返回岗位、姓名和候选人 ID。不要使用 shell 循环。
10. 成功后使用 `runtime_store.py greeting-complete` 原子记录 `greeted` 事件、
    候选人阶段和长期去重索引；runner 同时写入 `manual_takeover = 1`，在三条消息
    完成前挂起自动到期跟进。
11. 只打开一次精确会话；每次发送前在当前页面重新验证候选人姓名和沟通岗位，
    依次发送并读回验证 `greetings.md` 的技术与岗位介绍、匹配与转投提示和投递方式与流程提示。
    同一候选人的三条消息不得重复离开并重新进入会话；主动路径不请求附件简历。
12. 三条固定纯文本均读回验证成功后，状态设为 `waiting_application_status`，记录最后发送时间，
    并写入 `manual_takeover = 0` 恢复该阶段的正常到期处理。任一消息发送或验证失败时保留
    `greeted`、长期去重和 `manual_takeover = 1`，不得提前进入该阶段，也不得进入历史通用跟进；
    普通重跑不会重复触达，必须人工打开精确会话核对并恢复。

`boss greet` 仅报告“打招呼按钮仍可用，无法确认操作成功”时，不记录成功、不发送三条消息，跳过该候选人并继续下一位。其他任一步失败时停止该候选人后续动作并停止整次运行。平台出现验证码或风控时停止整次运行。
