# game-image

面向游戏资产的 AI 图片导演 / 参考图一致性 / 局部编辑 / Visual QA Skill。

目标不是替代图片模型，而是把“随缘生图”变成一条可控生产链：

```text
Request
  -> classify create / edit / repair / variant
  -> select approved references
  -> compile CHANGE + PRESERVE + locks
  -> generate/edit with the available image backend
  -> inspect actual output
  -> visual QA
  -> accept / surgical repair / regenerate
```

## 适合什么

- 游戏 Hero Prop / 道具 Master Reference
- 角色、环境、UI、图标等需要长期一致性的游戏美术资产
- 多参考图职责分离
- 局部材质、颜色、零件修改
- Blender / Unity / Unreal 建模前的参考图生产
- 不希望因为改一个局部而让整个资产“跑形”的工作流

## 不需要什么

- 不要求 ComfyUI
- 不要求本地 Stable Diffusion / FLUX
- 不要求本地 GPU 生图环境

本仓库是 **backend-neutral** 的控制层。Agent 可以接入其当前可用的 ChatGPT Image、OpenAI image generation/editing tool，或其它云端图片后端。

## 核心组件

- [SKILL.md](SKILL.md) — 总入口 / Game Image Director
- [Asset Reference](skills/asset-reference/SKILL.md) — Master Reference 与 Reference Atlas
- [Delta Edit](skills/delta-edit/SKILL.md) — 最小修改、Edit vs Regenerate
- [Visual QA](skills/visual-qa/SKILL.md) — 游戏资产硬门禁与修正指令
- [Rules](rules/) — Geometry / Material / Camera / Reference / Acceptance Gates
- [Templates](templates/) — TOML 结构化任务模板
- [KNIFE_001 Example](examples/KNIFE_001/) — 3D Hero Prop 工作示例

## 设计原则

1. **Approved master wins.** 已确认 Master 的优先级高于临时图、草图和模型自行猜测。
2. **One reference, one declared job.** 每张参考图必须声明它负责什么。
3. **Delta-only edits.** 局部修改只描述变化，不重新设计整个资产。
4. **Hard invariants are gates, not suggestions.** 几何、轮廓、零件位置、相机等硬约束失败即拒收。
5. **Inspect pixels before accepting.** 不根据 prompt 猜结果；必须查看真实生成图后再 QA。
6. **Repair surgically.** 构图和身份正确时优先定向修复；只有核心结构错误才重生。
7. **Provider neutral.** 不把流程绑死在某一个模型或 API。

## 快速使用

把本仓库作为一个 Agent Skill 目录加载后，可以直接描述任务：

```text
基于 KNIFE_001_ASSEMBLED_MASTER，
只把三个柳钉改成轻微拉丝的冷银灰钢材质。
保持刀身、木柄轮廓、Pin 中心、挡片、相机、光照和背景不变。
```

Director 应先读取资产清单和参考图职责，再编译成：

```text
OPERATION: local_edit
TARGET: three existing rivets

CHANGE:
- finish -> subtle brushed cold-silver steel

HARD PRESERVE:
- blade geometry
- handle silhouette
- rivet centers
- part count
- camera/projection

SOFT PRESERVE:
- wood tone and grain
- lighting
- background
```

生成后必须经过 Visual QA；如果硬门禁失败，不应直接交付。

## 本地验证

仓库中的验证器只检查结构化配置，不调用任何图片模型：

```bash
python3 scripts/validate_project.py
python3 -m unittest discover -s tests -v
```

Python 3.11+，仅使用标准库。

## 项目状态

当前目标：v0.1 — 先把游戏资产参考图生产闭环跑通，再接入更大的 2D Reference -> Blender -> Unity/Unreal Harness。

## Upstream ideas

本项目为原创实现，但设计上参考了以下公开项目中的通用思想：

- `waterblower/Omni-Art-Skills`：美术指导、参考图管理、图片质检、生成计划（相关 Skill 标注 MIT）
- `ybuild-ai/ai-game-art-pipeline-skill`：provider-neutral 游戏美术生产与 QA（MIT）

详见 [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md)。
