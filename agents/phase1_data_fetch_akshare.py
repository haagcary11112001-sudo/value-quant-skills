#!/usr/bin/env python3
"""
Phase 1: 数据获取与清洗 (Data Acquisition)
使用 AkShare 接口获取股票10年历史数据
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

try:
    import akshare as ak
except ImportError:
    print("❌ akshare 未安装，请运行: pip install akshare")
    exit(1)

from datetime import datetime

def fetch_stock_data_akshare(stock_code: str, years: int = 10) -> tuple:
    """
    使用 akshare 获取股票历史数据
    """
    end_year = datetime.now().year
    start_year = end_year - years + 1

    print(f"\n📥 开始获取 {stock_code} {start_year}-{end_year} 年度数据 (AkShare)...")

    results = {}

    # ========== 1. 价格数据 (前复权) ==========
    print("   - 价格数据 (前复权)...", end=" ")
    try:
        symbol = stock_code.replace(".SH", "").replace(".SZ", "")
        df_price = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=f"{start_year}0101",
            end_date=f"{end_year}1231",
            adjust="qfq"
        )
        df_price['日期'] = pd.to_datetime(df_price['日期'])
        df_price['年份'] = df_price['日期'].dt.year
        annual_price = df_price.groupby('年份')['收盘'].last().reset_index()
        annual_price.columns = ['year', 'price']
        annual_price = annual_price[(annual_price['year'] >= start_year) & (annual_price['year'] <= end_year)]
        results['price'] = annual_price
        print(f"✅ {len(annual_price)} 条")
    except Exception as e:
        print(f"❌ {e}")
        results['price'] = pd.DataFrame(columns=['year', 'price'])

    # ========== 2. EPS数据 (使用财务分析接口) ==========
    print("   - EPS数据...", end=" ")
    try:
        symbol = stock_code.replace(".SH", "").replace(".SZ", "")
        df_fin = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=str(start_year), end_year=str(end_year))
        # 找到每股收益列
        eps_col = None
        for col in df_fin.columns:
            if '基本每股收益' in col or 'EPS' in col.upper():
                eps_col = col
                break
        if eps_col:
            df_eps = df_fin[['日期', eps_col]].copy()
            df_eps['日期'] = pd.to_datetime(df_eps['日期'])
            df_eps['年份'] = df_eps['日期'].dt.year
            annual_eps = df_eps.groupby('年份')[eps_col].last().reset_index()
            annual_eps.columns = ['year', 'eps']
            annual_eps = annual_eps[(annual_eps['year'] >= start_year) & (annual_eps['year'] <= end_year)]
            results['eps'] = annual_eps
            print(f"✅ {len(annual_eps)} 条")
        else:
            print("❌ 未找到EPS列")
            results['eps'] = pd.DataFrame(columns=['year', 'eps'])
    except Exception as e:
        print(f"❌ {e}")
        results['eps'] = pd.DataFrame(columns=['year', 'eps'])

    # ========== 3. 分红数据 ==========
    print("   - 分红数据...", end=" ")
    try:
        symbol = stock_code.replace(".SH", "").replace(".SZ", "")
        # 使用 stock_a_lg_indicator 获取分红数据
        df_div = ak.stock_a_lg_indicator(symbol=symbol)
        # 找每股股息列
        div_col = None
        for col in df_div.columns:
            if '每股派息' in col or '股息' in col or '分红' in col:
                div_col = col
                break
        if div_col:
            df_div['年份'] = pd.to_datetime(df_div['日期']).dt.year
            annual_div = df_div.groupby('年份')[div_col].last().reset_index()
            annual_div.columns = ['year', 'dividend']
            annual_div = annual_div[(annual_div['year'] >= start_year) & (annual_div['year'] <= end_year)]
            results['dividend'] = annual_div
            print(f"✅ {len(annual_div)} 条")
        else:
            print("❌ 未找到分红列")
            results['dividend'] = pd.DataFrame(columns=['year', 'dividend'])
    except Exception as e:
        print(f"❌ {e}")
        results['dividend'] = pd.DataFrame(columns=['year', 'dividend'])

    # ========== 4. 当前PE ==========
    print("   - PE数据...", end=" ")
    results['current_pe'] = 0.0
    try:
        symbol = stock_code.replace(".SH", "").replace(".SZ", "")
        df_spot = ak.stock_zh_a_spot_em()
        stock_row = df_spot[df_spot['代码'] == symbol]
        if not stock_row.empty:
            pe = stock_row['市盈率'].values[0]
            if pd.notna(pe) and pe > 0:
                results['current_pe'] = float(pe)
                print(f"✅ PE={results['current_pe']:.2f}")
            else:
                print("❌ PE无效")
        else:
            print("❌ 未找到标的")
    except Exception as e:
        print(f"❌ {e}")

    # ========== 合并数据 ==========
    print("\n📊 数据合并与对齐...")

    all_years = pd.DataFrame({'year': range(start_year, end_year + 1)})

    merged = all_years.copy()
    merged['price'] = np.nan
    merged['eps'] = np.nan
    merged['dividend'] = np.nan

    if len(results['price']) > 0:
        for _, row in results['price'].iterrows():
            merged.loc[merged['year'] == row['year'], 'price'] = row['price']

    if len(results['eps']) > 0:
        for _, row in results['eps'].iterrows():
            merged.loc[merged['year'] == row['year'], 'eps'] = row['eps']

    if len(results['dividend']) > 0:
        for _, row in results['dividend'].iterrows():
            merged.loc[merged['year'] == row['year'], 'dividend'] = row['dividend']

    # 计算估算PE
    merged['pe_estimated'] = merged['price'] / merged['eps']
    merged.loc[merged['pe_estimated'] <= 0, 'pe_estimated'] = np.nan

    # 保存
    output_path = f"/tmp/{stock_code.replace('.', '_')}_akshare_data.json"
    merged.to_json(output_path, orient='records', date_format='iso')

    # 打印预览
    print(f"\n{'='*70}")
    print(f"📅 {stock_code} {start_year}-{end_year} 年度数据预览")
    print(f"{'='*70}")
    print(merged.to_string(index=False))
    print(f"{'='*70}")

    print(f"\n📈 数据概况:")
    print(f"   - 价格: {merged['price'].count()}/{(end_year-start_year+1)} 年有效")
    print(f"   - EPS:  {merged['eps'].count()}/{(end_year-start_year+1)} 年有效")
    print(f"   - 分红: {merged['dividend'].count()}/{(end_year-start_year+1)} 年有效")
    print(f"   - 当前PE(TTM): {results['current_pe']:.2f}")

    # 估算股息率
    valid_div = merged['dividend'].dropna()
    valid_price = merged['price'].dropna()
    if len(valid_div) > 0 and len(valid_price) > 0:
        avg_div = valid_div.mean()
        last_price = valid_price.iloc[-1]
        if last_price > 0:
            yield_rate = avg_div / last_price * 100
            print(f"   - 估算平均股息率: {yield_rate:.2f}%")

    print(f"\n📁 数据已保存: {output_path}")

    return merged, results

if __name__ == "__main__":
    import sys
    stock = sys.argv[1] if len(sys.argv) > 1 else "600519.SH"
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"\n{'#'*70}")
    print(f"# Phase 1: 数据获取与清洗 (AkShare)")
    print(f"# 股票: {stock}")
    print(f"# 周期: {years} 年")
    print(f"{'#'*70}")

    data, meta = fetch_stock_data_akshare(stock, years)