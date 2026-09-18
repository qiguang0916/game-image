# game-image

**Game Image Director / Execution Harness**：给 ChatGPT / Codex 的游戏图片生产控制层。

它不在本地跑图片模型，也不要求 ComfyUI。它负责把一个图片需求变成有 Master、有约束、有状态、有 QA、有返工上限的生产流程。

## v0.2 工作流

~~~text
用户要求
  ↓
Game Image Director
  ↓
Master / Reference Atlas
  ↓
Reference Role + Priority
  ↓
Geometry / Material / Camera Locks
  ↓
Delta Brief Compiler
  ↓
官方 $imagegen / 宿主内置图片能力
  ↓
实际生成/编辑结果
  ↓
Visual QA
  ├─ PASS → ACCEPTED
  ├─ REPAIR_MINOR → Correction Delta → 再编辑
  ├─ REGENERATE_MAJOR → 回到 Approved Master 重做
  └─ BLOCKED → 停止并说明限制
~~~

## 为什么不需要 ComfyUI

`game-image` 是 backend-neutral 的监督层：

- 不要求 CUDA
- 不要求 Stable Diffusion / FLUX 权重
- 不要求本地 GPU
- 不内置 OpenAI API 客户端
- 正常使用 OpenAI/Codex 时优先委托官方 `$imagegen` 的 built-in image tool

这样底层图片模型升级时，Game Image 的 Master / Lock / QA / Loop 逻辑不需要重写。

## 现在已经有的能力

- Game Image Director 主 Skill
- Asset Reference / Master Reference / Reference Atlas
- Reference Role / Priority
- Geometry Lock
- Material Lock
- Camera Lock
- Delta Edit
- Edit vs Regenerate 路由
- Visual QA
- Hard / Soft Acceptance Gates
- Brief Compiler
- Repair Brief Compiler
- Execution State Machine
- Repair / Regeneration 次数上限
- KNIFE_001 Hero Prop 示例
- GitHub Actions + Python 单元测试

## 目录

~~~text
SKILL.md
skills/
  asset-reference/
  delta-edit/
  visual-qa/
  execution-loop/
rules/
references/
templates/
scripts/
  validate_project.py
  compile_brief.py
  compile_repair.py
  execution_loop.py
examples/
  KNIFE_001/
tests/
~~~

## 1. 编译原始图片 Brief

~~~bash
python3 scripts/compile_brief.py \
  examples/KNIFE_001/asset.toml \
  examples/KNIFE_001/edits/rivets-brushed-silver.toml
~~~

它会合并：

- Asset 级 Hard / Soft Locks
- 当前 Edit Preserve
- Reference Role
- 输出用途
- Local Edit 的 no-redesign 边界

## 2. 初始化执行状态

~~~bash
python3 scripts/execution_loop.py init \
  --asset examples/KNIFE_001/asset.toml \
  --edit examples/KNIFE_001/edits/rivets-brushed-silver.toml \
  --output .game-image/runs/KNIFE_001_RIVETS.json
~~~

对于 KNIFE_001 的局部编辑，初始状态类似：

~~~text
READY
next_action = invoke_imagegen_edit
~~~

## 3. Image 执行

在支持 OpenAI/Codex 系统 `imagegen` 的宿主中：

- `game-image` 负责准备最终 Brief 和参考图职责；
- `$imagegen` 负责实际生成/编辑；
- project-bound 输出保存到工作区之后再进入 QA。

详见 `references/openai-imagegen-delegation.md`。

## 4. 记录结果

~~~bash
python3 scripts/execution_loop.py mark-generated \
  --run .game-image/runs/KNIFE_001_RIVETS.json \
  --result assets/generated/KNIFE_001_rivets_v1.png
~~~

状态进入：

~~~text
QA_PENDING
~~~

## 5. Visual QA

必须查看真实生成图，不允许根据 Prompt 猜测。

QA 使用：

~~~text
PASS
PASS_WITH_NOTES
REPAIR_MINOR
REGENERATE_MAJOR
BLOCKED
~~~

然后：

~~~bash
python3 scripts/execution_loop.py apply-qa \
  --run .game-image/runs/KNIFE_001_RIVETS.json \
  --qa path/to/qa-report.toml
~~~

## 6. 自动返工路由

### REPAIR_MINOR

进入：

~~~text
REPAIR_READY
~~~

编译最小修正指令：

~~~bash
python3 scripts/compile_repair.py \
  examples/KNIFE_001/asset.toml \
  examples/KNIFE_001/edits/rivets-brushed-silver.toml \
  path/to/qa-report.toml
~~~

以失败结果为 edit target，只修失败 gate。

### REGENERATE_MAJOR

进入：

~~~text
REGENERATE_READY
~~~

不继续在坏图上叠修改，而是回到 Approved Master / 原始 edit target，重新执行原始 Brief。

## 循环上限

默认：

~~~text
max_repair_passes = 2
max_regeneration_passes = 1
~~~

超过预算：

~~~text
BLOCKED
~~~

不允许无限“越修越坏”。

## 验证

Python 3.11+，核心脚本仅使用标准库：

~~~bash
python3 scripts/validate_project.py
python3 -m unittest discover -s tests -v
~~~

GitHub Actions 会在 push / PR 自动执行同一套验证。

## 当前定位

v0.2 已经把 v0.1 的“规则系统”升级成**可执行状态机**。

下一阶段重点不是再加 Prompt，而是：

- 在真实支持 `$imagegen` 的 Codex/Agent 环境跑端到端图片案例；
- 自动生成 QA TOML；
- 把最终通过的 Master 接入 Blender / 3D Harness。

## Upstream ideas

本项目为原创实现，但设计上参考了公开项目中的通用思想：

- `waterblower/Omni-Art-Skills`：美术指导、参考图管理、图片质检、生成计划。
- `ybuild-ai/ai-game-art-pipeline-skill`：provider-neutral 游戏美术生产与 QA。
- OpenAI 官方 `imagegen` Skill：作为 OpenAI/Codex 环境的图片执行层，而不是复制其实现。

详见 `ACKNOWLEDGEMENTS.md`。
