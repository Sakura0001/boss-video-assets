# Boss 直聘项目协作参考

本目录维护 Boss 直聘招聘自动化、`boss` CLI 副本和 `boss-zhaopin` skill。

## 唯一业务来源

招聘筛选、话术、投递资格、自动跟进、微信交换、状态和日报规则只维护在已安装 skill：

```text
/Users/yuyu/.codex/skills/boss-zhaopin/
```

仓库镜像位置：

```text
skills/boss-zhaopin/
```

镜像只由已安装 skill 的同步脚本生成，不得独立修改业务口径。`boss-recruiting-agent/` 是历史框架资料，不作为运行时来源。处理 Boss 任务时必须加载 `boss-zhaopin/SKILL.md` 及其按需引用的 references，不能从本文件推断候选人回复。

Windows 上从仓库根目录启动 Claude Code 时，项目桥接 skill 位于：

```text
.claude/skills/boss-zhaopin/SKILL.md
```

它只负责加载 `skills/boss-zhaopin/` 的仓库镜像，不维护第二套业务规则。Windows 运行时不得使用 `/Users/...` 或 `/opt/homebrew/...` 路径。

## Git 协作

1. 修改前运行 `git status --short`。
2. 只暂存当前任务相关文件，不提交其他子项目或调试文件。
3. 修改并验证后提交，并推送 GitHub。
4. 推送失败时明确说明原因。
5. 不把 token、Cookie、账号密码、手机号、微信号、简历或聊天全文写入 Git。

## Boss CLI

运行命令必须通过 `PATH` 解析：

```text
boss
```

仓库副本：

```text
tools/boss-cli/
```

常用命令：

```bash
boss help
boss login
boss list --unread
boss chat <姓名> --strict
boss send --text "<消息>"
boss action agree-resume
boss action wechat
boss positions
boss jd <岗位名称>
boss recommend <岗位关键字>
boss greet <姓名> --job <岗位关键字>
```

`boss login` 需要用户在浏览器完成登录。`greet`、在线简历预览和其他平台权益动作有成本，必须遵循 skill 中的上限和验证规则。

不要自动执行 `boss update`。本机或仓库中的 CLI 可能含有尚未发布的修复；只报告版本提示，除非用户明确要求升级。

## Live 操作安全

- 发送前使用 `boss chat "<姓名>" --strict` 精确打开会话。
- 不使用 shell 循环或并行方式批量发送真实消息。
- 前一步失败后不继续执行下一步。
- 接收简历、交换微信等动作后重新读取会话确认状态。
- 验证码、风控、异常弹窗或投诉出现时立即暂停。
- 不在候选人沟通中暴露 AI、自动化、内部规则或筛选原因。

## Skill 更新和同步

先更新并验证已安装 skill，再同步仓库镜像：

```bash
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_runtime_store.py
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/test_skill_contract.py
python3 /Users/yuyu/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/yuyu/.codex/skills/boss-zhaopin
python3 /Users/yuyu/.codex/skills/boss-zhaopin/scripts/sync_repo_copy.py \
  --destination <当前仓库根目录>/skills/boss-zhaopin
```

本地运行状态位于 `/Users/yuyu/.codex/state/boss-zhaopin/`，永远不能同步到仓库。

Windows 默认状态位置为 `%USERPROFILE%\.codex\state\boss-zhaopin\`，可由 `BOSS_ZHAOPIN_STATE_DIR` 覆盖，同样永远不能同步到仓库。Windows 安装、验证和 Claude Code `/loop 1m` 启动方式见 `docs/windows-setup.md`。
