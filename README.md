# value-quant-skills

A股量化分析工具 — 业绩-股价收敛测试与 DRIP 红利再投资蒙特卡洛模拟

[![GitHub release](https://img.shields.io/github/v/release/haagcary11112001-sudo/value-quant-skills)](https://github.com/haagcary11112001-sudo/value-quant-skills/releases)

## 功能特性

- **四阶段量化分析**：数据获取 → 双耦合验证 → 估值健康度 → DRIP 模拟
- **双耦合验证**：同时检验分红-股价、EPS-股价耦合度
- **Cook's Distance 极端值剔除**：自动识别并剔除对拟合影响最大的异常年份
- **蒙特卡洛模拟**：10,000 次模拟，预测 DRIP 策略收益分布
- **一键 PDF 报告**：自动生成 7 张可视化图表 + 完整分析报告，结论前置显示

---

## 安装到 Claude Code

在 Claude Code 中告诉你的 Agent：

```
请读取并使用 skills/quant-drip-analysis/ 中的 quant-drip-analysis skill 来分析股票。
这个技能的触发词是：分析股票、DRIP模拟、量化选股、股票耦合测试、分红股价收敛、估值分析。
```

或者手动安装到本地 skills 目录：

```bash
# 克隆到本地 skills 目录
git clone https://github.com/haagcary11112001-sudo/value-quant-skills.git /path/to/your/skills/quant-drip-analysis
```

---

## 使用方法

### 方式一：告诉 Claude Code 分析股票

在 Claude Code 中输入以下任一触发词：

```
分析股票 sh.600900 长江电力
DRIP模拟 sh.600900 长江电力 5
量化选股 长江电力
股票耦合测试 sh.600900
分红股价收敛 长江电力
估值分析 sh.600900 长江电力 3
```

### 方式二：手动运行脚本

```bash
python3 agents/quant_pdf.py <股票代码> <股票名称> [模拟年限]

# 示例
python3 agents/quant_pdf.py sh.600900 长江电力      # 默认3年
python3 agents/quant_pdf.py sh.600900 长江电力 5   # 5年模拟
python3 agents/quant_pdf.py sz.000921 海信家电 10  # 10年模拟
```

---

## 输出

- PDF 报告：`/tmp/{股票名}_DRIP_分析报告.pdf`
- 7 张可视化图表：`/tmp/{股票名}_*.png`

---

## 核心原理：为什么关注耦合？

股价与基本面的耦合是价值投资的基石。如果一家公司业绩增长但股价不涨，或者股价涨了但业绩没跟上，那么投资逻辑就是空中楼阁。

**本工具验证两种典型的业绩-股价耦合模式。**

### 分红耦合型

- **特征**：公司业绩良好但初期少分红，随着分红增加，股价同步上涨
- **逻辑**：分红是股东回报的直接体现，分红增长 → 股价增长
- **典型标的**：成熟型水电企业、基建类、REITs 等刚性需求资产
- **金融含义**：分红释放管理层对股东回报的诚意，是最实在的价值信号

### EPS耦合型

- **特征**：公司分红少或不稳定，但投资者更看重每股收益（EPS）增长
- **逻辑**：EPS 反映盈利能力，盈利增长 → 股价上涨
- **典型标的**：成长型公司、周期行业中 EPS 领先分红的标的
- **金融含义**：盈利是分红的来源，高 EPS 但低分红可能意味着资金被高效再投资

---

## 分析流程

### Phase 1: 数据获取

从 baostock 获取 10 年历史数据：股价、分红、EPS、PE

### Phase 2: 双耦合验证

| 测试 | 标准 | 含义 |
|------|------|------|
| 分红 CAGR 偏离度 | \|CAGR_P - CAGR_D\| < 5% | 股价与分红增长同步性 |
| EPS CAGR 偏离度 | \|CAGR_P - CAGR_EPS\| < 5% | 股价与盈利增长同步性 |
| 分红 R² 回归 | R² ≥ 0.6 | 分红对股价的解释力 |
| EPS R² 回归 | R² ≥ 0.6 | EPS 对股价的解释力 |
| Z-score | Z ≤ 1.5 | 当前估值在历史中的位置 |

**通过条件**：
- 任一耦合（分红或EPS）通过 + R² 达标 → 进入 DRIP 模拟
- 均未通过 → 判定为"泡沫假象型"，不执行 DRIP 模拟

**极端值处理（Cook's Distance）**：
- 首次拟合不通过 → 计算 Cook's Distance，剔除影响最大的点
- 剔除阈值：4/n（n=样本数），超过此值视为强影响点
- 剔除上限：10年最多删2年，5年最多删1年，少于5年不得删除
- 剔除后重新计算 CAGR 和 R²

### Phase 3: 定性判决

| 判决类型 | 条件 | 含义 |
|---------|------|------|
| 完美耦合型 | 分红+EPS 双验证全通过 | 业绩与股价完美锁定，DRIP 策略高度适配 |
| 分红耦合型 | 仅分红耦合通过 | 股东回报与股价同步，适合收息型投资者 |
| EPS 耦合型 | 仅 EPS 耦合通过 | 盈利驱动股价，DRIP 效果依赖股价稳定性 |
| 泡沫假象型 | 未通过任一耦合测试 | 股价定价脱离基本面，DRIP 效果存疑 |
| 估值还债/深坑型 | 未通过 CAGR 测试，当前极度低估 | 历史高估值正在消化，困境反转标的 |
| 部分通过 | 未通过 Z-score 等条件 | 多项测试未通过，需谨慎评估 |

### Phase 4: DRIP 模拟

**执行条件**：Phase 2 任一耦合通过

**模拟参数**：
- g = 过去 10 年股价 CAGR（均值漂移）
- σ = 历史对数收益率标准差（波动率）
- Y = 最新股息率（初始）
- D₀ = Y × P₀（初始绝对分红额）

**模拟设置**：
- 模拟次数：10,000 次
- 模拟期限：3-10 年（可自定义）
- 初始投入：10 万元

**核心公式（每年迭代）**：
1. 股价随机游走：P_{t+1} = P_t × exp((g - 0.5σ²) + σ × Z)
2. 绝对分红增长：D_{t+1} = D_t × (1 + g)
3. 动态红利再投资：S_{t+1} = S_t × (1 + D_{t+1} / P_{t+1})

**输出指标**：
| 指标 | 含义 |
|------|------|
| 中位数 | 第 5000 名的现实预期（50% 概率高于此值） |
| 翻倍概率 | 最终财富 > 2.0 的比例 |
| 亏损概率 | 最终财富 < 1.0 的比例 |
| VaR(5%) | 极端回撤底线 |

---

## 示例结果

### 长江电力 (sh.600900) — 完美耦合型

```
分红耦合：CAGR 偏离 1.13%，R²=0.84 ✅
EPS 耦合：CAGR 偏离 4.95%，R²=0.65 ✅
Z-score：Z=-0.13 ✅
判决：完美耦合型
3年 DRIP 中位数：1.28x
```

### 海信家电 (sz.000921) — EPS耦合型

```
分红耦合：CAGR 偏离 18.35%，R²=0.91 ✅（Cook's D剔除1个极端值后）
EPS 耦合：CAGR 偏离 3.20% ✅，R²=0.80 ✅（Cook's D剔除1个极端值后）
Z-score：Z=-0.91 ✅
判决：EPS耦合型
3年 DRIP 中位数：1.17x（高波动 σ=35.89%）
```

---

## 项目结构

```
├── README.md                              # 本文件
├── CLAUDE.md                              # Agent 系统指令
├── agents/
│   ├── quant_pdf.py                      # 主分析脚本
│   ├── phase1_data_fetch*.py             # 数据获取
│   └── phase2_analysis.py                # 耦合验证
└── skills/quant-drip-analysis/           # 可安装技能包
    ├── SKILL.md                          # 技能入口
    ├── workflow.md                       # 详细工作流
    └── reference/                        # 参考文档
        ├── diagnosis.md                  # 诊断表
        ├── formula.md                    # 公式与代码
        └── troubleshooting.md           # 故障排查
```

---

## 安装依赖

```bash
pip install baostock matplotlib scipy numpy pandas
```

---

## 技术栈

- **数据源**：baostock（A 股）
- **语言**：Python 3.9+
- **可视化**：matplotlib
- **统计分析**：scipy, numpy, pandas
- **PDF 生成**：minimax-pdf skill

---

## 免责声明

本工具仅供学习研究，不构成投资建议。股市有风险，投资需谨慎。
