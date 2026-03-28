---
name: quant-drip-analysis
description: A股量化分析工具，评估股票的分红-股价与EPS-股价耦合度，并执行DRIP红利再投资蒙特卡洛模拟。
license: MIT
metadata:
  version: "1.1"
  category: finance-analysis
---

# quant-drip-analysis

**一行命令生成完整 DRIP 分析报告**

## 触发词

"分析股票"、"DRIP模拟"、"量化选股"、"股票耦合测试"、"分红股价收敛"、"估值分析"

## 使用方法

```bash
python3 agents/quant_pdf.py <股票代码> <股票名称> [模拟年限]
```

## 示例

```bash
python3 agents/quant_pdf.py sh.600900 长江电力      # 默认3年
python3 agents/quant_pdf.py sh.600900 长江电力 5   # 5年模拟
python3 agents/quant_pdf.py sz.000921 海信家电 10  # 10年模拟
```

## 输出

- PDF报告：`/tmp/{股票名}_DRIP_分析报告.pdf`
- 7张可视化图表：`/tmp/{股票名}_*.png`

## 文档结构

- [workflow.md](workflow.md) — 完整工作流指南
- [reference/diagnosis.md](reference/diagnosis.md) — 问题诊断表
- [reference/formula.md](reference/formula.md) — 公式与代码
- [reference/troubleshooting.md](reference/troubleshooting.md) — 故障排查
