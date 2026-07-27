# Boss 直聘自动化工具

本仓库用于保存 Boss 直聘招聘自动化相关资料、工具副本和后续知识库。当前已内置 `@joohw/boss-cli` 的可分发副本，方便同事从 GitHub 拉取后在本机安装使用。

当前给普通用户使用的运行范围只有：筛选合格候选人、打招呼、发送三条知识库
消息，并持续执行到当天累计 150 个。未读、跟进、简历和微信流程不会运行。

## 目录结构

```text
skills/boss-zhaopin/                  当前招聘业务 skill 的仓库镜像
.claude/skills/boss-zhaopin/          Claude Code 项目 skill 桥接
scripts/setup-windows.ps1             Windows 环境准备脚本
scripts/greet_only.py                 一键登录并自动打满招呼的 Python 执行器
tools/boss-cli/                       Boss 直聘 CLI 工具副本
boss-recruiting-agent/                历史框架资料，不作为运行时来源
AGENTS.md                              Agent/Skill 协作参考说明
```

## 环境要求

- Node.js 20 或更高版本
- Python 3.9 或更高版本
- 64 位 Windows 10 1809 或更高版本（Windows 运行时）
- 本机已安装 Chrome / Chromium
- 可正常访问 Boss 直聘 B 端

## 安装使用

拉取仓库后进入 CLI 目录：

```bash
cd tools/boss-cli
npm install
```

本仓库不会提交 `node_modules/`，依赖需要在每台机器本地安装。

### Windows 一键安装与运行

在 PowerShell 中从仓库根目录运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
py -3 .\scripts\greet_only.py
```

Python 会检查 Boss CLI 登录状态；未登录时自动打开浏览器并等待用户登录，
登录成功后立即使用 Boss 推荐页当前选中的默认岗位开始执行。无需启动
Claude Code、无需 `/loop`，也无需输入岗位名。完整步骤和故障排查见
[Windows 迁移说明](docs/windows-setup.md)。

旧电脑的 `state.sqlite3` 不得上传 GitHub，但建议按迁移说明通过私密通道
复制到 Windows，避免丢失当日计数和长期去重。

## 运行方式

不全局安装时，可以直接运行：

```bash
cd tools/boss-cli
node dist/cli/index.js help
```

也可以安装为全局 `boss` 命令：

```bash
cd tools/boss-cli
npm install -g .
boss help
```

## 首次登录

直接运行 `scripts/greet_only.py`。脚本发现未登录后会调用 CLI 打开 Boss
登录页并等待；用户只需在浏览器完成登录。登录态保存在本机，不要提交任何
Cookie、Token 或缓存文件。

## 常用命令

```bash
boss list
boss list --unread
```

读取聊天列表；`--unread` 只读取未读候选人。

```bash
boss chat <姓名>
boss chat <姓名> --strict
```

打开指定候选人会话。默认包含匹配，`--strict` 为精确匹配。

```bash
boss send --text "您好，请问方便沟通一下这个岗位吗？"
```

向当前已打开的候选人会话发送消息。

```bash
boss positions
boss jd <岗位名称>
```

读取职位列表，或抓取指定岗位 JD 并缓存为 Markdown 文件。

```bash
boss recommend [岗位关键字]
boss deep-search [岗位关键字]
boss preview <姓名> --job <岗位关键字>
boss greet <姓名> --job <岗位关键字>
```

用于推荐候选人、深度搜索、简历预览和打招呼。`preview` 会消耗平台在线简历查看次数，`greet` 会消耗打招呼次数，请谨慎使用。

## Agent/Skill 使用建议

自动招聘问答建议按以下流程编排：

1. 使用 `boss list --unread` 获取未读候选人。
2. 使用 `boss chat <姓名>` 打开候选人会话。
3. 使用 `boss jd <岗位名称>` 获取或更新岗位 JD。
4. 从本项目知识库检索岗位、薪资、地点、作息、福利、面试流程等信息。
5. 生成专业 HR 语气回复，并检查是否存在不合规承诺或敏感表述。
6. 使用 `boss send --text "<回复内容>"` 发送。

真实自动招聘必须使用 `skills/boss-zhaopin/SKILL.md` 及其 references，不从下面的历史框架推断业务口径。更多 Agent 协作细节见 `AGENTS.md`，工具原始说明见 `tools/boss-cli/README.md`。

## 历史 Agent 框架

旧版框架资料位于：

```text
boss-recruiting-agent/
```

该目录仅供历史参考，不作为当前运行时来源。当前规则统一位于 `skills/boss-zhaopin/`。

历史目录结构：

```text
boss-recruiting-agent/config/       自动化开关、默认岗位、风险策略
boss-recruiting-agent/knowledge/    公司介绍、岗位介绍、FAQ、话术
boss-recruiting-agent/prompts/      大模型意图识别、HR 回复、合规检查提示词
boss-recruiting-agent/workflows/    主动打招呼、自动回复、每日运行流程
boss-recruiting-agent/runtime/      运行态占位目录，不提交候选人隐私数据
```

常用维护位置：

- 岗位介绍：`boss-recruiting-agent/knowledge/jobs/<岗位名>.md`
- 投递链接和岗位选择：`boss-recruiting-agent/knowledge/application/apply-links.md`
- 目标学校名单：`boss-recruiting-agent/knowledge/schools/target-schools.md`
- 公司介绍：`boss-recruiting-agent/knowledge/company.md`
- 薪资福利问答：`boss-recruiting-agent/knowledge/faq/salary.md`
- 作息加班问答：`boss-recruiting-agent/knowledge/faq/worktime.md`
- 面试流程问答：`boss-recruiting-agent/knowledge/faq/interview.md`
- 入职材料问答：`boss-recruiting-agent/knowledge/faq/onboarding.md`
- 主动打招呼话术：`boss-recruiting-agent/knowledge/scripts/greetings.md`
- 跟进话术：`boss-recruiting-agent/knowledge/scripts/followups.md`
- 个人语气与话术风格：`boss-recruiting-agent/knowledge/style/recruiter_voice.md`
- 全自动开关：`boss-recruiting-agent/config/agent.yaml`
- 学校筛选策略：`boss-recruiting-agent/config/school_policy.yaml`
- 自动发送风险策略：`boss-recruiting-agent/config/risk_policy.yaml`
- 候选人转化流程：`boss-recruiting-agent/workflows/candidate_conversion.md`

不要在该历史目录独立修改当前筛选、话术、投递、跟进或微信交换规则。

## 仅主动打招呼

不需要处理未读、跟进、简历或微信时，可在仓库根目录启动确定性的
Python 执行器。它从推荐页右侧读取全部结构化教育经历，并从
`skills/boss-zhaopin/references/` 读取学校、专业和三条主动招呼话术；
多所学校时任意一所精确命中目标名单即可，不调用大模型生成或改写消息。

只读配置校验：

```powershell
py -3 .\scripts\greet_only.py --validate-only
```

正式执行只需：

```powershell
py -3 .\scripts\greet_only.py
```

脚本默认目标是当天累计 150 个招呼，并使用 Boss 推荐页当前选中的岗位。
没有登录时自动打开登录页等待；不需要 `--execute`、`--job`、Claude Code
或 `/loop`。

执行器读取本地 `greeting-count` 断点续跑，每批最多检查十名不同候选人；
当前批次没有合格候选人时显式刷新推荐页。招呼成功后，只进入一次精确会话，
在当前会话中按知识库原文逐条发送并验证三条消息。每次发送前仍会核对姓名
和沟通岗位，但不会反复退出、重进聊天页。每位候选人操作前随机等待 1–2 秒，
进度输出包含该候选人的完整流程耗时。达到150、超出09:00–21:00、达到
候选人检查上限，或遇到登录、验证码、风控、精确会话和发送异常时停止。
进度中的 `selectionSeconds` 是筛选耗时，`workflowSeconds` 是招呼到三条
消息验证完成的耗时，`cycleSeconds` 是该候选人的完整周期耗时。

不要与另一台电脑、第二个终端或任何其他 Boss 自动化执行器同时运行。

用户只需要运行上述 Python 命令；候选人筛选、推荐页刷新、精确 ID 招呼、
聊天页切换、三条消息发送、结果验证和状态记录均由脚本自动编排。

## 注意事项

- `@joohw/boss-cli` 使用 GPL-3.0 许可证，分发时必须保留 `tools/boss-cli/LICENSE`、`tools/boss-cli/README.md` 和来源信息。
- 不要提交 Boss 登录缓存、Cookie、Token、候选人简历、聊天记录或其他隐私数据。
- 批量打招呼、简历预览和自动发送消息前，请确认平台规则和公司招聘合规要求。
