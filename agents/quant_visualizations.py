#!/usr/bin/env python3
"""
统一可视化脚本: 生成所有5张Quant Workflow图表
Usage: python3 agents/quant_visualizations.py <股票代码> <股票名称>
Example: python3 agents/quant_visualizations.py sh.600900 长江电力
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from scipy.stats import gaussian_kde
import baostock as bs
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

ACCENT = '#E8A020'
DARK = '#1C1C2B'

def login_baostock():
    lg = bs.login()
    print(f'Baostock login: {lg.error_code}')

def logout_baostock():
    bs.logout()

def get_stock_name(stock_code):
    """从股票代码推断名称"""
    names = {
        'sh.600900': '长江电力',
        'sh.600519': '贵州茅台',
        'sz.000333': '美的集团',
        'sh.600887': '伊利股份',
    }
    return names.get(stock_code, stock_code)

def fetch_price_data(stock_code, years=10):
    """获取10年股价数据 (使用日线数据聚合)"""
    end_date = '2026-03-26'
    start_date = f'{2026-years}-01-01'

    rs = bs.query_history_k_data_plus(
        stock_code,
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        fields='date,code,close'
    )

    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    df = pd.DataFrame(data, columns=['date', 'code', 'close'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year

    # 取年末收盘价
    annual = df.groupby('year')['close'].last().reset_index()
    annual.columns = ['year', 'price']
    return annual

def fetch_dividend_data(stock_code, years=10):
    """获取10年分红数据"""
    all_data = []
    current_year = 2026

    for year in range(current_year - years, current_year):
        rs = bs.query_dividend_data(code=stock_code, year=str(year))
        while rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            all_data.append({'year': int(year), 'dividend': row[9] if len(row) > 9 else None})

    df = pd.DataFrame(all_data)
    if len(df) > 0:
        df['dividend'] = pd.to_numeric(df['dividend'], errors='coerce')
        df = df[df['dividend'].notna()].sort_values('year')
    return df

def fetch_pe_data(stock_code, years=10):
    """获取10年PE数据 (使用日线数据聚合)"""
    end_date = '2026-03-26'
    start_date = f'{2026-years}-01-01'

    rs = bs.query_history_k_data_plus(
        stock_code,
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        fields='date,code,peTTM'
    )

    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    df = pd.DataFrame(data, columns=['date', 'code', 'pe'])
    df['pe'] = pd.to_numeric(df['pe'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df = df[df['pe'].notna() & (df['pe'] > 0)]

    # 取年平均PE
    annual = df.groupby('year')['pe'].mean().reset_index()
    annual.columns = ['year', 'pe']
    return annual

def plot_task1_price_chart(df_price, stock_name, save_path):
    """可视化任务1: 10年股价走势图 + 最大回撤"""
    prices = df_price['price'].values
    years = df_price['year'].values

    # 计算最大回撤
    peak = np.maximum.accumulate(prices)
    drawdown = (prices - peak) / peak * 100
    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]
    max_dd_year = years[max_dd_idx]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(years, prices, 'b-', linewidth=2, label='股价')
    ax.fill_between(years, prices, peak, alpha=0.3, color='red', label='回撤区间')

    ax.set_xlabel('年份', fontsize=11)
    ax.set_ylabel('股价 (元)', fontsize=11, color='blue')
    ax.set_title(f'{stock_name} 10年股价走势与最大回撤', fontsize=14, fontweight='bold')

    # 标注最大回撤
    ax.annotate(f'最大回撤\n{max_dd:.1f}%\n({int(max_dd_year)}年)',
                xy=(max_dd_year, prices[max_dd_idx]),
                xytext=(max_dd_year, prices[max_dd_idx] * 0.7),
                fontsize=9,
                arrowprops=dict(arrowstyle='->', color='red'),
                color='red')

    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✅ {save_path}')

def plot_task2_dual_log_chart(df_price, df_div, stock_name, save_path):
    """可视化任务2: 分红-股价双轴对数趋势图"""
    # 合并数据
    merged = pd.merge(df_price[['year', 'price']], df_div[['year', 'dividend']],
                     on='year', how='inner').dropna()

    if len(merged) < 3:
        print(f'  ⚠️ 数据不足，跳过 {save_path}')
        return

    fig, ax1 = plt.subplots(figsize=(10, 5))

    color1 = 'tab:blue'
    ax1.set_xlabel('年份', fontsize=11)
    ax1.set_ylabel('ln(股价)', fontsize=11, color=color1)
    ax1.plot(merged['year'], np.log(merged['price']), 'o-', color=color1, linewidth=2, label='ln(股价)')
    ax1.tick_params(axis='y', labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('ln(分红)', fontsize=11, color=color2)
    ax2.plot(merged['year'], np.log(merged['dividend']), 's--', color=color2, linewidth=2, label='ln(分红)')
    ax2.tick_params(axis='y', labelcolor=color2)

    plt.title(f'{stock_name} 分红-股价对数趋势图 (耦合检验)', fontsize=14, fontweight='bold')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.95))
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✅ {save_path}')

def plot_task3_regression_scatter(df_price, df_div, stock_name, save_path):
    """可视化任务3: 分红弹性回归散点图"""
    merged = pd.merge(df_price[['year', 'price']], df_div[['year', 'dividend']],
                     on='year', how='inner').dropna()

    if len(merged) < 3:
        print(f'  ⚠️ 数据不足，跳过 {save_path}')
        return

    ln_p = np.log(merged['price'].values)
    ln_d = np.log(merged['dividend'].values)

    slope, intercept, r_value, p_value, std_err = stats.linregress(ln_d, ln_p)
    beta = slope
    r_squared = r_value ** 2

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(ln_d, ln_p, s=80, alpha=0.7, label='年度数据')

    x_line = np.linspace(ln_d.min(), ln_d.max(), 100)
    ax.plot(x_line, slope * x_line + intercept, 'r-', linewidth=2,
            label=f'回归线: y = {slope:.2f}x + {intercept:.2f}')

    ax.set_xlabel('ln(分红)', fontsize=11)
    ax.set_ylabel('ln(股价)', fontsize=11)
    ax.set_title(f'{stock_name} 分红弹性回归\nβ={beta:.2f}, R²={r_squared:.4f}', fontsize=14, fontweight='bold')

    textstr = f'β (弹性系数) = {beta:.2f}\nR² (拟合优度) = {r_squared:.4f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)

    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✅ {save_path}')

def plot_task4_pe_band(df_pe, stock_name, save_path):
    """可视化任务4: 10年PE Band通道图"""
    pe_series = df_pe['pe'].values
    years = df_pe['year'].values

    if len(pe_series) < 3:
        print(f'  ⚠️ 数据不足，跳过 {save_path}')
        return

    pe_mean = np.mean(pe_series)
    pe_std = np.std(pe_series)
    current_pe = pe_series[-1]

    fig, ax = plt.subplots(figsize=(10, 5))

    # 通道带
    ax.fill_between(years, pe_mean - 2*pe_std, pe_mean + 2*pe_std, alpha=0.15, color='gray', label='±2σ')
    ax.fill_between(years, pe_mean - pe_std, pe_mean + pe_std, alpha=0.25, color='blue', label='±1σ')
    ax.axhline(y=pe_mean, color='green', linestyle='--', linewidth=1.5, label=f'均值={pe_mean:.1f}')

    # PE曲线
    ax.plot(years, pe_series, 'b-', linewidth=2, marker='o')
    ax.scatter([years[-1]], [current_pe], color='red', s=100, zorder=5, label=f'当前PE={current_pe:.1f}')

    ax.set_xlabel('年份', fontsize=11)
    ax.set_ylabel('市盈率 (PE)', fontsize=11)
    ax.set_title(f'{stock_name} 10年PE Band通道图', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✅ {save_path}')

def plot_task5_drip_distribution(final_values, stock_name, save_path):
    """可视化任务5: DRIP概率分布直方图"""
    results = np.array(final_values)

    fig, ax = plt.subplots(figsize=(10, 6))

    # 直方图
    weights = np.ones_like(results) / len(results)
    n, bins, patches = ax.hist(results, bins=50, weights=weights, alpha=0.7, color='steelblue')

    # KDE曲线
    kde = gaussian_kde(results)
    x_kde = np.linspace(results.min(), results.max(), 200)
    ax.plot(x_kde, kde(x_kde), 'r-', linewidth=2, label='KDE密度曲线')

    # 统计线
    median = np.median(results)
    var_5 = np.percentile(results, 5)

    ax.axvline(x=median, color='gold', linestyle='--', linewidth=2,
               label=f'中位数 {median:.2f}x')
    ax.axvline(x=var_5, color='red', linestyle=':', linewidth=2,
               label=f'VaR(5%) {var_5:.2f}x')
    ax.axvline(x=1.0, color='black', linestyle='-', linewidth=1.5,
               label='盈亏平衡 1.0x')

    # 填充
    for i, (patch, x) in enumerate(zip(patches, bins[:-1])):
        if x < var_5:
            patch.set_facecolor('salmon')

    ax.set_xlabel('最终财富倍数', fontsize=11)
    ax.set_ylabel('概率密度', fontsize=11)
    ax.set_title(f'{stock_name} DRIP 3年期蒙特卡洛模拟 (n=10,000)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # 统计信息
    stats_text = (f'中位数: {median:.2f}x\n'
                  f'翻倍概率: {(results > 2.0).mean()*100:.1f}%\n'
                  f'亏损概率: {(results < 1.0).mean()*100:.1f}%\n'
                  f'VaR(5%): {var_5:.2f}x')
    ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  ✅ {save_path}')

def main(stock_code, stock_name=None):
    if stock_name is None:
        stock_name = get_stock_name(stock_code)

    print(f'\n📊 {stock_name} ({stock_code}) 可视化生成')
    print('=' * 50)

    login_baostock()

    # 生成图表
    save_prefix = f'/tmp/{stock_name}'

    try:
        df_price = fetch_price_data(stock_code, years=10)
        df_div = fetch_dividend_data(stock_code, years=10)
        df_pe = fetch_pe_data(stock_code, years=10)

        if len(df_price) > 0:
            plot_task1_price_chart(df_price, stock_name, f'{save_prefix}_股价走势图.png')

        if len(df_price) > 0 and len(df_div) > 0:
            plot_task2_dual_log_chart(df_price, df_div, stock_name, f'{save_prefix}_对数趋势图.png')
            plot_task3_regression_scatter(df_price, df_div, stock_name, f'{save_prefix}_回归散点图.png')

        if len(df_pe) > 0:
            plot_task4_pe_band(df_pe, stock_name, f'{save_prefix}_PE_Band图.png')

    except Exception as e:
        print(f'  ❌ 图表生成失败: {e}')

    # DRIP分布图需要单独运行模拟，这里跳过
    print('\n💡 如需生成DRIP分布图，请运行 Phase 4 模拟脚本')

    logout_baostock()
    print('\n✅ 可视化任务完成!')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    stock_code = sys.argv[1]
    stock_name = sys.argv[2] if len(sys.argv) > 2 else None
    main(stock_code, stock_name)