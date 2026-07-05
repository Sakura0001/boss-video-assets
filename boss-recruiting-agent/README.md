# Boss Recruiting Agent

本目录是 Boss 直聘全自动招聘工具的业务框架。它不直接保存候选人隐私数据，而是维护自动招聘所需的配置、岗位知识库、问答库、提示词和流程说明。

## 设计原则

- 高内聚：每个文件只负责一种内容，例如岗位、FAQ、话术、提示词、流程。
- 低耦合：知识库不依赖具体执行代码，Boss CLI 操作也不写死业务答案。
- 配置驱动：是否全自动、默认岗位、轮询间隔、发送策略都放在 `config/`。
- 可审计：自动发送前的合规边界和风险策略单独维护。

## 目录说明

```text
config/
  agent.yaml                 全自动运行总配置
  risk_policy.yaml           自动发送和拦截策略
  school_policy.yaml         学校筛选策略
knowledge/
  company.md                 公司介绍、业务、团队、办公地点
  jobs/
    default.md               默认岗位模板
  schools/
    target-schools.md        目标学校名单
  faq/
    salary.md                薪资福利类问答
    interview.md             面试流程类问答
    worktime.md              作息加班类问答
    onboarding.md            入职流程类问答
  scripts/
    greetings.md             主动打招呼话术
    followups.md             跟进和追问话术
prompts/
  candidate_intent.md        候选人意图识别提示词
  hr_reply.md                HR 回复生成提示词
  compliance_check.md        发送前合规检查提示词
workflows/
  auto_greet.md              主动打招呼流程
  auto_reply.md              收到回复后的自动回答流程
  daily_run.md               每日自动化流程
knowledge/application/
  apply-links.md             投递链接和岗位选择口径
runtime/
  .gitkeep                   运行态目录占位，不提交隐私数据
docs/
  filling-guide.md           逐个文件填写指南
```

## 内容维护位置

岗位介绍维护在：

```text
knowledge/jobs/<岗位名>.md
```

投递链接和岗位选择维护在：

```text
knowledge/application/apply-links.md
```

常见问题维护在：

```text
knowledge/faq/
```

公司介绍维护在：

```text
knowledge/company.md
```

主动打招呼话术维护在：

```text
knowledge/scripts/greetings.md
```

大模型 HR 语气和回答规则维护在：

```text
prompts/hr_reply.md
```

全自动开关和默认岗位维护在：

```text
config/agent.yaml
```

自动发送风险边界维护在：

```text
config/risk_policy.yaml
```

目标学校名单维护在：

```text
knowledge/schools/target-schools.md
```

## 全自动运行思路

后续执行器应按以下顺序调用：

1. 读取 `config/agent.yaml` 判断是否启用全自动。
2. 使用 `boss recommend <岗位>` 或 `boss list --unread` 获取目标候选人。
3. 识别候选人的最终学历学校，并根据 `knowledge/schools/target-schools.md` 判断是否继续触达。
4. 使用 `knowledge/scripts/greetings.md` 和岗位知识生成主动打招呼内容。
5. 使用 `boss greet <姓名>` 主动触达。
6. 轮询 `boss list --unread` 发现候选人回复。
7. 使用 `boss chat <姓名>` 打开会话。
8. 根据候选人问题检索 `knowledge/`。
9. 候选人询问投递方式时，优先读取 `knowledge/application/apply-links.md`，默认推荐 AI 应用工程师岗位入口。
10. 使用 `prompts/hr_reply.md` 生成专业 HR 回复。
11. 使用 `config/risk_policy.yaml` 和 `prompts/compliance_check.md` 检查是否允许自动发送。
12. 通过检查后使用 `boss send --text "<回复内容>"` 自动发送。

## 隐私和提交规则

- 不要把 Boss 登录态、Cookie、Token、候选人简历、聊天记录提交到 Git。
- `runtime/` 只允许提交 `.gitkeep`，运行日志和缓存应被忽略。
- 知识库只维护公司和岗位可公开或可对候选人说明的信息。
