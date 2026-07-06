# 工作流：主动打招呼

## 目标

根据默认岗位或指定岗位，在 Boss 推荐列表中主动触达候选人。

主动打招呼后，后续推进应进入 `workflows/candidate_conversion.md` 中定义的标准候选人转化流程。

## 输入

- `config/agent.yaml`
- `knowledge/jobs/<岗位名>.md`
- `knowledge/schools/target-schools.md`
- `config/school_policy.yaml`
- `knowledge/scripts/greetings.md`
- `boss recommend [岗位关键字]`

## 流程

1. 读取 `config/agent.yaml`。
2. 如果 `automation.enable_auto_greet` 为 `false`，停止执行。
3. 使用 `boss recommend <岗位关键字>` 获取推荐候选人。
4. 按 `max_candidates_per_run` 限制处理数量。
5. 识别候选人的最终学历学校。
6. 读取 `knowledge/schools/target-schools.md` 和 `config/school_policy.yaml`。
7. 如果学校在目标名单中，继续处理；如果学校不在名单中或无法识别，默认跳过主动打招呼。
8. 读取岗位知识和打招呼模板。
9. 生成候选人打招呼内容。
10. 如果 `automation.enable_auto_send` 为 `true`，执行 `boss greet <姓名>`。
11. `boss greet` 之后必须立刻补充一条真人化消息，说明看过候选人背景和岗位方向匹配，避免平台默认招呼语显得过于模板化。
12. 按 `workflows/candidate_conversion.md` 的顺序继续补充 2 条岗位介绍：第一条讲部门/产品和工作内容，第二条讲开发/AI 开发方向和岗位优势；不要继续连发 4-5 条。
13. 记录本次执行摘要，不保存候选人隐私。

## 人工维护点

- 岗位关键词：`config/agent.yaml`
- 岗位介绍：`knowledge/jobs/`
- 目标学校名单：`knowledge/schools/target-schools.md`
- 学校筛选策略：`config/school_policy.yaml`
- 打招呼话术：`knowledge/scripts/greetings.md`
