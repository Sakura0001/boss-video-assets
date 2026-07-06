# 工作流：自动回复

## 目标

收到候选人回复后，检索知识库并自动生成专业 HR 回复。

如果候选人表现出意向，自动回复流程应转入 `workflows/candidate_conversion.md`：先确认候选人是否已经投递、是否投递到“云软件研发部”或合适的 ICT 部门，再索要附件简历或引导投递。只有候选人未投递、投递的不是云软件研发部、需要路由到我们部门，或明确希望我帮忙跟流程时，才发送微信交换入口，并要求候选人主动添加我的微信。

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
8. 如果候选人表现出意向，先确认投递状态：`boss send --text "同学你这边是不是还没有投递呀？"`。
9. 如果候选人未投递、投递的不是云软件研发部或合适 ICT 部门、需要路由到我们部门，或明确希望我帮忙跟流程，再按 `workflows/candidate_conversion.md` 推进索要简历、引导投递和微信承接。
10. 未完成投递状态确认前，禁止执行 `boss action wechat`。
11. 执行 `boss action wechat` 后，必须补充说明让候选人主动添加我的微信，因为账号一天不能主动添加太多同学，频繁添加容易异常。
12. 对普通问题，使用 `prompts/hr_reply.md` 生成 HR 回复。
13. 使用 `prompts/compliance_check.md` 和 `config/risk_policy.yaml` 检查回复。
14. 如果允许自动发送，执行 `boss send --text "<回复内容>"`。
15. 如果不允许自动发送，保留草稿或输出人工确认说明。

## 人工维护点

- 常见问题：`knowledge/faq/`
- 回复语气：`prompts/hr_reply.md`
- 风险策略：`config/risk_policy.yaml`
- 候选人转化流程：`workflows/candidate_conversion.md`
