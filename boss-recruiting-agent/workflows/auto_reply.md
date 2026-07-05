# 工作流：自动回复

## 目标

收到候选人回复后，检索知识库并自动生成专业 HR 回复。

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
8. 使用 `prompts/hr_reply.md` 生成 HR 回复。
9. 使用 `prompts/compliance_check.md` 和 `config/risk_policy.yaml` 检查回复。
10. 如果允许自动发送，执行 `boss send --text "<回复内容>"`。
11. 如果不允许自动发送，保留草稿或输出人工确认说明。

## 人工维护点

- 常见问题：`knowledge/faq/`
- 回复语气：`prompts/hr_reply.md`
- 风险策略：`config/risk_policy.yaml`

