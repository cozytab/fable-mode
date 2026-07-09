# fable-mode

[English](README.md) | **简体中文**

**一套工作纪律协议，让 Opus 4.8（或任意非顶级模型）以 Fable-5 级别的质量干活。**

fable-mode 是一个 [Claude Code](https://claude.com/claude-code) skill，外加一组
守卫 hook。核心前提：

> **产出质量 = 模型能力 × 工作纪律**

---

## 快速上手

```bash
# 1. 安装 skill（认 CLAUDE_CONFIG_DIR，没设就退回 ~/.claude）
git clone https://github.com/cozytab/fable5-mode \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode"

# 2.（可选）注册强制层 hook——合并进你的 settings.json，自解析路径，幂等：
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/install.sh"
```

```text
# 3. 在 Claude Code 里，直接开口要它——任意语言都行：
   "用 fable 模式"   ·   "use fable mode"   ·   "严谨点，一次做对"
```

```bash
# 4. 对你认真对待的项目，开启强制：
mkdir .fable
printf -- '- [ ] 1. 第一张卡（带可机器验证的验收）\n' > .fable/LEDGER.md
```

skill 单独就能用；第 2 步**可选**（把纪律变成硬拦截）。skill 虽然用英文写，
Claude 仍会用**你的**语言回复。

## 设计初衷与效果

**为什么做它。** 弱模型多数时候不是当场"变笨"才失败，而是败在*过程*：边想边写、
写到一半改主意；不跑任何东西就说"看起来对"；不做验证就把活撒出去；任务干到一半
悄悄停下。这些是过程性失败，而过程可以用结构来修。既然顶级产出里"纪律那一半"与
模型无关，你就能把强模型的*工作习惯*交给便宜的模型，补回相当一块差距——代价是
多花编排步骤，而不是换更大的模型。

**你实际得到什么。**

- 思考发生在最便宜的阶段（写好的设计门禁），而不是实现到一半才想。
- "做完"意味着验收命令跑过了——不是"看起来对"。
- 关键产出在交付前先过一轮对抗式*证伪*。
- 长任务里上下文保持干净：靠外部 SPEC/PROGRESS 记忆，而不是越滚越肥的对话。
- 模型最爱偷懒的两条——*撒活之前先写计划*、*别带着没做完的活就收尾*——由 hook
  强制，而不是靠自觉。
- 它对自己的天花板很诚实：真撞到能力墙（从零推导长链条、一次吃下超大代码库、精细
  审美判断），它会告诉你该换更强的模型，而不是硬装。

**它不做什么。** 它不会把 Opus 变成 Fable 5。它补的是*纪律*差距，不是*能力*差距。
代价是真实的——多花编排步骤、小任务上更慢——所以小任务别用它。（净 token 视任务
而定；容易返工的活反而可能更省。）

## 六大杠杆

| # | 杠杆 | 强制什么 |
|---|---|---|
| 1 | **设计门禁** | 动手写码前先写 `docs/SPEC.md`（需求 + 方案 + 任务卡，每卡带*可机器验证*的验收）。把思考集中在最便宜的阶段。 |
| 2 | **小卡执行** | 每张卡在新鲜上下文里跑；验收命令不过就不进下一卡；失败 2 次就升级攻坚，而不是瞎试。 |
| 3 | **对抗式自查** | 不"生成即交付"。派独立视角去*证伪*关键产出；宽解空间的难题则生成 N 个方案 + 评审 + 合成。 |
| 4 | **真实产品验证** | 静态检查全绿 ≠ 能用。每个里程碑端到端跑真实产品，留证据（截图、日志、测试输出）。 |
| 5 | **上下文卫生** | SPEC + PROGRESS 是外部记忆。靠重读它们恢复现场，而不是把失败尝试的推理拖进臃肿上下文。 |
| 6 | **断点自治** | 后台长任务配看门狗 + 可续跑断点，挂一次最多损失一张卡。 |

完整协议在 **[`SKILL.md`](SKILL.md)** ——那才是 Claude 实际读的文本。

## 强制层（比提示词多出来的那部分）

六大杠杆写成散文，仍靠模型自觉。四个 hook 把最容易偷懒的规则变成硬拦截：

| Hook | 事件 | 效果 |
|---|---|---|
| **Profile Injector** | `SessionStart` | 自动注入纪律，**按账本状态定量**——进行中的轮次注入全量，空闲/暂停时只有一行——外加按模型选档和未勾项恢复。 |
| **Spawn Guard** | `PreToolUse`（Agent/Task/Workflow） | 没写账本就想派详细 subagent/Workflow，拦——逼你先过设计门禁；同时机械执行**模型天花板**：任何想用比主会话更强模型的 spawn 直接拦下，不再只靠嘴上说。 |
| **Fail-Streak Reminder** | `PostToolUse`（Bash） | 纯提醒、永不拦截：连续第 3 次命令失败时注入**归因阶梯**（先怀疑测试本身 → 再证明新代码真的在跑 → 最后才调产品，且按不变量修"类"不修"例"）——治在错误层级上死磨。 |
| **Close Guard** | `Stop` | 账本还有未勾项就想结束回合，拦——治提前收尾/空转。同时强制**关卡带证据**：`- [x]` 卡片没有 `-- evidence:` 标记就想收尾，拦——"报证据，不报形容词"从嘴上说变成硬规则。 |

另有 **`hooks/fable_lint.py`**（非 hook，一键体检 CLI）：查 SPEC 是否带
`[实测]/[推断]/[未展示]` 来源标签、每张开卡是否写了验收、每张关卡是否带证据。
收尾或 CI 时跑：`python3 hooks/fable_lint.py <项目目录>`。

让它敢全局注册的几个设计属性：

- **按项目 opt-in**：靠 `.fable/` 目录（向上查找，到 git root 为界）。没有
  `.fable/` → hook 静默放行，绝不碰你没 opt-in 的项目。
- **fail-open**：hook 任何异常都放行（exit 0）。守卫里的 bug 绝不会 brick 你的会话。
- **loop-safe**：close guard 认 `stop_hook_active`，不会把你困死。
- **豁免**：小 spawn（< 1500 字符）和 fork 永不拦。

机制细节见 **[`hooks/README.md`](hooks/README.md)**。

## 安装

**前置要求**：[Claude Code](https://claude.com/claude-code)，以及 `python3`
（仅标准库，无第三方依赖；只有用 hook 时才需要）。

你的 Claude 配置目录：设了 `$CLAUDE_CONFIG_DIR` 就用它，否则是 `~/.claude`。下面
全部由它推导，所以你的配置装在哪都能用。

### 方式 A —— 自动（推荐；这也是 AI 能替你跑的）

```bash
git clone https://github.com/cozytab/fable5-mode \
  "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode"
bash "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/install.sh"
```

`install.sh` 会**解析自己的位置**（所以不管你 clone 到哪，hook 路径都对）、认
`CLAUDE_CONFIG_DIR`、并把四个 hook **合并**进 `settings.json` 而不破坏已有配置。
它是幂等的——skill 换了位置再跑一次就会重新指向新路径。随时可用
`bash install.sh --uninstall` 移除 hook。

或者直接对 Claude Code 说：

> 按 https://github.com/cozytab/fable5-mode 的 README 帮我安装这个 skill。

**升级**：`git pull` 之后**重跑 `install.sh`**。新版本可能新增 hook 事件（比如
`PostToolUse`），而只有安装脚本会更新你的 `settings.json`——单纯 `git pull` 只更新
文件、不会注册新 hook。脚本幂等，重跑永远安全。

### 方式 B —— 手动

按上面 clone，然后把这四条**合并**进 `<配置目录>/settings.json` 的 `hooks` 对象
（别覆盖文件；已有 `hooks` 键就加进去）。用你实际 clone 的绝对路径——下面的
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}` 会在 hook 运行时由 shell 展开：

```json
"hooks": {
  "SessionStart": [{"hooks": [{"type": "command",
    "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_profile_inject.py"}]}],
  "PreToolUse": [{"matcher": "Agent|Task|Workflow",
    "hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_spawn_guard.py"}]}],
  "PostToolUse": [{"matcher": "Bash",
    "hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_fail_streak.py"}]}],
  "Stop": [{"hooks": [{"type": "command",
    "command": "python3 ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/fable-mode/hooks/fable_close_guard.py"}]}]
}
```

光装 skill 就能靠开口触发 fable-mode；只想要协议就跳过 hook。

### 给 AI 助手：如何安装本项目

当用户让你从本仓安装 fable-mode：

1. 配置目录 = 设了 `$CLAUDE_CONFIG_DIR` 就用它，否则 `~/.claude`。
2. 把仓 `git clone` 到 `<配置目录>/skills/fable-mode`。
3. 跑 `bash <配置目录>/skills/fable-mode/install.sh`——它会幂等合并 hook、自己解析
   路径。若你选择自己改 `settings.json` 注册，务必**合并**进已有 `hooks` 对象（别
   覆盖文件），并用**绝对**的 clone 路径——用户若重定位过配置，别硬编码 `~/.claude`。
4. 告诉用户 hook 是可选的，且在项目有 `.fable/` 目录前一直静默。

## 使用

**点名才触发**——"用 fable 模式""严谨模式"，或英文 "use fable mode"
"work like Fable 5""rigorous mode"。它刻意**不会**因为任务大、任务重要就自动
进入——不搞突然袭击式的流程税；顶多*提议*要不要开。另一条显式路径是项目里有
`.fable/` 目录，hooks 会自动把纪律带进会话。

**开启机械强制**（对你认真对待的项目）：

```bash
mkdir .fable
cat > .fable/LEDGER.md <<'EOF'
- [ ] 1. 第一张卡（带可机器验证的验收）
- [ ] 2. 第二张卡
EOF
```

从此在该项目里：会话自动加载纪律和正确档位；没账本不能派详细 agent；有未勾卡不能
结束回合。把卡标成 `- [x]`（完成并验证）或 `- [~] ... -- deferred: 原因` 来关闭。
想关掉强制：把卡勾完，或 `rm -rf .fable`。

**大项目里的小需求？** 强制是按**轮次**的，不是按键盘的：卡全勾完（空闲态）时守卫
静默、注入近乎为零，小修小改畅通无阻。轮次进行中要临时干别的，在 `.fable/LEDGER.md`
里加一行 `PAUSED: 原因` 即可免打扰（模型天花板仍然生效）；删掉该行恢复轮次。

## 并发分级

fable-mode 的并发不是一个死数字。

- **保守档（默认）** —— 上限 ≤5 个并发 subagent，本机限流护栏。适合日常、额度敏感、
  质量优先的活。
- **高吞吐档（需显式开启）** —— 积极派并行 subagent、异步通信、不阻塞。无固定上限；
  实测部署区间 10–500+。它拿更多 token 换吞吐、并有限流风险——所以只在你明确要求、
  或运行模型本身就是 Fable 5 时才自动启用。

Profile Injector 会按模型自动选档（`FABLE_MODE_PROFILE=auto|conservative|throughput`
可覆盖）。

**模型路由（按能力匹配）**："绝不降级"和"甩给便宜模型"都不对。fable-mode 按卡片
的实际要求路由——设计、调试和**所有验证**留在主会话模型上；规格清晰的实现卡可以降
一档；机械的收集/格式化类活用便宜档 + 低 effort。这正是 Anthropic 自己的做法（他们
的研究系统用 Opus 级 lead + Sonnet 级子 agent，比单 agent 强 90.2%）。让降级变得
安全的是兜底机制：只降验收可机器校验的卡；验收连挂两次就升档——但**封顶于主会话
模型**（阶梯的顶端是收回主上下文攻坚，绝不是去够更强的模型：fable-mode 的意义就是
不用 Fable 5 也拿到 Fable 5 级结果，所以它绝不悄悄向上够）；验证者永远不弱于实现者。
拿不准就继承主会话模型。

## Fable 5 习惯集

在六大杠杆之外，skill 还移植了 Anthropic 官方文档里 Fable 5 的具体行为——让任何
模型进了 fable-mode 项目都继承它们：每条进度汇报先对照工具结果再说；回合绝不停在
一句"我接下来会…"上（能做就当场做掉）；结论先行；只在真正需要用户时才暂停；先评估
再动手；新鲜上下文的验证者优于自我检查；按任务路由模型与 effort（验证永不降级）；派活时把"为什么"一起传下去；维护一份教训
文件。其中价值最高的三条习惯
由 Profile Injector 自动注入每个 fable-mode 会话。

起步骨架在 [`templates/`](templates/)——SPEC、LEDGER、PROGRESS，以及引擎中立的
新鲜视角[验证者提示词](templates/VERIFIER_PROMPT.md)。

**为什么是 skill + hooks，而不是插件或 Agent？** 改成插件只增加分发便利、不增加
任何强制能力，而我们不发布无法端到端验证的形态；"Agent"只能建议、不能拦截。当前
形态一条 clone + 一个脚本装完、且在真机验证过。插件化是"暂缓"，不是"否决"。

## 没有更强的模型？它会降级，绝不卡住

fable-mode 对能力墙很诚实——但"换 Fable 5"对跑不了 Fable 5 的人就是死路。所以
**非 Fable 模型的会话会被自动告知：别把难点甩给更强的模型、也别卡在那儿等一个你
根本运行不了的模型**。它改为在你现有的模型上硬扛过去：把难点拆成更小的可验证步骤、
best-of-N + 裁判、让工具/测试当事实依据、把残留风险如实标注而不是阻塞。如果你**确实**
有更强的档位可以甩活，设 `FABLE_ESCALATION=on`。

## 目录结构

```
fable-mode/
├── SKILL.md              # Claude 读的协议（六大杠杆、分级、红线）
├── README.md             # English
├── README.zh-CN.md       # 本文件
├── install.sh            # 合并/移除 settings.json 里的 hook（自解析路径、幂等）
├── templates/            # SPEC / LEDGER / PROGRESS 骨架 + 新鲜视角验证者提示词
├── hooks/
│   ├── README.md         # hook 机制、账本格式、安装
│   ├── _fable_common.py  # 共用工具（读 stdin、向上找 .fable/、解析账本）
│   ├── fable_profile_inject.py   # SessionStart：按模型选档 + 恢复现场
│   ├── fable_spawn_guard.py      # PreToolUse：设计门禁(需开卡) + 模型天花板
│   ├── fable_fail_streak.py      # PostToolUse(Bash)：失败连击时注入归因阶梯
│   ├── fable_lint.py             # 非 hook：一键纪律体检 CLI
│   └── fable_close_guard.py      # Stop：有开卡/证据空洞 → 拦结束回合
└── tests/
    ├── test_guards.py    # 派发/收尾守卫、模型天花板、PAUSED、证据、失败连击、lint
    ├── test_inject.py    # 按状态注入、档位、模型路由、升级策略
    └── test_install.py   # install.sh：全新/合并/幂等/重指向/卸载
```

## 测试

无第三方依赖：

```bash
python3 tests/test_guards.py    # opt-in 判定、账本有无、豁免、git-root 边界、loop-safety、fail-open
python3 tests/test_inject.py    # 按模型选档、env 覆盖、恢复现场、JSON 信封、fail-open
python3 tests/test_install.py   # install.sh：全新、合并、幂等、重指向、卸载、坏 JSON 拒改
```

## 许可

[MIT](LICENSE) © 2026 cozytab。

可自由使用、复制、修改、合并、发布、分发、再授权乃至出售——含商用，也可用于闭源
项目。**唯一要求**：在所有副本或实质性部分中保留版权声明与 MIT 许可文本（即
`LICENSE` 文件）。按"现状"提供，不含任何担保，作者不承担任何责任。
