# DRIP 量化分析 Agent

> 本 Agent 专注于 A 股量化分析，执行 DRIP 红利再投资蒙特卡洛模拟

---

## 快速索引

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目介绍、使用方法、示例结果 |
| [skills/quant_drip_agent_system.md](skills/quant_drip_agent_system.md) | Agent 系统提示词 |
| [skills/quant-drip-analysis/workflow.md](skills/quant-drip-analysis/workflow.md) | 四阶段工作流 |
| [skills/quant-drip-analysis/reference/formula.md](skills/quant-drip-analysis/reference/formula.md) | 模拟公式与代码 |
| [skills/quant-drip-analysis/reference/diagnosis.md](skills/quant-drip-analysis/reference/diagnosis.md) | 诊断表 |

---

## 快速开始

```bash
python3 agents/quant_pdf.py <股票代码> <股票名称> [模拟年限]

# 示例
python3 agents/quant_pdf.py sh.600900 长江电力 3
```

## 触发词

`分析股票`、`DRIP模拟`、`量化选股`、`股票耦合测试`、`分红股价收敛`、`估值分析`
