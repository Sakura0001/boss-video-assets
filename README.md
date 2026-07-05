# Boss 直聘自动化工具

本仓库用于保存 Boss 直聘招聘自动化相关资料、工具副本和后续知识库。当前已内置 `@joohw/boss-cli` 的可分发副本，方便同事从 GitHub 拉取后在本机安装使用。

## 目录结构

```text
boss-recruiting-agent/  全自动招聘 Agent 框架、知识库、提示词和流程
tools/boss-cli/       Boss 直聘 CLI 工具副本
video-assets/         项目视频或素材资源
AGENTS.md             Agent/Skill 协作参考说明
```

## 环境要求

- Node.js 20 或更高版本
- 本机已安装 Chrome / Chromium
- 可正常访问 Boss 直聘 B 端

## 安装使用

拉取仓库后进入 CLI 目录：

```bash
cd tools/boss-cli
npm install
```

本仓库不会提交 `node_modules/`，依赖需要在每台机器本地安装。

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

```bash
boss login
```

该命令会打开 Boss 直聘登录页，需要用户在浏览器中自行完成登录。登录态保存在本机，不要提交任何 Cookie、Token 或缓存文件。

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

更多 Agent 协作细节见 `AGENTS.md`，工具原始说明见 `tools/boss-cli/README.md`。

## 全自动招聘 Agent 框架

全自动招聘框架位于：

```text
boss-recruiting-agent/
```

它把自动招聘拆成几类独立内容：

```text
boss-recruiting-agent/config/       自动化开关、默认岗位、风险策略
boss-recruiting-agent/knowledge/    公司介绍、岗位介绍、FAQ、话术
boss-recruiting-agent/prompts/      大模型意图识别、HR 回复、合规检查提示词
boss-recruiting-agent/workflows/    主动打招呼、自动回复、每日运行流程
boss-recruiting-agent/runtime/      运行态占位目录，不提交候选人隐私数据
```

常用维护位置：

- 岗位介绍：`boss-recruiting-agent/knowledge/jobs/<岗位名>.md`
- 公司介绍：`boss-recruiting-agent/knowledge/company.md`
- 薪资福利问答：`boss-recruiting-agent/knowledge/faq/salary.md`
- 作息加班问答：`boss-recruiting-agent/knowledge/faq/worktime.md`
- 面试流程问答：`boss-recruiting-agent/knowledge/faq/interview.md`
- 入职材料问答：`boss-recruiting-agent/knowledge/faq/onboarding.md`
- 主动打招呼话术：`boss-recruiting-agent/knowledge/scripts/greetings.md`
- 跟进话术：`boss-recruiting-agent/knowledge/scripts/followups.md`
- 全自动开关：`boss-recruiting-agent/config/agent.yaml`
- 自动发送风险策略：`boss-recruiting-agent/config/risk_policy.yaml`

推荐按 `boss-recruiting-agent/docs/filling-guide.md` 的顺序逐个补齐内容。

## 注意事项

- `@joohw/boss-cli` 使用 GPL-3.0 许可证，分发时必须保留 `tools/boss-cli/LICENSE`、`tools/boss-cli/README.md` 和来源信息。
- 不要提交 Boss 登录缓存、Cookie、Token、候选人简历、聊天记录或其他隐私数据。
- 批量打招呼、简历预览和自动发送消息前，请确认平台规则和公司招聘合规要求。
