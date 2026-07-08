# 工作流：自动回复

## 目标

收到候选人回复后，检索知识库并生成专业 HR 回复。候选人出现投递相关意向时，Boss 侧不再发送投递链接、官网入口、岗位入口选择或简历编号备案细节，直接进入微信承接。

## 输入

- `boss list --unread`
- `boss chat <姓名>`
- `knowledge/`
- `prompts/candidate_intent.md`
- `prompts/hr_reply.md`
- `prompts/compliance_check.md`
- `config/risk_policy.yaml`

## 流程

1. 读取 `config/agent.yaml`。
2. 如果 `automation.enable_auto_reply` 为 `false`，停止执行。
3. 使用 `boss list --unread` 获取未读候选人。
4. 使用 `boss chat <姓名>` 打开候选人会话。
5. 识别候选人最新消息的意图。
6. 按意图检索岗位、公司和 FAQ 知识。
7. 如果 `require_knowledge_match` 为 `true` 且没有命中知识，生成需人工确认的回复，不自动发送。
8. 如果候选人消息中出现“对方想发送附件简历给您，您是否同意”，先只发送 `boss send --text "收到同学"`，再执行 `boss action agree-resume`，再用 `boss chat <姓名> --strict` 确认 `简历获取状态: 已获取`。
9. 如果候选人首次问“机会大吗”“进的机会大吗”“概率大吗”等，回复：`我看了下机会挺大的，只要你性格测评和笔试通过了，这个帮不了你，到后面面评不差的话offer概率还是很大的`
10. 如果候选人重复问机会，或追问“你没骗我吧”“真的假的”等，不要复读上一句，改用：`没骗你哈，我不会拿这个忽悠你。你这个背景确实可以往我们方向推，但测评、笔试和面试还是要自己过。我们先加个微信，后续投递和编号我在微信上跟你说。`
11. 如果候选人表示未投递、简历编号没给过别人、有转投/改投/路由意向，或笔试挂了想重新走流程，直接按 `followups.md` 执行微信承接三步。
12. 如果候选人已经投递到合适 ICT 部门，且没有表达需要我跟流程，不重复推投递，也不强行换微信。
13. 对普通问题，使用 `prompts/hr_reply.md` 生成 HR 回复。
14. 使用 `prompts/compliance_check.md` 和 `config/risk_policy.yaml` 检查回复。
15. 如果允许自动发送，执行 `boss send --text "<回复内容>"`。
16. 如果不允许自动发送，保留草稿或输出人工确认说明。

## 人工维护点

- 常见问题：`knowledge/faq/`
- 回复语气：`prompts/hr_reply.md`
- 风险策略：`config/risk_policy.yaml`
- 候选人转化流程：`workflows/candidate_conversion.md`
