# 工作流：主动打招呼

## 目标

根据默认岗位或指定岗位，在 Boss 推荐列表中主动触达候选人。

## 输入

- `config/agent.yaml`
- `knowledge/jobs/<岗位名>.md`
- `knowledge/scripts/greetings.md`
- `boss recommend [岗位关键字]`

## 流程

1. 读取 `config/agent.yaml`。
2. 如果 `automation.enable_auto_greet` 为 `false`，停止执行。
3. 使用 `boss recommend <岗位关键字>` 获取推荐候选人。
4. 按 `max_candidates_per_run` 限制处理数量。
5. 读取岗位知识和打招呼模板。
6. 生成候选人打招呼内容。
7. 如果 `automation.enable_auto_send` 为 `true`，执行 `boss greet <姓名>`。
8. 记录本次执行摘要，不保存候选人隐私。

## 人工维护点

- 岗位关键词：`config/agent.yaml`
- 岗位介绍：`knowledge/jobs/`
- 打招呼话术：`knowledge/scripts/greetings.md`

