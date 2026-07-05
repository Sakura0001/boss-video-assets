# 内容填写指南

这个指南用于逐个补齐全自动招聘工具需要的业务内容。

## 推荐填写顺序

1. `knowledge/company.md`
2. `knowledge/jobs/default.md`
3. `knowledge/faq/salary.md`
4. `knowledge/faq/worktime.md`
5. `knowledge/faq/interview.md`
6. `knowledge/faq/onboarding.md`
7. `knowledge/scripts/greetings.md`
8. `knowledge/scripts/followups.md`
9. `config/agent.yaml`
10. `config/risk_policy.yaml`

## 每个文件怎么填

### company.md

填写公司名称、行业、规模、地点、主营业务、团队情况、公司亮点和不能承诺的信息。

### jobs/default.md

填写具体岗位信息。每个岗位建议复制一份单独文件，例如：

```text
knowledge/jobs/java-backend.md
knowledge/jobs/sales.md
knowledge/jobs/hr-specialist.md
```

### faq/*.md

填写候选人高频问题的标准口径。建议每个回答都能直接发给候选人。

### scripts/*.md

填写主动触达和跟进候选人的话术。话术里可以保留占位符，例如【岗位名称】、【地点】、【薪资范围】。

### prompts/*.md

维护大模型的回答规则。通常不需要频繁修改，除非回复风格或合规边界要调整。

### config/*.yaml

维护自动化开关、默认岗位、轮询间隔、每日上限和风险策略。

## 填写原则

- 可以承诺的写清楚。
- 不确定的写“需要人工确认”。
- 不要写候选人隐私。
- 不要写账号密码、Cookie、Token。
- 不要写招聘歧视性条件。

