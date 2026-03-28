#!/usr/bin/env python3
"""
Phase 1: 数据获取与清洗 (Data Acquisition)
使用 Baostock 接口获取A股10年历史数据
"""

import pandas as pd
import numpy as np
import baostock as bs
import warnings
warnings.filterwarnings('ignore')

from datetime import datetime

def fetch_stock_data_baostock(stock_code: str, years: int = 10) -> tuple:
    """
    使用 baostock 获取股票10年历史数据
    - 前复权收盘价
    - 年度EPS
    - 年度分红
    """
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = f"{datetime.now().year - years + 1}-01-01"

    # 转换代码格式 sh.600519 -> sh.600519
    bs_code = stock_code.lower().replace('.sh', '.sh').replace('.sz', '.sz')
    if not bs_code.startswith('sh.') and not bs_code.startswith('sz.'):
        # 假设沪市
        bs_code = f"sh.{stock_code.replace('.SH', '').replace('.SZ', '')}"

    print(f"\n📥 开始获取 {stock_code} ({bs_code}) {years} 年数据 (Baostock)...")

    results = {}

    # ========== 1. 价格数据 (前复权) ==========
    print("   - 价格数据 (前复权)...", end=" ")
    try:
        rs = bs.query_history_k_data_plus(
            code=bs_code,
            start_date=start_date,
            end_date=end_date,
            frequency='d',
            fields='date,code,open,high,low,close,volume,amount'
        )

        data_list = []
        while rs.error_code == '0' and rs.next():
            data_list.append(rs.get_row_data())
        df_price = pd.DataFrame(data_list, columns=rs.fields)

        # 转换日期并按年聚合
        df_price['date'] = pd.to_datetime(df_price['date'])
        df_price['year'] = df_price['date'].dt.year
        df_price['close'] = pd.to_numeric(df_price['close'], errors='coerce')

        # 取年末收盘价
        annual_price = df_price.groupby('year')['close'].last().reset_index()
        annual_price.columns = ['year', 'price']

        results['price'] = annual_price
        print(f"✅ {len(annual_price)} 年")
    except Exception as e:
        print(f"❌ {e}")
        results['price'] = pd.DataFrame(columns=['year', 'price'])

    # ========== 2. EPS数据 ==========
    print("   - EPS数据...", end=" ")
    try:
        all_eps = []
        for year in range(datetime.now().year - years + 1, datetime.now().year + 1):
            for quarter in [1, 2, 3, 4]:
                rs = bs.query_profit_data(code=bs_code, year=str(year), quarter=quarter)
                while rs.error_code == '0' and rs.next():
                    row = rs.get_row_data()
                    # fields: ['code', 'pubDate', 'statDate', 'roeAvg', 'npMargin', 'gpMargin', 'netProfit', 'epsTTM', 'MBRevenue', 'totalShare', 'liqaShare']
                    # index 7 = epsTTM
                    if row[7] and row[7] != '':
                        try:
                            eps = float(row[7])
                            report_year = int(row[2][:4]) if row[2] else year
                            all_eps.append({'year': report_year, 'eps': eps})
                        except:
                            pass

        if all_eps:
            df_eps = pd.DataFrame(all_eps)
            # 取年末财报的EPS（通常Q4的数据是全年完整EPS）
            annual_eps = df_eps.groupby('year')['eps'].last().reset_index()
            results['eps'] = annual_eps
            print(f"✅ {len(annual_eps)} 年")
        else:
            print("❌ 未获取到EPS")
            results['eps'] = pd.DataFrame(columns=['year', 'eps'])
    except Exception as e:
        print(f"❌ {e}")
        results['eps'] = pd.DataFrame(columns=['year', 'eps'])

    # ========== 3. 分红数据 ==========
    print("   - 分红数据...", end=" ")
    try:
        all_div = []
        for year in range(datetime.now().year - years + 1, datetime.now().year + 1):
            rs = bs.query_dividend_data(code=bs_code, year=str(year))
            while rs.error_code == '0' and rs.next():
                row = rs.get_row_data()
                # fields: ['code', 'dividPreNoticeDate', 'dividAgmPumDate', 'dividPlanAnnounceDate', 'dividPlanDate',
                #          'dividRegistDate', 'dividOperateDate', 'dividPayDate', 'dividStockMarketDate',
                #          'dividCashPsBeforeTax', 'dividCashPsAfterTax', 'dividStocksPs', 'dividCashStock', ...]
                # index 9 = dividCashPsBeforeTax (每股派息)
                try:
                    if row[9] and row[9] != '':
                        div = float(row[9])
                        report_date = row[3] if row[3] else f"{year}-12-31"
                        report_year = int(report_date[:4]) if report_date else year
                        all_div.append({'year': report_year, 'dividend': div})
                except:
                    pass

        if all_div:
            df_div = pd.DataFrame(all_div)
            # 按年汇总分红（可能有半年分红）
            annual_div = df_div.groupby('year')['dividend'].sum().reset_index()
            results['dividend'] = annual_div
            print(f"✅ {len(annual_div)} 年")
        else:
            print("❌ 未获取到分红")
            results['dividend'] = pd.DataFrame(columns=['year', 'dividend'])
    except Exception as e:
        print(f"❌ {e}")
        results['dividend'] = pd.DataFrame(columns=['year', 'dividend'])

    # ========== 4. 当前PE ==========
    results['current_pe'] = 0.0
    print("   - PE数据...", end=" ")
    try:
        # 使用最新价格/EPS估算PE
        if len(results['price']) > 0 and len(results['eps']) > 0:
            latest_price = results['price']['price'].iloc[-1]
            latest_eps = results['eps']['eps'].iloc[-1]
            if latest_eps > 0:
                results['current_pe'] = latest_price / latest_eps
                print(f"✅ PE={results['current_pe']:.2f}")
            else:
                print("❌ EPS为0")
        else:
            print("❌ 数据不足")
    except Exception as e:
        print(f"❌ {e}")

    # ========== 合并数据 ==========
    print("\n📊 数据合并与对齐...")

    all_years = pd.DataFrame({'year': range(datetime.now().year - years + 1, datetime.now().year + 1)})

    merged = all_years.copy()
    merged['price'] = np.nan
    merged['eps'] = np.nan
    merged['dividend'] = np.nan

    if len(results['price']) > 0:
        for _, row in results['price'].iterrows():
            mask = merged['year'] == row['year']
            merged.loc[mask, 'price'] = row['price']

    if len(results['eps']) > 0:
        for _, row in results['eps'].iterrows():
            mask = merged['year'] == row['year']
            merged.loc[mask, 'eps'] = row['eps']

    if len(results['dividend']) > 0:
        for _, row in results['dividend'].iterrows():
            mask = merged['year'] == row['year']
            merged.loc[mask, 'dividend'] = row['dividend']

    # 计算估算PE
    merged['pe_estimated'] = merged['price'] / merged['eps']
    merged.loc[(merged['pe_estimated'] <= 0) | (merged['pe_estimated'] > 1000), 'pe_estimated'] = np.nan

    # 保存
    output_path = f"/tmp/{stock_code.replace('.', '_')}_baostock_data.json"
    merged.to_json(output_path, orient='records', date_format='iso')

    # 打印预览
    print(f"\n{'='*70}")
    print(f"📅 {stock_code} {datetime.now().year - years + 1}-{datetime.now().year} 年度数据预览")
    print(f"{'='*70}")
    print(merged.to_string(index=False))
    print(f"{'='*70}")

    print(f"\n📈 数据概况:")
    print(f"   - 价格: {merged['price'].count()}/{years} 年有效")
    print(f"   - EPS:  {merged['eps'].count()}/{years} 年有效")
    print(f"   - 分红: {merged['dividend'].count()}/{years} 年有效")
    print(f"   - 当前PE(估算): {results['current_pe']:.2f}")

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
    print(f"# Phase 1: 数据获取与清洗 (Baostock)")
    print(f"# 股票: {stock}")
    print(f"# 周期: {years} 年")
    print(f"{'#'*70}")

    # 登录 baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ Baostock 登录失败: {lg.error_msg}")
        exit(1)
    print(f"✅ Baostock 登录成功")

    try:
        data, meta = fetch_stock_data_baostock(stock, years)
    finally:
        bs.logout()
        print("\n🔒 已退出 Baostock")