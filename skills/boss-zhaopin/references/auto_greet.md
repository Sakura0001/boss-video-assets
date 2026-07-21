# 自动打招呼

1. 读取 `agent.yaml`、`school_policy.yaml`、`target_schools.md`、`greetings.md` 和 `automation_runtime.md`。
2. 查询当日 `greeting-count`，达到 150 时停止。
3. 使用 `boss recommend <岗位关键字>` 获取候选人。
4. 只处理资料明确的 2027 届、本科或研究生、目标学校、且专业能明确对应 `school_policy.yaml` 的 `allowed_majors` 方向（允许合理相关变体）的候选人；不要求技术经历。
5. 检查长期去重；已联系过的不再打招呼。
6. 逐个执行 `boss greet "<姓名>" --job <岗位关键字>`，不要使用 shell 循环。
7. 成功后记录 `greeted` 事件并写入去重索引。
8. 打开精确会话，依次发送 `greetings.md` 的真人化说明、合并介绍和附件简历请求。
9. 状态设为 `waiting_resume`，记录最后发送时间。

任一步失败时停止该候选人后续动作。平台出现验证码或风控时停止整次运行。
