#!/usr/bin/env python3
"""
Quant Agent Workflow 完整流程脚本
Phase 1 → Phase 2 → Phase 3 → Phase 4 → PDF

Usage:
    python3 agents/quant_workflow.py <股票代码> <股票名称>
    python3 agents/quant_workflow.py sh.600900 长江电力
"""

import sys
import json
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from scipy.stats import gaussian_kde
import baostock as bs
import matplotlib.font_manager as fm

# ============== 中文字体配置 ==============
# 查找支持中文的系统字体
for font in fm.fontManager.ttflist:
    if 'STHeiti' in font.name or 'Heiti' in font.name or 'PingFang' in font.name:
        print(f"Found font: {font.name} -> {font.fname}")

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['STHeiti', 'PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============== 配置 ==============
STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else 'sh.600900'
STOCK_NAME = sys.argv[2] if len(sys.argv) > 2 else '长江电力'
YEARS = 10
SIMULATIONS = 10000
SIM_YEARS = 3
INITIAL_INVESTMENT = 100000  # 10万

# ============== 工具函数 ==============
def login_baostock():
    lg = bs.login()
    print(f'Baostock: {lg.error_code}')

def logout_baostock():
    bs.logout()

def fetch_price_data(code, years=10):
    """获取日线数据，聚合为年末收盘价"""
    end_date = '2026-03-26'
    start_date = f'{2026-years}-01-01'
    rs = bs.query_history_k_data_plus(
        code, start_date=start_date, end_date=end_date, frequency='d',
        fields='date,code,close'
    )
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    df = pd.DataFrame(data, columns=['date', 'code', 'close'])
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    annual = df.groupby('year')['close'].last().reset_index()
    annual.columns = ['year', 'price']
    return annual

def fetch_dividend_data(code, years=10):
    """获取年度分红数据"""
    all_div = []
    for year in range(2026 - years, 2026):
        rs = bs.query_dividend_data(code=code, year=str(year))
        while rs.error_code == '0' and rs.next():
            row = rs.get_row_data()
            try:
                if len(row) > 9 and row[9] and row[9] != '':
                    div = float(row[9])
                    all_div.append({'year': year, 'dividend': div})
            except:
                pass
    if not all_div:
        return pd.DataFrame(columns=['year', 'dividend'])
    df = pd.DataFrame(all_div)
    annual = df.groupby('year')['dividend'].sum().reset_index()
    return annual

def fetch_pe_data(code, years=10):
    """获取PE数据"""
    end_date = '2026-03-26'
    start_date = f'{2026-years}-01-01'
    rs = bs.query_history_k_data_plus(
        code, start_date=start_date, end_date=end_date, frequency='d',
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
    annual = df.groupby('year')['pe'].mean().reset_index()
    annual.columns = ['year', 'pe']
    return annual

# ============== Phase 1: 数据获取 ==============
def phase1_data_fetch():
    print(f'\n{"="*60}')
    print(f'Phase 1: 数据获取与清洗 - {STOCK_NAME} ({STOCK_CODE})')
    print('='*60)

    login_baostock()

    df_price = fetch_price_data(STOCK_CODE, YEARS)
    df_div = fetch_dividend_data(STOCK_CODE, YEARS)
    df_pe = fetch_pe_data(STOCK_CODE, YEARS)

    print(f'\n📊 价格数据: {len(df_price)} 年')
    print(f'📊 分红数据: {len(df_div)} 年')
    print(f'📊 PE数据: {len(df_pe)} 年')

    logout_baostock()

    return df_price, df_div, df_pe

# ============== Phase 2: 三大拟合测试 ==============
def phase2_analysis(df_price, df_div, df_pe):
    print(f'\n{"="*60}')
    print('Phase 2: 三大拟合测试')
    print('='*60)

    # 合并数据
    merged = df_price.merge(df_div, on='year', how='inner')
    if len(merged) < 3:
        print('❌ 数据不足，无法进行Phase 2分析')
        return None

    prices = merged['price'].values
    dividends = merged['dividend'].values
    n = len(prices)

    # 测试一: CAGR偏离度
    cagr_p = (prices[-1] / prices[0]) ** (1 / (n - 1)) - 1
    cagr_d = (dividends[-1] / dividends[0]) ** (1 / (n - 1)) - 1
    deviation = abs(cagr_p - cagr_d)
    test1_pass = deviation < 0.05

    print(f'\n测试一: CAGR偏离度')
    print(f'  股价CAGR: {cagr_p*100:.2f}%')
    print(f'  分红CAGR: {cagr_d*100:.2f}%')
    print(f'  偏离度: {deviation*100:.2f}%')
    print(f'  结果: {"✅ 通过" if test1_pass else "❌ 未通过"}')

    # 测试二: β与R²
    ln_p = np.log(prices)
    ln_d = np.log(dividends)
    slope, intercept, r_value, _, _ = stats.linregress(ln_d, ln_p)
    beta = slope
    r_squared = r_value ** 2
    test2_pass = r_squared >= 0.6

    print(f'\n测试二: β与R²')
    print(f'  β (弹性系数): {beta:.4f}')
    print(f'  R² (拟合优度): {r_squared:.4f}')
    print(f'  结果: {"✅ 通过" if test2_pass else "❌ 未通过"}')

    # 测试三: Z-score
    pe_data = df_pe['pe'].values
    pe_mean = np.mean(pe_data)
    pe_std = np.std(pe_data)
    current_pe = pe_data[-1]
    z_score = (current_pe - pe_mean) / pe_std if pe_std > 0 else 0
    test3_pass = z_score <= 1.5

    print(f'\n测试三: Z-score')
    print(f'  当前PE: {current_pe:.2f}')
    print(f'  历史均值: {pe_mean:.2f}')
    print(f'  Z-score: {z_score:.2f}')
    print(f'  结果: {"✅ 通过" if test3_pass else "❌ 未通过"}')

    # 波动率
    log_returns = np.diff(np.log(prices))
    sigma = np.std(log_returns)

    return {
        'merged': merged,
        'cagr_p': cagr_p, 'cagr_d': cagr_d, 'deviation': deviation,
        'test1_pass': test1_pass,
        'beta': beta, 'r_squared': r_squared, 'test2_pass': test2_pass,
        'current_pe': current_pe, 'pe_mean': pe_mean, 'pe_std': pe_std,
        'z_score': z_score, 'test3_pass': test3_pass,
        'sigma': sigma,
        'n': n
    }

# ============== Phase 3: 定性判决 ==============
def phase3_verdict(phase2_results):
    print(f'\n{"="*60}')
    print('Phase 3: 定性判决')
    print('='*60)

    t1, t2, t3 = phase2_results['test1_pass'], phase2_results['test2_pass'], phase2_results['test3_pass']
    passed = sum([t1, t2, t3])

    if t1 and t2 and t3:
        verdict = '完美耦合型'
        description = '全盘通过，可进入Phase 4 DRIP模拟'
    elif not t1 and t3:
        verdict = '泡沫假象型'
        description = '未通过测试一、三，股价涨幅脱离分红基本面'
    elif not t1 and not t3 and phase2_results['z_score'] < -1:
        verdict = '估值还债/深坑型'
        description = '未通过测试一，当前极度低估，困境反转标的'
    else:
        verdict = '部分通过'
        description = f'{passed}/3通过，仅供参考'

    print(f'\n🎯 判决: {verdict}')
    print(f'📝 说明: {description}')
    print(f'   测试一(CAGR): {"✅" if t1 else "❌"}')
    print(f'   测试二(β/R²): {"✅" if t2 else "❌"}')
    print(f'   测试三(Z-score): {"✅" if t3 else "❌"}')

    return verdict, description, passed == 3

# ============== Phase 4: DRIP蒙特卡洛模拟 ==============
def phase4_drip_simulation(phase2_results, df_price, df_div):
    print(f'\n{"="*60}')
    print('Phase 4: DRIP蒙特卡洛模拟')
    print('='*60)

    g = phase2_results['cagr_p']  # 股价CAGR作为增长漂移
    sigma = phase2_results['sigma']
    current_price = df_price['price'].values[-1]
    current_div = df_div['dividend'].values[-1] if len(df_div) > 0 else 0
    y = current_div / current_price  # 股息率
    d0 = y * current_price

    print(f'\n📊 模拟参数:')
    print(f'  g (CAGR): {g*100:.2f}%')
    print(f'  σ (波动率): {sigma*100:.2f}%')
    print(f'  Y (股息率): {y*100:.2f}%')
    print(f'  P0 (股价): {current_price:.2f}元')
    print(f'  D0 (分红): {d0:.4f}元')
    print(f'  模拟次数: {SIMULATIONS}')
    print(f'  模拟期限: {SIM_YEARS}年')

    # 蒙特卡洛模拟
    results = []
    initial_shares = INITIAL_INVESTMENT / current_price  # 初始持股数量

    for _ in range(SIMULATIONS):
        p = current_price
        d = d0
        s = initial_shares  # 持股数量

        for _ in range(SIM_YEARS):
            z = np.random.normal(0, 1)
            p = p * np.exp((g - 0.5 * sigma**2) + sigma * z)
            d = d * (1 + g)
            # 分红再投资：收到的分红买入更多股票
            new_shares = (d / p)
            s = s + new_shares

        final_value = s * p
        results.append(final_value / INITIAL_INVESTMENT)

    results = np.array(results)

    # 核心指标
    median = np.median(results)
    double_prob = (results > 2.0).mean()
    loss_prob = (results < 1.0).mean()
    var_5 = np.percentile(results, 5)

    print(f'\n📊 模拟结果:')
    print(f'  中位数: {median:.2f}x')
    print(f'  翻倍概率: {double_prob*100:.1f}%')
    print(f'  亏损概率: {loss_prob*100:.1f}%')
    print(f'  VaR(5%): {var_5:.2f}x')

    return results, {
        'median': median,
        'double_prob': double_prob,
        'loss_prob': loss_prob,
        'var_5': var_5,
        'g': g, 'sigma': sigma, 'y': y, 'p0': current_price, 'd0': d0
    }

# ============== 可视化生成 ==============
def generate_visualizations(df_price, df_div, df_pe, phase2_results, drip_results):
    print(f'\n{"="*60}')
    print('生成可视化图表')
    print('='*60)

    prices = df_price['price'].values
    years = df_price['year'].values
    dividends = df_div['dividend'].values if len(df_div) > 0 else []
    div_years = df_div['year'].values if len(df_div) > 0 else []

    # Chart 1: 股价走势图 + 最大回撤
    print('  生成 Chart 1: 股价走势图...')
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
    ax.set_title(f'{STOCK_NAME} 10年股价走势与最大回撤', fontsize=14, fontweight='bold')
    ax.annotate(f'最大回撤\n{max_dd:.1f}%\n({int(max_dd_year)}年)',
                xy=(max_dd_year, prices[max_dd_idx]),
                xytext=(max_dd_year, prices[max_dd_idx] * 0.7),
                fontsize=9, arrowprops=dict(arrowstyle='->', color='red'), color='red')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'/tmp/{STOCK_NAME}_股价走势图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 2: 分红-股价双轴对数趋势图
    print('  生成 Chart 2: 对数趋势图...')
    if len(df_div) > 0:
        merged = pd.merge(df_price, df_div, on='year', how='inner')
        fig, ax1 = plt.subplots(figsize=(10, 5))
        ax2 = ax1.twinx()
        ax1.plot(merged['year'], np.log(merged['price']), 'o-', color='tab:blue', linewidth=2, label='ln(股价)')
        ax2.plot(merged['year'], np.log(merged['dividend']), 's--', color='tab:red', linewidth=2, label='ln(分红)')
        ax1.set_ylabel('ln(股价)', color='tab:blue')
        ax2.set_ylabel('ln(分红)', color='tab:red')
        ax1.set_xlabel('年份')
        plt.title(f'{STOCK_NAME} 分红-股价对数趋势图 (耦合检验)', fontsize=14, fontweight='bold')
        fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.95))
        ax1.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'/tmp/{STOCK_NAME}_对数趋势图.png', dpi=150, bbox_inches='tight')
        plt.close()

    # Chart 3: 回归散点图
    print('  生成 Chart 3: 回归散点图...')
    if len(df_div) > 0:
        ln_p = np.log(merged['price'].values)
        ln_d = np.log(merged['dividend'].values)
        slope, intercept, r_value, _, _ = stats.linregress(ln_d, ln_p)
        beta = slope
        r_squared = r_value ** 2

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(ln_d, ln_p, s=80, alpha=0.7)
        x_line = np.linspace(ln_d.min(), ln_d.max(), 100)
        ax.plot(x_line, slope * x_line + intercept, 'r-', linewidth=2)
        ax.set_xlabel('ln(分红)')
        ax.set_ylabel('ln(股价)')
        ax.set_title(f'{STOCK_NAME} 分红弹性回归\nβ={beta:.2f}, R²={r_squared:.4f}', fontsize=14, fontweight='bold')
        textstr = f'β (弹性系数) = {beta:.2f}\nR² (拟合优度) = {r_squared:.4f}'
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'/tmp/{STOCK_NAME}_回归散点图.png', dpi=150, bbox_inches='tight')
        plt.close()

    # Chart 4: PE Band通道图
    print('  生成 Chart 4: PE Band图...')
    pe_series = df_pe['pe'].values
    pe_years = df_pe['year'].values
    pe_mean = np.mean(pe_series)
    pe_std = np.std(pe_series)
    current_pe = pe_series[-1]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(pe_years, pe_mean - 2*pe_std, pe_mean + 2*pe_std, alpha=0.15, color='gray', label='±2σ')
    ax.fill_between(pe_years, pe_mean - pe_std, pe_mean + pe_std, alpha=0.25, color='blue', label='±1σ')
    ax.axhline(y=pe_mean, color='green', linestyle='--', linewidth=1.5, label=f'均值={pe_mean:.1f}')
    ax.plot(pe_years, pe_series, 'b-', linewidth=2, marker='o')
    ax.scatter([pe_years[-1]], [current_pe], color='red', s=100, zorder=5, label=f'当前PE={current_pe:.1f}')
    ax.set_xlabel('年份')
    ax.set_ylabel('市盈率 (PE)')
    ax.set_title(f'{STOCK_NAME} 10年PE Band通道图', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'/tmp/{STOCK_NAME}_PE_Band图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 5: DRIP概率分布直方图
    print('  生成 Chart 5: DRIP分布图...')
    results = drip_results
    median = np.median(results)
    var_5 = np.percentile(results, 5)

    fig, ax = plt.subplots(figsize=(10, 6))
    weights = np.ones_like(results) / len(results)
    n, bins, patches = ax.hist(results, bins=50, weights=weights, alpha=0.7, color='steelblue')

    kde = gaussian_kde(results)
    x_kde = np.linspace(results.min(), results.max(), 200)
    ax.plot(x_kde, kde(x_kde), 'r-', linewidth=2, label='KDE密度曲线')

    ax.axvline(x=median, color='gold', linestyle='--', linewidth=2, label=f'中位数 {median:.2f}x')
    ax.axvline(x=var_5, color='red', linestyle=':', linewidth=2, label=f'VaR(5%) {var_5:.2f}x')
    ax.axvline(x=1.0, color='black', linestyle='-', linewidth=1.5, label='盈亏平衡 1.0x')

    for patch, x in zip(patches, bins[:-1]):
        if x < var_5:
            patch.set_facecolor('salmon')

    ax.set_xlabel('最终财富倍数')
    ax.set_ylabel('概率密度')
    ax.set_title(f'{STOCK_NAME} DRIP {SIM_YEARS}年期蒙特卡洛模拟 (n={SIMULATIONS:,})', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    stats_text = (f'中位数: {median:.2f}x\n'
                  f'翻倍概率: {(results > 2.0).mean()*100:.1f}%\n'
                  f'亏损概率: {(results < 1.0).mean()*100:.1f}%\n'
                  f'VaR(5%): {var_5:.2f}x')
    ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(f'/tmp/{STOCK_NAME}_drip_高级分布图.png', dpi=150, bbox_inches='tight')
    plt.close()

    print('  ✅ 所有图表生成完成')

# ============== 主流程 ==============
def main():
    print(f'\n{"="*60}')
    print(f'🚀 Quant Agent Workflow 启动')
    print(f'   股票: {STOCK_NAME} ({STOCK_CODE})')
    print(f'   周期: {YEARS}年')
    print(f'{"="*60}')

    # Phase 1: 数据获取
    df_price, df_div, df_pe = phase1_data_fetch()

    # Phase 2: 三大测试
    phase2_results = phase2_analysis(df_price, df_div, df_pe)

    # Phase 3: 定性判决
    verdict, description, can_proceed = phase3_verdict(phase2_results)

    # Phase 4: DRIP模拟
    drip_results, drip_stats = phase4_drip_simulation(phase2_results, df_price, df_div)

    # 生成可视化
    generate_visualizations(df_price, df_div, df_pe, phase2_results, drip_results)

    print(f'\n{"="*60}')
    print('✅ Workflow 完成!')
    print(f'   图表文件: /tmp/{STOCK_NAME}_*.png')
    print(f'   下一步: 运行 PDF 生成脚本')
    print(f'{"="*60}')

    return {
        'stock_name': STOCK_NAME,
        'stock_code': STOCK_CODE,
        'df_price': df_price,
        'df_div': df_div,
        'df_pe': df_pe,
        'phase2': phase2_results,
        'verdict': verdict,
        'description': description,
        'drip_stats': drip_stats
    }

if __name__ == '__main__':
    main()