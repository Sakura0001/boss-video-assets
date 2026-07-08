# Boss 直聘项目协作参考

本目录用于维护 Boss 直聘招聘自动化相关资料、知识库和后续 Skill/Agent 编排。当前本机已安装 `boss` CLI，可作为自动招聘工具的浏览器自动化入口。本仓库也在 `tools/boss-cli/` 保留了一份可分发副本，方便同事从 GitHub 拉取后本地安装使用。

全自动招聘 Agent 框架位于 `boss-recruiting-agent/`，其中 `config/` 维护自动化开关和风险策略，`knowledge/` 维护公司、岗位、FAQ 和话术，`prompts/` 维护大模型提示词，`workflows/` 维护自动化流程。

## 已安装工具

`boss` 命令位置：

```bash
/opt/homebrew/bin/boss
```

实际指向：

```text
/opt/homebrew/lib/node_modules/@joohw/boss-cli/dist/cli/index.js
```

安装包：

```text
@joohw/boss-cli
```

该工具是一个 Boss 直聘自动化 CLI，不是 Codex Skill。它基于本机 Chrome/CDP 复用登录态，适合被 Skill 或 Agent 通过子进程调用。

## 仓库内置副本

本仓库内置副本位置：

```text
tools/boss-cli/
```

同事拉取仓库后，可执行：

```bash
cd tools/boss-cli
npm install
npm install -g .
boss help
```

也可以不全局安装，直接运行：

```bash
cd tools/boss-cli
node dist/cli/index.js help
```

仓库不会提交 `node_modules/`。依赖需要在每台机器本地安装。该工具许可证为 GPL-3.0，复制和分发时必须保留 `tools/boss-cli/LICENSE`、`tools/boss-cli/README.md` 和来源信息。

## 常用命令

```bash
boss help
```

查看帮助。

```bash
boss login
```

打开 Boss 直聘登录页。需要用户在浏览器里自行完成登录。

```bash
boss list
boss list --unread
```

读取聊天列表。`--unread` 只读取未读候选人。

```bash
boss chat <姓名>
boss chat <姓名> --strict
```

打开指定候选人会话。默认包含匹配，`--strict` 为精确匹配。仅适用于已建立联系、能在聊天列表里看到的候选人。

```bash
boss send --text "同学，方便发一下简历吗？"
boss send -t "同学，方便沟通一下这个岗位吗？"
boss send --text "同学，辛苦发一下附件简历。" --request-resume
```

向当前已打开的候选人会话发送文本消息。`--request-resume` 会在发送后自动执行“求简历”操作。

```bash
boss action resume
boss action not-fit
boss action remark --remark "候选人已沟通，关注 Java 后端岗位"
boss action agree-resume
boss action request-attachment-resume
boss action history
boss action wechat
```

在当前聊天页已打开候选人详情时执行操作。

```bash
boss positions
```

读取当前职位列表，包含开放、待开放、已关闭状态。

```bash
boss jd <岗位名称>
```

抓取指定职位详情，并缓存为本地同名 Markdown 文件。后续知识库和自动回复应优先引用这些 JD 内容。

```bash
boss recommend [岗位关键字]
boss preview <姓名> --job <岗位关键字>
boss greet <姓名> --job <岗位关键字>
boss deep-search [岗位关键字]
```

用于推荐页、简历预览、打招呼和深度搜索。`preview` 会消耗平台在线简历查看次数，`greet` 会消耗打招呼次数，使用前要谨慎确认。

## 建议的 Agent 编排流程

自动招聘问答建议按以下顺序执行：

1. 使用 `boss list --unread` 获取未读候选人。
2. 对每个候选人使用 `boss chat <姓名>` 打开会话。
3. 读取当前岗位资料：优先使用 `boss jd <岗位名称>` 生成或更新 JD 缓存。
4. 从本项目知识库中检索匹配内容，例如岗位职责、薪资范围、工作地点、作息、福利、面试流程、入职要求。
5. 结合候选人的问题、岗位 JD、知识库答案生成专业 HR 语气回复。
6. 发送前检查回复是否存在违规承诺、歧视性表达、过度保证或未经确认的信息。
7. 使用 `boss send --text "<回复内容>"` 发送。

## 标准候选人转化流程

本项目的标准全自动招聘流程以“Boss 触达，微信承接”为目标。Agent 执行时应优先遵循 `boss-recruiting-agent/workflows/candidate_conversion.md`。

1. 先识别候选人最终学历学校，并对照 `boss-recruiting-agent/knowledge/schools/target-schools.md`。学校命中后才主动打招呼。
2. 使用 `boss greet <姓名>` 打招呼。
3. `boss greet` 后必须立刻补充一条真人化消息：“我看了下你的背景，和我们数据库方向挺匹配的，方便的话我给你简单介绍下我们这边方向。”这是必须环节，用来避免平台默认招呼语显得过于模板化。
4. 真人化补充消息之后，只补充 1 条合并岗位介绍，一次讲清楚部门/产品、岗位工作内容和方向优势；不要拆成两条占用发送机会，也不要继续连发 4-5 条。城市、流程、投递等信息等候选人回复或主动询问后再说。
5. 岗位介绍发送完后，主动索要附件简历：`boss send --text "方便的话辛苦发我一份附件简历，我帮你进一步看下和数据库方向的匹配度。" --request-resume`。
6. 如果候选人先发起附件简历请求，必须先只回复“收到同学”，再执行 `boss action agree-resume` 接收简历，并重新打开会话确认 `简历获取状态: 已获取`，再进入后续投递状态确认、投递引导或微信承接。不要在接收简历前补“我这边先帮你看下”等额外解释。
   - 如果候选人首次问“机会大吗”“进的机会大吗”“概率大吗”等，回复：“我看了下机会挺大的，只要你性格测评和笔试通过了，这个帮不了你，到后面面评不差的话offer概率还是很大的”。
   - 如果候选人重复问机会，或追问“你没骗我吧”“真的假的”等，不要复读上一句，改用：“没骗你哈，我不会拿这个忽悠你。你这个背景确实可以往我们方向推，但测评、笔试和面试还是要自己过。我们先加个微信，后续投递和编号我在微信上跟你说。”
7. 当候选人已发送并已接收简历，或已经明确表达兴趣、问过岗位优势/组织归属/地点/流程等关键问题且沟通差不多时，及时转入微信承接，不要在 Boss 中继续拖长对话。
   - 如果候选人还没投递过、简历编号没给过别人，或已经投递但有改投、路由到我们部门、重新投递我们部门并重新笔试的意向，直接交换微信。
   - 交换微信后，后续沟通转到微信承接，Boss 侧不再继续反复推进投递细节。
8. 转微信时先发送：“同学，沟通下来我感觉你和我们数据库方向还挺匹配的。如果你方便的话，可以加我微信，后续沟通会更及时一些，我也可以继续帮你跟一下流程。”
9. 使用 `boss action wechat` 发送微信交换入口。
10. 发出微信交换入口后，必须补充：“辛苦你这边主动加我一下哈，我们账号一天不能主动添加太多同学，频繁添加容易异常。加上后你备注一下姓名，我后续在微信上跟你继续沟通。”
11. 候选人发来微信、表示已添加，或已明确知道需要主动添加微信后，Boss 对话可以结束，后续转到微信沟通。

不要在候选人没有表现出意向前索要微信。不要由我频繁主动添加候选人微信，因为账号一天不能主动添加太多同学，频繁添加容易异常。

## 组织归属核心口径

候选人询问“部门属于 ICT 还是华为云”“是不是华为云下的团队”“组织归属在哪里”时，必须明确回答：

- 我们部门组织归属是华为 ICT 体系下，不是华为云下。
- 业务会涉及云数据库、云服务和企业级数据库场景，但组织归属口径必须说清楚：属于 ICT，不属于华为云。
- 可以对候选人自然表达为：“这个点我明确一下，我们部门是 ICT 下的，不是华为云下的。业务上会涉及云数据库场景，但组织归属不是华为云。”
- 不要含糊回答成“同时涉及 ICT 和云”“看最终团队再确认”等容易让候选人误解的说法。
- 不要主动攻击或评价华为云，只需要正面澄清我们部门属于 ICT。

## 投递状态与微信承接口径

候选人询问“怎么投递”“投哪个岗位”“投递链接是什么”，或表示未投递、简历编号没给过别人、有转投意向时，必须先读取 `boss-recruiting-agent/knowledge/application/apply-links.md`。

- 本项目不再维护投递链接、真实 URL 或岗位链接表。
- Boss 侧不要发送投递链接、官网入口、岗位入口选择、真实 URL 或简历编号备案细节。
- 每次正式推进前，可以自然确认一句：“同学你这边是不是还没有投递呀？”如果候选人已经投递到合适的 ICT 部门，且没有表达需要我帮忙跟流程，就不要重复推投递，也不要强行换微信。
- 如果候选人还没投递、简历编号没给过别人、有转投/改投/路由到我们部门意向，或笔试没有通过，直接使用 Boss CLI 交换微信，后续投递、编号、转投和重新笔试细节在微信沟通。
- 笔试未通过的同学直接说明可以投递我们部门重新笔试，然后交换微信。
- 交换微信后，Boss 侧不再继续反复推进投递细节。

## 知识库维护位置

- 公司介绍：`boss-recruiting-agent/knowledge/company.md`
- 岗位介绍：`boss-recruiting-agent/knowledge/jobs/<岗位名>.md`
- 投递状态和微信承接：`boss-recruiting-agent/knowledge/application/apply-links.md`
- 目标学校名单：`boss-recruiting-agent/knowledge/schools/target-schools.md`
- 薪资福利：`boss-recruiting-agent/knowledge/faq/salary.md`
- 作息加班：`boss-recruiting-agent/knowledge/faq/worktime.md`
- 面试流程：`boss-recruiting-agent/knowledge/faq/interview.md`
- 入职材料：`boss-recruiting-agent/knowledge/faq/onboarding.md`
- 主动打招呼话术：`boss-recruiting-agent/knowledge/scripts/greetings.md`
- 跟进话术：`boss-recruiting-agent/knowledge/scripts/followups.md`
- 个人语气与话术风格：`boss-recruiting-agent/knowledge/style/recruiter_voice.md`
- 全自动开关：`boss-recruiting-agent/config/agent.yaml`
- 学校筛选策略：`boss-recruiting-agent/config/school_policy.yaml`
- 自动发送风险策略：`boss-recruiting-agent/config/risk_policy.yaml`
- 候选人转化流程：`boss-recruiting-agent/workflows/candidate_conversion.md`

## 回复风格要求

自动回复必须以招聘负责人本人的口吻和候选人沟通，让对方感受到是在和真实 HR 正常交流，而不是在和机器人、脚本或大模型对话。这是本项目最根本的回复要求。

- 使用第一人称，例如“我这边”“我帮你看一下”“我给你简单介绍下”。
- 默认称呼候选人为“同学”，这样更亲切；除非明确不是学生/校招语境，否则避免正式称谓和过度敬语。
- 具体语气和话术应优先参考 `boss-recruiting-agent/knowledge/style/recruiter_voice.md`。
- 语气自然，像日常招聘沟通，不要像公告、客服模板、机器人提示或系统通知。
- 不要暴露自动化身份，不要提到“我是 AI”“我是 Agent”“我是机器人”“根据知识库”“系统显示”等表达。
- 不要输出分析过程、检索过程、规则判断或内部策略。
- 不要机械复读候选人的问题；应直接接话、回答、推进下一步。
- 不要使用过度正式或营销化表达，避免让候选人感觉是模板话术。
- 礼貌、清晰、简洁。
- 先正面回答候选人的核心问题。
- 对薪资、录用、编制、远程、加班、福利等敏感事项，只表达已确认信息，不做绝对承诺。
- 不使用歧视性或不合规表述，例如年龄、性别、婚育、地域等不当筛选。
- 信息不确定时，应说明“我这边再确认一下”或“以面试沟通和公司最终确认为准”。
- 对笔试题型、流程经验等公开渠道常见但我这边拿不准的信息，不要编造；可以建议同学去小红书、微信公众号或者网上经验贴找一下参考参考。对外口径要自然：“公司内部招聘流程都差不多，网上这些经验可以参考一下。”
- 候选人表示“想了解一下方向”“看一下匹不匹配”时，必须拆成两次单独发送，不要一次发两段。第一条先介绍方向和匹配点，方向统一写成“数据库/软件研发/测试开发”，斜杠和英文缩写前后不要额外加空格，整体像真人手机打字；第二条再单独补充我这边的优势，用来把方向核心性、成长空间、简历认可度讲清楚，吸引同学继续沟通。

## 安全边界

- 不要把 Boss 登录 Cookie、Token、手机号、候选人隐私、简历原文提交到 Git。
- 不要把 GitHub token、Boss 账号密码或任何认证凭据写入代码、文档或提示词。
- 不要批量导出或长期保存与招聘目的无关的候选人隐私数据。
- 发送消息前，应确保内容与招聘沟通相关，且符合平台规则和公司合规要求。

## 后续 Skill 建议

后续可创建一个本地 Codex Skill，例如 `boss-recruiting-qa`，专门封装以下能力：

- 调用 `boss` CLI 读取候选人和岗位信息。
- 维护招聘知识库。
- 按岗位、城市、招聘阶段检索问答。
- 生成专业 HR 回复。
- 对敏感承诺和不合规表达做发送前检查。
