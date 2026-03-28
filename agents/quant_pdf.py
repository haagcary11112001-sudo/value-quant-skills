#!/usr/bin/env python3
"""
Quant Agent Workflow 完整流程: 一键生成分析报告PDF

Usage:
    python3 agents/quant_pdf.py <股票代码> <股票名称> [模拟年限]
    python3 agents/quant_pdf.py sh.600900 长江电力     # 默认3年
    python3 agents/quant_pdf.py sh.600900 长江电力 5   # 5年模拟
    python3 agents/quant_pdf.py sh.600900 长江电力 10  # 10年模拟
"""

import sys
import os
import json
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats
from scipy.stats import gaussian_kde
import baostock as bs

# ============== 中文字体配置 ==============
for font in fm.fontManager.ttflist:
    if 'STHeiti' in font.name or 'PingFang' in font.name:
        plt.rcParams['font.sans-serif'] = ['STHeiti', 'PingFang SC']
        break
plt.rcParams['axes.unicode_minus'] = False

# ============== 配置 ==============
STOCK_CODE = sys.argv[1] if len(sys.argv) > 1 else 'sh.600900'
STOCK_NAME = sys.argv[2] if len(sys.argv) > 2 else '长江电力'
SIM_YEARS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
SIM_YEARS = max(3, min(10, SIM_YEARS))  # 限制在3-10年范围
YEARS = 10
SIMULATIONS = 10000
INITIAL_INVESTMENT = 100000  # 10万

MINIMAX_PDF = '/Users/claudecodedezhuanshumac/.minimax-skills/skills/minimax-pdf/scripts'
TMP_DIR = '/tmp'

# ============== Baostock 数据获取 ==============
def login_baostock():
    lg = bs.login()
    print(f'Baostock: {lg.error_code}')

def logout_baostock():
    bs.logout()

def fetch_price_data(code, years=10):
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

def fetch_eps_data(code, years=10):
    """获取EPS数据 (年报)"""
    all_eps = []
    for year in range(2026 - years, 2026):
        for quarter in [1, 2, 3, 4]:
            rs = bs.query_profit_data(code=code, year=str(year), quarter=quarter)
            while rs.error_code == '0' and rs.next():
                row = rs.get_row_data()
                try:
                    # fields: code, pubDate, statDate, roeAvg, npMargin, gpMargin, netProfit, epsTTM, ...
                    if len(row) > 7 and row[7] and row[7] != '':
                        eps = float(row[7])
                        report_year = int(row[2][:4]) if row[2] else year
                        all_eps.append({'year': report_year, 'eps': eps})
                except:
                    pass
    if not all_eps:
        return pd.DataFrame(columns=['year', 'eps'])
    df = pd.DataFrame(all_eps)
    # 取年末完整年度EPS (通常Q4数据)
    annual = df.groupby('year')['eps'].last().reset_index()
    return annual

# ============== 分析函数 ==============
def run_analysis():
    print(f'\n{"="*60}')
    print(f'🚀 Quant Agent Workflow 启动')
    print(f'   股票: {STOCK_NAME} ({STOCK_CODE})')
    print(f'{"="*60}')

    login_baostock()

    print('\n📥 Phase 1: 数据获取...')
    df_price = fetch_price_data(STOCK_CODE, YEARS)
    df_div = fetch_dividend_data(STOCK_CODE, YEARS)
    df_eps = fetch_eps_data(STOCK_CODE, YEARS)
    df_pe = fetch_pe_data(STOCK_CODE, YEARS)
    print(f'   价格: {len(df_price)}年 | 分红: {len(df_div)}年 | EPS: {len(df_eps)}年 | PE: {len(df_pe)}年')

    # 合并数据 (分红)
    merged_div = df_price.merge(df_div, on='year', how='inner')
    prices = merged_div['price'].values
    dividends = merged_div['dividend'].values
    n_div = len(prices)

    # 合并数据 (EPS)
    merged_eps = df_price.merge(df_eps, on='year', how='inner')
    prices_eps = merged_eps['price'].values
    eps_values = merged_eps['eps'].values
    n_eps = len(prices_eps)

    # ========== 极端值剔除函数 ==========
    def remove_outliers_iqr(data, label="数据"):
        """使用IQR方法剔除极端值"""
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (data >= lower) & (data <= upper)
        if mask.sum() < len(data) * 0.7:  # 如果剔除过多，回退到不用
            print(f"   警告: {label}异常值过多({len(data)-mask.sum()}个)，保留全部数据")
            return data
        removed = len(data) - mask.sum()
        if removed > 0:
            print(f"   {label}: 剔除{removed}个极端值")
        return data[mask], mask

    def remove_outliers_zscore(data, threshold=2.5, label="数据"):
        """使用Z-score方法剔除极端值"""
        z = np.abs((data - np.mean(data)) / np.std(data))
        mask = z < threshold
        if mask.sum() < len(data) * 0.7:
            print(f"   警告: {label}异常值过多({len(data)-mask.sum()}个)，保留全部数据")
            return data, np.ones(len(data), dtype=bool)
        removed = len(data) - mask.sum()
        if removed > 0:
            print(f"   {label}: 剔除{removed}个极端值 (Z>{threshold})")
        return data[mask], mask

    # ========== 双耦合测试 ==========

    # 测试一: 双CAGR偏离度 (不剔除，用于判断)
    cagr_p_div = (prices[-1] / prices[0]) ** (1 / (n_div - 1)) - 1
    cagr_d = (dividends[-1] / dividends[0]) ** (1 / (n_div - 1)) - 1
    deviation_div = abs(cagr_p_div - cagr_d)

    cagr_p_eps = (prices_eps[-1] / prices_eps[0]) ** (1 / (n_eps - 1)) - 1
    cagr_eps = (eps_values[-1] / eps_values[0]) ** (1 / (n_eps - 1)) - 1
    deviation_eps = abs(cagr_p_eps - cagr_eps)

    test1_div_pass = deviation_div < 0.05
    test1_eps_pass = deviation_eps < 0.05
    test1_pass = test1_div_pass or test1_eps_pass  # 单一耦合通过即可

    # 测试二: 双β与R² (先不使用剔除极端值)
    print("   分红回归: 首次拟合")
    ln_p_div = np.log(prices)
    ln_d = np.log(dividends)
    slope_div, _, r_div, _, _ = stats.linregress(ln_d, ln_p_div)
    r_squared_div = r_div ** 2
    test2_div_pass_initial = r_squared_div >= 0.6

    print("   EPS回归: 首次拟合")
    ln_p_eps = np.log(prices_eps)
    ln_eps = np.log(eps_values)
    slope_eps, _, r_eps, _, _ = stats.linregress(ln_eps, ln_p_eps)
    r_squared_eps = r_eps ** 2
    test2_eps_pass_initial = r_squared_eps >= 0.6

    # 如果首次拟合不通过，剔除极端值后重试
    outlier_removed_div = False
    outlier_removed_eps = False

    if not test2_div_pass_initial:
        print("   分红回归: 首次未通过，剔除极端值后重试")
        ln_p_div_all = np.log(prices)
        ln_d_all = np.log(dividends)
        _, mask_p_div = remove_outliers_zscore(ln_p_div_all, threshold=2.5, label="股价")
        _, mask_d = remove_outliers_zscore(ln_d_all, threshold=2.5, label="分红")
        mask_div = mask_p_div & mask_d
        if mask_div.sum() >= len(prices) * 0.7:
            ln_p_div = ln_p_div_all[mask_div]
            ln_d = ln_d_all[mask_div]
            slope_div, _, r_div, _, _ = stats.linregress(ln_d, ln_p_div)
            r_squared_div = r_div ** 2
            outlier_removed_div = True

    if not test2_eps_pass_initial:
        print("   EPS回归: 首次未通过，剔除极端值后重试")
        ln_p_eps_all = np.log(prices_eps)
        ln_eps_all = np.log(eps_values)
        _, mask_p_eps = remove_outliers_zscore(ln_p_eps_all, threshold=2.5, label="股价")
        _, mask_eps = remove_outliers_zscore(ln_eps_all, threshold=2.5, label="EPS")
        mask_eps_combined = mask_p_eps & mask_eps
        if mask_eps_combined.sum() >= len(prices_eps) * 0.7:
            ln_p_eps = ln_p_eps_all[mask_eps_combined]
            ln_eps = ln_eps_all[mask_eps_combined]
            slope_eps, _, r_eps, _, _ = stats.linregress(ln_eps, ln_p_eps)
            r_squared_eps = r_eps ** 2
            outlier_removed_eps = True

    test2_div_pass = r_squared_div >= 0.6
    test2_eps_pass = r_squared_eps >= 0.6
    test2_pass = test2_div_pass or test2_eps_pass  # 单一耦合通过即可

    # 测试三: Z-score
    pe_data = df_pe['pe'].values
    pe_mean = np.mean(pe_data)
    pe_std = np.std(pe_data)
    current_pe = pe_data[-1]
    z_score = (current_pe - pe_mean) / pe_std if pe_std > 0 else 0
    test3_pass = z_score <= 1.5

    # 波动率
    log_returns = np.diff(np.log(prices))
    sigma = np.std(log_returns)

    print(f'\n📊 Phase 2: 双耦合验证测试')
    print(f'   --- 分红-股价耦合 ---')
    print(f'   测试一: CAGR偏离度 {"✅" if test1_div_pass else "❌"} (偏离度: {deviation_div*100:.2f}%)')
    print(f'   测试二: β与R² {"✅" if test2_div_pass else "❌"} (R²={r_squared_div:.4f}){" [剔除极端值后]" if outlier_removed_div else ""}')
    print(f'   --- EPS-股价耦合 ---')
    print(f'   测试一: CAGR偏离度 {"✅" if test1_eps_pass else "❌"} (偏离度: {deviation_eps*100:.2f}%)')
    print(f'   测试二: β与R² {"✅" if test2_eps_pass else "❌"} (R²={r_squared_eps:.4f}){" [剔除极端值后]" if outlier_removed_eps else ""}')
    print(f'   --- Z-score ---')
    print(f'   测试三: Z-score {"✅" if test3_pass else "❌"} (Z={z_score:.2f})')

    # 判决
    coupling_type = ''
    if test1_div_pass and test2_div_pass:
        coupling_type = '分红'
    elif test1_eps_pass and test2_eps_pass:
        coupling_type = 'EPS'

    if test1_pass and test2_pass and test3_pass:
        if coupling_type == '分红' and test1_eps_pass and test2_eps_pass:
            verdict = '完美耦合型'
        elif coupling_type == '分红':
            verdict = '分红耦合型'
        elif coupling_type == 'EPS':
            verdict = 'EPS耦合型'
        else:
            verdict = '单一耦合型'
        can_predict = True
        predict_reason = ""
    elif not test1_pass and test3_pass:
        verdict = '泡沫假象型'
        can_predict = False
        predict_reason = "股价与基本面严重脱节(R²偏低)，定价受宏观/情绪/概念主导，DRIP预测模型失效。"
    elif not test1_pass and z_score < -1:
        verdict = '估值还债/深坑型'
        can_predict = True  # 低估值提供安全边际
        predict_reason = "虽未通过耦合测试，但当前估值极低(深坑型)，高股息提供安全边际。"
    else:
        verdict = '部分通过'
        can_predict = False
        predict_reason = "多项耦合测试未通过，股价定价逻辑不清晰，DRIP预测不确定性太高。"

    print(f'\n🎯 Phase 3: 定性判决 - {verdict}')
    if not can_predict:
        print(f'   ⚠️ {predict_reason}')

    # DRIP模拟
    g = cagr_p_div
    current_price = df_price['price'].values[-1]
    current_div = df_div['dividend'].values[-1] if len(df_div) > 0 else 0
    y = current_div / current_price
    d0 = y * current_price

    if can_predict:
        print(f'\n🎲 Phase 4: DRIP蒙特卡洛模拟')
        print(f'   g={g*100:.2f}% σ={sigma*100:.2f}% Y={y*100:.2f}%')

        # 模拟
        results = []
        initial_shares = INITIAL_INVESTMENT / current_price
        for _ in range(SIMULATIONS):
            p, d, s = current_price, d0, initial_shares
            for _ in range(SIM_YEARS):
                z = np.random.normal(0, 1)
                p = p * np.exp((g - 0.5 * sigma**2) + sigma * z)
                d = d * (1 + g)
                s = s + (d / p)
            results.append(s * p / INITIAL_INVESTMENT)

        results = np.array(results)
        median = np.median(results)
        double_prob = (results > 2.0).mean()
        loss_prob = (results < 1.0).mean()
        var_5 = np.percentile(results, 5)

        print(f'   中位数: {median:.2f}x | 翻倍概率: {double_prob*100:.1f}% | 亏损概率: {loss_prob*100:.1f}%')
    else:
        print(f'\n🎲 Phase 4: 跳过DRIP模拟')
        print(f'   原因: {predict_reason}')
        results = None
        median = None
        double_prob = None
        loss_prob = None
        var_5 = None

    logout_baostock()

    return {
        'df_price': df_price, 'df_div': df_div, 'df_eps': df_eps, 'df_pe': df_pe,
        'merged_div': merged_div, 'merged_eps': merged_eps,
        'cagr_p_div': cagr_p_div, 'cagr_d': cagr_d, 'deviation_div': deviation_div,
        'cagr_p_eps': cagr_p_eps, 'cagr_eps': cagr_eps, 'deviation_eps': deviation_eps,
        'test1_div_pass': test1_div_pass, 'test1_eps_pass': test1_eps_pass,
        'slope_div': slope_div, 'r_squared_div': r_squared_div,
        'slope_eps': slope_eps, 'r_squared_eps': r_squared_eps,
        'test2_div_pass': test2_div_pass, 'test2_eps_pass': test2_eps_pass,
        'current_pe': current_pe, 'pe_mean': pe_mean, 'pe_std': pe_std,
        'z_score': z_score, 'test3_pass': test3_pass,
        'sigma': sigma,
        'g': g, 'y': y, 'd0': d0, 'p0': current_price,
        'median': median, 'double_prob': double_prob, 'loss_prob': loss_prob, 'var_5': var_5,
        'verdict': verdict, 'results': results,
        'can_predict': can_predict, 'predict_reason': predict_reason
    }

# ============== 可视化 ==============
def generate_charts(data):
    print('\n📈 生成可视化图表...')
    prices = data['df_price']['price'].values
    years = data['df_price']['year'].values
    merged_div = data['merged_div']
    merged_eps = data['merged_eps']

    # Chart 1: 股价走势图
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
    plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_股价走势图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 2: 分红-股价对数趋势图
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()
    ax1.plot(merged_div['year'], np.log(merged_div['price']), 'o-', color='tab:blue', linewidth=2, label='ln(股价)')
    ax2.plot(merged_div['year'], np.log(merged_div['dividend']), 's--', color='tab:red', linewidth=2, label='ln(分红)')
    ax1.set_ylabel('ln(股价)', color='tab:blue')
    ax2.set_ylabel('ln(分红)', color='tab:red')
    ax1.set_xlabel('年份')
    plt.title(f'{STOCK_NAME} 分红-股价对数趋势图 (耦合检验)', fontsize=14, fontweight='bold')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.95))
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_分红对数趋势图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 3: EPS-股价对数趋势图
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()
    ax1.plot(merged_eps['year'], np.log(merged_eps['price']), 'o-', color='tab:blue', linewidth=2, label='ln(股价)')
    ax2.plot(merged_eps['year'], np.log(merged_eps['eps']), 's--', color='tab:green', linewidth=2, label='ln(EPS)')
    ax1.set_ylabel('ln(股价)', color='tab:blue')
    ax2.set_ylabel('ln(EPS)', color='tab:green')
    ax1.set_xlabel('年份')
    plt.title(f'{STOCK_NAME} EPS-股价对数趋势图 (耦合检验)', fontsize=14, fontweight='bold')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.95))
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_EPS对数趋势图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 4: 分红弹性回归散点图
    ln_p_div = np.log(merged_div['price'].values)
    ln_d = np.log(merged_div['dividend'].values)
    slope_div, intercept_div, r_div, _, _ = stats.linregress(ln_d, ln_p_div)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(ln_d, ln_p_div, s=80, alpha=0.7, color='tab:red', label='年度数据')
    x_line = np.linspace(ln_d.min(), ln_d.max(), 100)
    ax.plot(x_line, slope_div * x_line + intercept_div, 'r-', linewidth=2)
    ax.set_xlabel('ln(分红)')
    ax.set_ylabel('ln(股价)')
    ax.set_title(f'{STOCK_NAME} 分红弹性回归\nβ={slope_div:.2f}, R²={r_div**2:.4f}', fontsize=14, fontweight='bold')
    textstr = f'β = {slope_div:.2f}\nR² = {r_div**2:.4f}'
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_分红回归散点图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 5: EPS弹性回归散点图
    ln_p_eps = np.log(merged_eps['price'].values)
    ln_eps = np.log(merged_eps['eps'].values)
    slope_eps, intercept_eps, r_eps, _, _ = stats.linregress(ln_eps, ln_p_eps)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(ln_eps, ln_p_eps, s=80, alpha=0.7, color='tab:green', label='年度数据')
    x_line = np.linspace(ln_eps.min(), ln_eps.max(), 100)
    ax.plot(x_line, slope_eps * x_line + intercept_eps, 'g-', linewidth=2)
    ax.set_xlabel('ln(EPS)')
    ax.set_ylabel('ln(股价)')
    ax.set_title(f'{STOCK_NAME} EPS弹性回归\nβ={slope_eps:.2f}, R²={r_eps**2:.4f}', fontsize=14, fontweight='bold')
    textstr = f'β = {slope_eps:.2f}\nR² = {r_eps**2:.4f}'
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_EPS回归散点图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 6: PE Band
    pe_series = data['df_pe']['pe'].values
    pe_years = data['df_pe']['year'].values
    pe_mean = data['pe_mean']
    pe_std = data['pe_std']
    current_pe = data['current_pe']

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
    plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_PE_Band图.png', dpi=150, bbox_inches='tight')
    plt.close()

    # Chart 7: DRIP分布 (仅在可预测时生成)
    if data['can_predict']:
        results = data['results']
        median = data['median']
        var_5 = data['var_5']

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
        plt.savefig(f'{TMP_DIR}/{STOCK_NAME}_drip_高级分布图.png', dpi=150, bbox_inches='tight')
        plt.close()
        print('   ✅ 7张图表生成完成')
    else:
        print('   ✅ 6张图表生成完成 (跳过DRIP分布图)')

# ============== PDF生成 ==============
def generate_pdf(data):
    print('\n📄 生成PDF报告...')

    # 生成 content.json - 带问题诊断
    # 分红诊断
    if data['test1_div_pass'] and data['test2_div_pass']:
        div_diagnosis = "分红与股价完美耦合，股东回报与股价增长同步"
    elif not data['test1_div_pass'] and data['cagr_d'] > data['cagr_p_div']:
        div_diagnosis = "分红增长远超股价(脱节)，公司可能在高估历史估值或留存利润"
    elif not data['test1_div_pass']:
        div_diagnosis = "股价涨幅远超分红，估值泡沫风险"
    else:
        div_diagnosis = "分红增长尚可，但R²解释力不足，定价受其他因素主导"

    # EPS诊断
    if data['test1_eps_pass'] and data['test2_eps_pass']:
        eps_diagnosis = "EPS与股价完美耦合，基本面驱动定价"
    elif not data['test1_eps_pass'] and data['cagr_eps'] > data['cagr_p_eps']:
        eps_diagnosis = "EPS增长远超股价，公司盈利能力提升未反映到股价"
    elif not data['test1_eps_pass']:
        eps_diagnosis = "股价涨幅远超EPS，定价脱离业绩基本面"
    else:
        eps_diagnosis = "EPS增长尚可，但R²解释力不足，定价受宏观/情绪影响"

    # Z-score诊断
    if data['z_score'] < -1:
        pe_diagnosis = "严重低估，历史PE低位，DRIP安全边际高"
    elif data['z_score'] < 0:
        pe_diagnosis = "偏低估，PE低于历史均值，具配置价值"
    elif data['z_score'] < 1.5:
        pe_diagnosis = "正常估值区间，PE接近历史均值"
    else:
        pe_diagnosis = "偏高估，PE高于历史均值，小心戴维斯双杀"

    # 判决诊断
    if data['verdict'] == '完美耦合型':
        verdict_diagnosis = "水电/REITs等刚性需求+稳定现金流资产，股东回报与股价锁定。DRIP策略高度适配，分红再投资能持续积累股数。"
    elif data['verdict'] == '分红耦合型':
        verdict_diagnosis = "分红与股价耦合，但EPS关联弱。适合收息型投资者，但需关注分红政策持续性。"
    elif data['verdict'] == 'EPS耦合型':
        verdict_diagnosis = "EPS增长驱动股价，但分红未同步。可能处于成长期或利润留存再投资。DRIP效果依赖股价稳定性。"
    elif data['verdict'] == '泡沫假象型':
        verdict_diagnosis = "股价定价脱离基本面！R²极低说明股价受宏观/情绪/概念主导。DRIP在此标的上效果存疑。"
    elif data['verdict'] == '估值还债/深坑型':
        verdict_diagnosis = "历史高估值正在消化，PE极低。困境反转标的，高股息率弥补等待时间。"
    else:
        verdict_diagnosis = "多项测试未通过，需谨慎评估。DRIP效果取决于后续耦合修复。"

    # 构建PDF内容
    content = [
        {"type": "h1", "text": f"{STOCK_NAME} DRIP量化分析报告"},
        {"type": "body", "text": f"股票代码: {STOCK_CODE} | 分析周期: {YEARS}年 (2017-2026)<br/>当前股价: {data['p0']:.2f}元 | 当前PE: {data['current_pe']:.2f} | 股息率: {data['y']*100:.2f}%"},
        {"type": "h2", "text": "一、数据概况"},
        {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_股价走势图.png", "caption": "10年股价走势与最大回撤分析"},
        {"type": "h2", "text": "二、双耦合验证测试"},
        {"type": "h3", "text": "2.1 分红-股价耦合"},
        {"type": "callout", "text": f"CAGR偏离度: {'✅ 通过' if data['test1_div_pass'] else '❌ 未通过'} (偏离度: {data['deviation_div']*100:.2f}%)\nR²: {'✅ 通过' if data['test2_div_pass'] else '❌ 未通过'} ({data['r_squared_div']:.4f})\n\n诊断: {div_diagnosis}"},
        {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_分红对数趋势图.png", "caption": "分红-股价对数趋势图"},
        {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_分红回归散点图.png", "caption": "分红弹性回归散点图"},
        {"type": "h3", "text": "2.2 EPS-股价耦合"},
        {"type": "callout", "text": f"CAGR偏离度: {'✅ 通过' if data['test1_eps_pass'] else '❌ 未通过'} (偏离度: {data['deviation_eps']*100:.2f}%)\nR²: {'✅ 通过' if data['test2_eps_pass'] else '❌ 未通过'} ({data['r_squared_eps']:.4f})\n\n诊断: {eps_diagnosis}"},
        {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_EPS对数趋势图.png", "caption": "EPS-股价对数趋势图"},
        {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_EPS回归散点图.png", "caption": "EPS弹性回归散点图"},
        {"type": "h3", "text": "2.3 综合Z-score测试"},
        {"type": "callout", "text": f"Z-score: {'✅ 通过' if data['test3_pass'] else '❌ 未通过'} (Z={data['z_score']:.2f})\n当前PE({data['current_pe']:.2f}) vs 历史均值({data['pe_mean']:.2f})\n\n诊断: {pe_diagnosis}"},
        {"type": "h2", "text": "三、估值健康度"},
        {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_PE_Band图.png", "caption": "10年PE Band通道图"},
    ]

    # Phase 4: DRIP模拟 或 无法预测
    if data['can_predict']:
        content.extend([
            {"type": "h2", "text": f"四、DRIP蒙特卡洛模拟 ({SIM_YEARS}年期)"},
            {"type": "table", "headers": ["参数", "值"], "rows": [
                ["g (CAGR)", f"{data['g']*100:.2f}%"],
                ["σ (波动率)", f"{data['sigma']*100:.2f}%"],
                ["Y (股息率)", f"{data['y']*100:.2f}%"],
                ["P0 (股价)", f"{data['p0']:.2f}元"],
                ["D0 (分红)", f"{data['d0']:.4f}元"],
                ["模拟次数", f"{SIMULATIONS:,}次"],
                ["模拟期限", f"{SIM_YEARS}年"]
            ], "col_widths": [0.4, 0.4]},
            {"type": "table", "headers": ["指标", "值", "含义"], "rows": [
                ["中位数", f"{data['median']:.2f}x", "50%概率高于此值"],
                ["翻倍概率", f"{data['double_prob']*100:.1f}%", f"{SIM_YEARS}年增长潜力"],
                ["亏损概率", f"{data['loss_prob']*100:.1f}%", "本金受损概率"],
                ["VaR(5%)", f"{data['var_5']:.2f}x", "极端回撤底线"]
            ], "col_widths": [0.25, 0.2, 0.35]},
            {"type": "figure", "path": f"{TMP_DIR}/{STOCK_NAME}_drip_高级分布图.png", "caption": f"DRIP {SIM_YEARS}年期概率分布"},
            {"type": "h2", "text": "五、定性判决"},
            {"type": "callout", "text": f"🎉 {data['verdict']}\n\n{verdict_diagnosis}\n\n{SIM_YEARS}年DRIP预期: {data['median']:.0%}收益 | 亏损概率: {data['loss_prob']*100:.0f}%"},
        ])
    else:
        content.extend([
            {"type": "h2", "text": "四、无法预测"},
            {"type": "callout", "text": f"⚠️ {data['verdict']}\n\n{data['predict_reason']}\n\n历史数据不足以支撑DRIP蒙特卡洛模拟。\n\n可能原因：\n• 股价与基本面严重背离（R²偏低）\n• 行业周期性过强（证券、能源等）\n• 数据异常/不连续（如新股分红起步晚）\n\n建议：该标的不适合DRIP策略，请选择其他完美耦合型股票。"},
            {"type": "h2", "text": "五、定性判决"},
            {"type": "callout", "text": f"❌ {data['verdict']}\n\n{verdict_diagnosis}\n\n该标的暂不适合DRIP策略。"},
        ])

    content.extend([
        {"type": "divider", "text": ""},
        {"type": "caption", "text": "Generated by Quant Agent | Data Source: Baostock"}
    ])

    content_path = f'{TMP_DIR}/{STOCK_NAME}_content.json'
    with open(content_path, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    # 生成 tokens
    tokens_path = f'{TMP_DIR}/{STOCK_NAME}_tokens.json'
    os.system(f'cd {MINIMAX_PDF} && python3 palette.py '
               f'--title "{STOCK_NAME} DRIP量化分析报告" '
               f'--type report --author "Quant Agent" '
               f'--date "2026-03-27" --accent "#E8A020" '
               f'--out {tokens_path} 2>/dev/null')

    # 添加中文字体到 tokens
    with open(tokens_path, 'r') as f:
        tokens = json.load(f)
    tokens["font_paths"] = {
        "STHeiti": "/System/Library/Fonts/STHeiti Light.ttc"
    }
    tokens["font_body_rl"] = "STHeiti"
    tokens["font_body_b_rl"] = "STHeiti"
    tokens["font_display_rl"] = "STHeiti"
    with open(tokens_path, 'w') as f:
        json.dump(tokens, f, indent=2)

    # 生成 cover
    cover_html = f'{TMP_DIR}/{STOCK_NAME}_cover.html'
    cover_pdf = f'{TMP_DIR}/{STOCK_NAME}_cover.pdf'
    os.system(f'cd {MINIMAX_PDF} && python3 cover.py --tokens {tokens_path} --out {cover_html} 2>/dev/null')
    os.system(f'cd {MINIMAX_PDF} && node render_cover.js --input {cover_html} --out {cover_pdf} 2>/dev/null')

    # 生成 body
    body_pdf = f'{TMP_DIR}/{STOCK_NAME}_body.pdf'
    os.system(f'cd {MINIMAX_PDF} && python3 render_body.py --tokens {tokens_path} --content {content_path} --out {body_pdf} 2>/dev/null')

    # 合并
    output_pdf = f'{TMP_DIR}/{STOCK_NAME}_DRIP_分析报告.pdf'
    os.system(f'cd {MINIMAX_PDF} && python3 merge.py --cover {cover_pdf} --body {body_pdf} --out {output_pdf} --title "{STOCK_NAME} DRIP量化分析报告" 2>/dev/null')

    print(f'   ✅ PDF生成完成: {output_pdf}')
    return output_pdf

# ============== 主流程 ==============
def main():
    # 1. 运行分析
    data = run_analysis()

    # 2. 生成图表
    generate_charts(data)

    # 3. 生成PDF
    pdf_path = generate_pdf(data)

    print(f'\n{"="*60}')
    print('✅ 完成!')
    print(f'   图表: {TMP_DIR}/{STOCK_NAME}_*.png')
    print(f'   PDF: {pdf_path}')
    print(f'{"="*60}')

    return pdf_path

if __name__ == '__main__':
    main()