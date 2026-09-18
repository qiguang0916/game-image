# game-image

**Game Image Director / Execution Harness**：给 ChatGPT / Codex 的游戏图片生产控制层。

它不在本地跑图片模型，也不要求 ComfyUI。它把图片需求变成一个有 Master、有明确 edit target、有 Reference Role、有 QA、有状态、有返工上限的生产闭环。

## v0.3 核心变化：Host Action Protocol

v0.2 已经有状态机，但 Agent 仍需要自己解释“下一步具体做什么”。

v0.3 增加 **Host Action Packet**：

~~~text
Run State
   ↓
next_action.py
   ↓
JSON Host Action Packet
   ↓
Codex / Agent
   ├─ imagegen_generate
   ├─ imagegen_edit
   ├─ visual_qa
   ├─ deliver
   └─ report_blocked
~~~

Packet 会明确提供：

- 这一步是生成还是编辑；
- **真正的 edit target 是哪张图**；
- 哪些图只是辅助 reference；
- 每张 reference 的 role；
- 最终 authoritative prompt；
- QA hard / soft gates；
- 下一步如何更新状态。

## 完整工作流

~~~text
用户要求
  ↓
Game Image Director
  ↓
Master / Reference Atlas
  ↓
明确 Edit Target
  ↓
Reference Role + Priority
  ↓
Geometry / Material / Camera Locks
  ↓
Execution Run
  ↓
Host Action Packet
  ↓
官方 $imagegen / 宿主内置图片能力
  ↓
实际生成/编辑结果
  ↓
Host Action Packet: visual_qa
  ↓
Visual QA
  ├─ PASS → ACCEPTED → deliver
  ├─ REPAIR_MINOR → Failed Result 做 edit target → 再编辑
  ├─ REGENERATE_MAJOR → 回 Approved Master → 重做
  └─ BLOCKED → 停止并说明限制
~~~

## 为什么不需要 ComfyUI

`game-image` 是 backend-neutral 的监督层：

- 不要求 CUDA
- 不要求 Stable Diffusion / FLUX 权重
- 不要求本地 GPU
- 不内置 OpenAI API 客户端
- OpenAI/Codex 环境优先委托官方 `$imagegen` built-in image tool

底层图片模型升级，不需要重写 Master / Lock / QA / Loop。

## 当前能力

- Game Image Director
- Asset Reference / Reference Atlas
- Reference Role / Priority
- **Explicit Edit Target**
- Geometry Lock
- Material Lock
- Camera Lock
- Delta Edit
- Edit vs Regenerate
- Visual QA
- Hard / Soft Acceptance Gates
- Brief Compiler
- Repair Brief Compiler
- Execution State Machine
- **Host Action Packet Compiler**
- Repair / Regeneration 次数上限
- KNIFE_001 示例
- **完整 E2E dry-run**
- GitHub Actions 自动验证

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
  openai-imagegen-delegation.md
  host-action-protocol.md
templates/
scripts/
  validate_project.py
  compile_brief.py
  compile_repair.py
  execution_loop.py
  next_action.py
  demo_e2e.py
examples/
  KNIFE_001/
tests/
~~~

## 使用

### 1. 初始化 run

~~~bash
python3 scripts/execution_loop.py init \
  --asset examples/KNIFE_001/asset.toml \
  --edit examples/KNIFE_001/edits/rivets-brushed-silver.toml \
  --output .game-image/runs/KNIFE_001_RIVETS.json
~~~

### 2. 获取下一步

~~~bash
python3 scripts/next_action.py \
  --asset examples/KNIFE_001/asset.toml \
  --edit examples/KNIFE_001/edits/rivets-brushed-silver.toml \
  --run .game-image/runs/KNIFE_001_RIVETS.json
~~~

初始 Packet 会类似：

~~~json
{
  "action": "imagegen_edit",
  "edit_target": {
    "reference_id": "ASSEMBLED_MASTER",
    "path": "references/KNIFE_001_ASSEMBLED_MASTER.png"
  },
  "references": [
    {
      "reference_id": "ASSEMBLED_MASTER",
      "roles": ["identity", "material", "color", "camera"]
    },
    {
      "reference_id": "HANDLE_L_OUTER_MASTER",
      "roles": ["geometry", "silhouette", "part_layout", "material"]
    }
  ]
}
~~~

这意味着：

**ASSEMBLED_MASTER 是被编辑的原图；HANDLE_L_OUTER_MASTER 只是辅助参考。**

### 3. Host 执行 Image

Codex / Agent 根据 Packet 调用 `$imagegen`。

结果保存后：

~~~bash
python3 scripts/execution_loop.py mark-generated \
  --run .game-image/runs/KNIFE_001_RIVETS.json \
  --result assets/generated/KNIFE_001_rivets_v1.png
~~~

### 4. 再次获取下一步

现在 Packet 会变为：

~~~text
action = visual_qa
~~~

里面已经包含：

- result_path
- comparison references
- requested change
- hard gates
- soft gates

Agent 实际看图，写 QA TOML。

### 5. Apply QA

~~~bash
python3 scripts/execution_loop.py apply-qa \
  --run .game-image/runs/KNIFE_001_RIVETS.json \
  --qa path/to/qa.toml
~~~

然后继续调用 `next_action.py`。

不需要 Agent 自己重新规划整个流程。

## Repair

如果 QA = `REPAIR_MINOR`：

~~~text
edit_target = 上一轮失败的生成结果
prompt = Correction Delta
~~~

只修失败 gate。

## Regenerate

如果 QA = `REGENERATE_MAJOR`：

~~~text
edit_target = 原 Approved Master
restart_policy = approved_source_not_failed_result
~~~

防止在坏图上反复叠错。

## 循环上限

默认：

~~~text
max_repair_passes = 2
max_regeneration_passes = 1
~~~

超限进入 `BLOCKED`。

## E2E Dry Run

不调用图片模型也能验证完整 Harness 路由：

~~~bash
python3 scripts/demo_e2e.py
~~~

预期：

~~~text
1 READY -> imagegen_edit
2 QA_PENDING -> visual_qa
3 REPAIR_READY -> imagegen_edit(failed result)
4 QA_PENDING -> visual_qa
5 ACCEPTED -> deliver
E2E DRY RUN PASS
~~~

## 自动验证

~~~bash
python3 scripts/validate_project.py
python3 -m unittest discover -s tests -v
python3 scripts/demo_e2e.py
~~~

GitHub Actions 在 push / PR 自动运行三项。

## 当前定位

v0.3 已经把“规则 + 状态机”进一步变成了**Codex 可消费的机器协议**。

下一阶段是真实 Host E2E：

> 在安装了 `game-image` 且能用 `$imagegen` 的 Codex/Agent 环境，放入真实 Master Reference 图片，运行一次真实图片编辑 → QA → Repair → PASS。

完成后即可进入 v1.0 收口，以及和 AI 3D Game Harness 对接。
