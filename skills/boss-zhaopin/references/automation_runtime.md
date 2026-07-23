# 自动运行与本地状态

## 状态位置

默认状态数据库为：

`~/.codex/state/boss-zhaopin/state.sqlite3`

Windows 上解析为 `%USERPROFILE%\.codex\state\boss-zhaopin\state.sqlite3`。如需改位置，设置 `BOSS_ZHAOPIN_STATE_DIR`；它指向目录，不是数据库文件。

macOS 和 Linux 使用目录权限 `0700`、数据库权限 `0600`。Windows 把状态放在当前用户配置文件内，并由安装脚本收紧目录 ACL。数据库和任何导出报告不得提交到 Git。

运行时脚本始终通过当前 skill 根目录解析：`<skill-root>/scripts/runtime_store.py`。不得硬编码某台机器的用户名或绝对路径。

## 启动

### macOS / Linux

```bash
SKILL_ROOT="<当前 SKILL.md 所在目录>"
NOW_ISO="$(date -Iseconds)"
python3 "$SKILL_ROOT/scripts/runtime_store.py" init
python3 "$SKILL_ROOT/scripts/runtime_store.py" purge --as-of "$NOW_ISO"
python3 "$SKILL_ROOT/scripts/runtime_store.py" greeting-count --date "YYYY-MM-DD"
python3 "$SKILL_ROOT/scripts/runtime_store.py" due-followups --as-of "$NOW_ISO"
```

### Windows PowerShell

从仓库根目录运行 Claude Code 时，项目 skill 根目录是 `skills\boss-zhaopin`：

```powershell
$SkillRoot = (Resolve-Path ".\skills\boss-zhaopin").Path
$NowIso = (Get-Date).ToString("o")
py -3 "$SkillRoot\scripts\runtime_store.py" init
py -3 "$SkillRoot\scripts\runtime_store.py" purge --as-of $NowIso
py -3 "$SkillRoot\scripts\runtime_store.py" greeting-count --date "YYYY-MM-DD"
py -3 "$SkillRoot\scripts\runtime_store.py" due-followups --as-of $NowIso
```

候选人标识优先使用 Boss 页面或 CLI 提供的稳定会话标识。无法取得时，使用规范化姓名、最终学校和毕业年份生成本地哈希；不得用姓名模糊匹配替代发送前的 `boss chat "<姓名>" --strict`。

## 事件

每个成功动作后记录一个事件：

- `greeted`
- `candidate_replied`
- `resume_received`
- `confirmed_unsubmitted`
- `confirmed_non_cloud_software`
- `wechat_exchange_completed`
- `stopped`，payload 写终止原因
- `knowledge_gap`，payload 只写脱敏摘要

先确认 Boss 动作成功，再写事件。失败动作不能计数。

主动打招呼成功后使用 `greeting-complete` 原子写入 `greeted` 事件、长期去重
和候选人 `greeted` 阶段。不得分别调用 `record-event` 与 `dedupe-add` 模拟
该动作，以免中断后出现计数和去重不一致。

```text
macOS / Linux:
python3 "$SKILL_ROOT/scripts/runtime_store.py" greeting-complete \
  --candidate-id "<稳定候选人ID>" --display-name "<姓名>" \
  --greeted-at "<ISO时间>" --job "<岗位>" \
  --school "<最终学校>" --major "<专业>" --degree "<学历>" --grad-year 2027

Windows PowerShell:
py -3 "$SkillRoot\scripts\runtime_store.py" greeting-complete `
  --candidate-id "<稳定候选人ID>" --display-name "<姓名>" `
  --greeted-at "<ISO时间>" --job "<岗位>" `
  --school "<最终学校>" --major "<专业>" --degree "<学历>" --grad-year 2027
```

## 保留规则

- 候选人执行状态保存三天，之后自动删除。
- 长期去重索引保存到 `2027-12-31`。
- 微信交换台账和每日日报一直保留，供微信二次核对。
- 微信台账允许保存 Boss 显示姓名、会话标识、交换时间、最终学校、专业、学历、投递状态、原部门和备注。
- 不保存简历正文、手机号、微信号、Cookie、Token 或完整聊天记录。

## 转投判断

把对话提取成结构化字段后运行：

macOS / Linux：

```bash
python3 "$SKILL_ROOT/scripts/runtime_store.py" evaluate-transfer \
  --application-target "none|cloud_software|other|unknown" \
  --psych-status "not_taken|passed|failed|unknown" \
  --interview-status "not_started|started|unknown" \
  --written-status "not_taken|passed|failed|unknown"
```

Windows PowerShell 使用相同参数，把解释器和脚本路径换为：

```powershell
py -3 "$SkillRoot\scripts\runtime_store.py" evaluate-transfer `
  --application-target "none|cloud_software|other|unknown" `
  --psych-status "not_taken|passed|failed|unknown" `
  --interview-status "not_started|started|unknown" `
  --written-status "not_taken|passed|failed|unknown"
```

`ask_process_stage` 表示继续询问流程阶段，不得提前交换微信。

## 微信交换完成

仅在 `boss action wechat` 已确认完成后运行 `wechat-complete`。传入 Boss 显示姓名和已知资料；不要传简历正文或联系方式。

## 日报

```text
macOS / Linux: python3 "$SKILL_ROOT/scripts/runtime_store.py" daily-report --date "YYYY-MM-DD"
Windows PowerShell: py -3 "$SkillRoot\scripts\runtime_store.py" daily-report --date "YYYY-MM-DD"
```

日报包含招呼、回复、简历、投递状态、微信交换、转化率、终止原因、知识缺口，以及当天完成微信交换的候选人名单。数据库没有该日期的数据时，明确说没有记录，不得编造或擅自填零。
