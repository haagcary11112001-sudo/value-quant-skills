# 公式与代码模式

## 波动率计算

```python
σ = std(ln(P_t / P_{t-1}))  # 历史对数收益率标准差
```

## DRIP模拟参数

| 参数 | 计算方法 | 含义 |
|------|---------|------|
| g | 过去10年股价CAGR | 长期均值漂移 |
| σ | std(ln(P_t / P_{t-1})) | 年波动率 |
| Y | 最新一期 D / 最新一期 P | 初始股息率 |
| D0 | Y × P0 | 初始绝对分红额 |

## DRIP核心公式 (每年迭代)

1. **股价随机游走**：P_{t+1} = P_t × exp((g - 0.5σ²) + σ × Z)
2. **绝对分红增长**：D_{t+1} = D_t × (1 + g)
3. **动态红利再投资**：S_{t+1} = S_t × (1 + D_{t+1} / P_{t+1})

## 可视化代码模式

### 最大回撤图

```python
peak = np.maximum.accumulate(prices)
drawdown = (prices - peak) / peak * 100
max_dd_idx = np.argmin(drawdown)
plt.fill_between(years, prices, peak, alpha=0.3, color='red')
```

### PE Band图

```python
pe_mean = np.mean(pe_series)
pe_std = np.std(pe_series)
plt.fill_between(years, pe_mean-2*pe_std, pe_mean+2*pe_std, alpha=0.2, color='gray')
plt.fill_between(years, pe_mean-pe_std, pe_mean+pe_std, alpha=0.3, color='blue')
plt.axhline(y=pe_mean, color='green', linestyle='--')
plt.scatter([current_year], [current_pe], color='red', s=100, zorder=5)
```

### DRIP概率分布图

```python
from scipy.stats import gaussian_kde
weights = np.ones_like(results) / len(results)
n, bins, patches = plt.hist(results, bins=50, weights=weights, alpha=0.7)
kde = gaussian_kde(results)
x_kde = np.linspace(results.min(), results.max(), 200)
plt.plot(x_kde, kde(x_kde), 'r-', linewidth=2)
plt.axvline(x=np.median(results), color='gold', linestyle='--', label=f'中位数 {np.median(results):.2f}x')
plt.axvline(x=np.percentile(results, 5), color='red', linestyle=':', label=f'VaR(5%) {np.percentile(results,5):.2f}x')
plt.axvline(x=1.0, color='black', linestyle='-', linewidth=1.5, label='盈亏平衡 1.0x')
```
