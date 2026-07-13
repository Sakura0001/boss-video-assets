# 本仓库内置 boss-cli 使用说明

本目录是从本机已安装的 `@joohw/boss-cli` 复制的可分发副本，用于让同事从当前 GitHub 仓库获取同一套 Boss 直聘 CLI 工具。

## 安装依赖

进入本目录：

```bash
cd tools/boss-cli
npm install
```

本仓库不会提交 `node_modules/`。依赖需要在每台机器本地安装。

## 运行方式

在本目录内直接运行：

```bash
node dist/cli/index.js help
```

也可以临时使用 npm 执行：

```bash
npx . help
```

如需安装为全局 `boss` 命令：

```bash
cd tools/boss-cli
npm install -g .
boss help
```

## 首次登录

```bash
boss login
```

该命令会打开 Boss 直聘登录页，需要用户在浏览器中自行完成登录。

## 后台浏览器模式

```bash
boss browser status
boss browser start --headless
boss browser restart --headful
boss login
boss browser restart --headless
boss browser stop
```

普通业务命令默认不再把浏览器窗口切到前台。`boss login` 始终使用可视模式；登录完成后运行 `boss browser restart --headless` 即可回到后台。

如果 `status` 显示 `unmanaged`，说明固定调试端口上是升级前启动的旧浏览器。生命周期命令不会自动关闭它；手动关闭该旧窗口一次，再启动受管浏览器即可。

## 常用命令

```bash
boss list
boss list --unread
boss chat <姓名>
boss send --text "您好，请问方便沟通一下这个岗位吗？"
boss positions
boss jd <岗位名称>
boss recommend [岗位关键字]
boss deep-search [岗位关键字]
```

更多用法见本目录的 `README.md` 或运行：

```bash
boss help
```

## 注意事项

- 本工具许可证为 GPL-3.0，复制和分发时必须保留 `LICENSE`、`README.md` 和来源信息。
- 不要提交 `node_modules/`、Boss 登录缓存、Cookie、Token、候选人简历或聊天隐私数据。
- `preview` 会消耗平台在线简历查看次数，`greet` 会消耗打招呼次数，批量使用前请确认招聘策略和平台规则。
