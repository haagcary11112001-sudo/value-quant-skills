# 🤖 Agents 开发架构师

> **核心原则**: 封装性 > 堆砌性；触发-执行映射 > 文档罗列

---

## 🎯 从 this 项目学到的设计经验

### 1. 渐进式三级结构

```
SKILL.md (入口) → workflow.md (流程) → reference/ (细节)
```

| 层级 | 内容 | 用户场景 |
|------|------|----------|
| **SKILL.md** | 一句话触发 + 快速示例 | 知道这个 skill 能做什么 |
| **workflow.md** | 完整流程 + 判断逻辑 | 需要执行时参考步骤 |
| **reference/** | 公式、诊断表、故障排查 | 遇到问题时查阅细节 |

**Why:** 用户只需要知道自己该读哪一层，不需要被全部内容淹没。

---

### 2. 标准化的 Agent Prompt 模板

每个子 Agent 的 system prompt 必须包含：

```markdown
# [Agent名称] - 最高指令

> **核心原则**: [一句话总结该 Agent 最核心的目标]

---

## 🏛️ 智能体职责
**我只负责 [核心职责描述]。**

### 🔴 铁律
1. [禁止事项1]
2. [禁止事项2]

### ⚙️ 业务工作流
1. **步骤1** → [具体动作]
2. **步骤2** → [具体动作]

---

## 📚 Skills 读取规则
| 需要时读取 | 文件路径 | 用途 |
|-----------|----------|------|
| xxx | path | xxx |

### 输入变量
| 变量名 | 数据类型 | 处理规则 |
|--------|----------|----------|
| xxx | String | xxx |

---

## 🚀 输出格式约束
{
  "status": "success|error|circuit_broken",
  ...
}
```

**Why:** 标准化确保多 Agent协作时一致性，父 Agent 可以无脑加载。

---

### 3. 熔断 Auto-Fix 机制

```markdown
### 🔴 铁律
- Auto-Fix 上限 5 次：连续失败 5 次自动停止，输出熔断报告

### 🚀 输出格式约束
{
  "status": "circuit_broken",
  "reason": "auto_fix_limit_exceeded",
  "fix_count": 5
}
```

**Why:** 防止 Agent 陷入死循环，报错必须有明确的终止条件。

---

### 4. 判断表优于流程图

| 判决类型 | 条件 |
|---------|------|
| 完美耦合型 | 分红+EPS 双验证全通过 |
| 泡沫假象型 | 未通过任一耦合测试 |

**Why:** 我执行时直接查表，不用在脑子里过一遍冗长文字逻辑。

---

### 5. Skills 是「触发-执行」映射

```
用户: "分析股票 sh.600900"
       ↓
   匹配触发词 → 加载 quant_drip_agent_system.md
       ↓
   执行 Phase 1-4 → 输出 PDF
```

**Skills 索引导航格式：**

```markdown
| Skill | 触发场景 | 说明 |
|-------|----------|------|
| DRIP量化 | A股量化分析、DRIP模拟 | [.../quant_drip_agent_system.md] |
```

**Why:** 用户不需要告诉我怎么做，只需要说目标。

---

### 6. 输入/输出必须类型严格

```json
{
  "stock_code": "sh.600900",  // 必须包含交易所前缀
  "years": 3,                  // int, 范围 1-10
  "pdf_path": "/tmp/..."       // 可选，有默认值
}
```

**Why:** Agent 协作时代码解析不能有二义性，类型错误直接报错而非静默适配。

---

### 7. 职责单一原则

一个 Agent 只做一件事：

| Agent | 职责 |
|-------|------|
| quant-drip-agent | DRIP 量化分析 |
| maker-node | 代码生成 + TDD |
| checker-node | 代码审查 |

**Why:** 职责越单一，复用性越高，组合越灵活。

---

### 8. 金融公式必须与代码严格对应

workflow.md:
```
P_{t+1} = P_t × exp((g - 0.5σ²) + σ × Z)
```

reference/formula.md:
```python
P_next = P_current * np.exp((g - 0.5 * sigma**2) + sigma * Z)
```

**Why:** 不同人实现出来的结果必须一致，不能有解读空间。

---

## 🏗️ 子 Agent 封装检查清单

创建新的子 Agent 时，对照检查：

- [ ] SKILL.md 存在且包含触发词
- [ ] system prompt 包含 Quote / 职责 / 铁律 / 工作流
- [ ] 输入/输出有 JSON Schema 定义
- [ ] 错误处理有熔断机制（上限 5 次）
- [ ] 工作流引用 reference/ 中的公式和诊断表
- [ ] 在父级 CLAUDE.md Skills 索引中注册

---

## 📚 Skills 索引发射窗

| Skill | 路径 |
|-------|------|
| DRIP量化Agent | [skills/quant_drip_agent_system.md](skills/quant_drip_agent_system.md) |
| DRIP工作流 | [skills/quant-drip-analysis/workflow.md](skills/quant-drip-analysis/workflow.md) |
| DRIP诊断表 | [skills/quant-drip-analysis/reference/diagnosis.md](skills/quant-drip-analysis/reference/diagnosis.md) |
| DRIP公式 | [skills/quant-drip-analysis/reference/formula.md](skills/quant-drip-analysis/reference/formula.md) |
