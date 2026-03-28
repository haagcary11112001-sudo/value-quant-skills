#!/usr/bin/env python3
"""
Phase 1: 数据获取与清洗
调用东方财富 API 获取股票历史数据
"""

import os
import json
import requests
import pandas as pd
from datetime import datetime

MX_APIKEY = os.environ.get("MX_APIKEY", "mkt_Pz4iJAahONxZKM_Wefid02IcAPP0L7fnV5sTVJ3-mMw")
API_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"

def call_mx_api(query: str) -> dict:
    headers = {"Content-Type": "application/json", "apikey": MX_APIKEY}
    response = requests.post(API_URL, headers=headers, json={"toolQuery": query}, timeout=30)
    response.raise_for_status()
    return response.json()

def extract_year(date_str: str) -> int:
    """从日期字符串提取年份"""
    try:
        year_str = date_str.split("年")[0].split("-")[0]
        year = int(''.join(filter(str.isdigit, year_str))[:4])
        return year if 2000 <= year <= 2030 else None
    except:
        return None

def get_stock_data(stock_code: str, years: int = 10) -> dict:
    end_year = datetime.now().year
    start_year = end_year - years + 1

    print(f"\n📥 开始获取 {stock_code} {start_year}-{end_year} 年度数据...")

    results = {}

    # 1. 价格数据
    print("   - 价格数据...")
    try:
        data = call_mx_api(f"{stock_code} {start_year}-{end_year} 年度前复权收盘价")
        if data.get("success"):
            table = data["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"][0]["table"]
            prices = list(table.values())[0]
            dates = table["headName"]
            records = []
            for d, p in zip(dates, prices):
                y = extract_year(d)
                if y:
                    records.append({"year": y, "price": float(p.replace("元", "").replace("¥", "").strip())})
            results["price"] = pd.DataFrame(records).sort_values("year").drop_duplicates("year")
            print(f"     ✅ {len(results['price'])} 条")
    except Exception as e:
        results["price"] = pd.DataFrame(columns=["year", "price"])
        print(f"     ❌ {e}")

    # 2. EPS数据
    print("   - EPS数据...")
    try:
        data = call_mx_api(f"{stock_code} {start_year}-{end_year} 年度每股收益")
        if data.get("success"):
            table = data["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"][0]["table"]
            eps_values = list(table.values())[0]
            dates = table["headName"]
            records = []
            for d, e in zip(dates, eps_values):
                y = extract_year(d)
                if y:
                    records.append({"year": y, "eps": float(e.replace("元", "").strip())})
            results["eps"] = pd.DataFrame(records).sort_values("year").drop_duplicates("year")
            print(f"     ✅ {len(results['eps'])} 条")
    except Exception as e:
        results["eps"] = pd.DataFrame(columns=["year", "eps"])
        print(f"     ❌ {e}")

    # 3. 分红数据
    print("   - 分红数据...")
    try:
        data = call_mx_api(f"{stock_code} {start_year}-{end_year} 年度每股分红")
        records = []
        if data.get("success"):
            table_list = data["data"]["data"]["searchDataResultDTO"].get("dataTableDTOList", [])
            if table_list:
                table = table_list[0]["table"]
                for key, values in table.items():
                    if key == "headName":
                        continue
                    dates = table["headName"]
                    for d, v in zip(dates, values):
                        y = extract_year(d)
                        if y:
                            try:
                                records.append({"year": y, "dividend": float(v.replace("元", "").replace("(含税)", "").strip())})
                            except:
                                pass
        results["dividend"] = pd.DataFrame(records).sort_values("year").drop_duplicates("year") if records else pd.DataFrame(columns=["year", "dividend"])
        print(f"     ✅ {len(results['dividend'])} 条")
    except Exception as e:
        results["dividend"] = pd.DataFrame(columns=["year", "dividend"])
        print(f"     ❌ {e}")

    # 4. PE数据
    print("   - PE数据...")
    try:
        data = call_mx_api(f"{stock_code} 市盈率")
        if data.get("success"):
            table_list = data["data"]["data"]["searchDataResultDTO"].get("dataTableDTOList", [])
            if table_list:
                table = table_list[0]["table"]
                for key, values in table.items():
                    if key == "headName":
                        continue
                    results["current_pe"] = float(values[0].replace("倍", "").strip())
                    results["pe_history"] = [float(v.replace("倍", "").strip()) for v in values if v]
                    print(f"     ✅ PE={results['current_pe']}")
                    break
    except:
        pass

    if "current_pe" not in results:
        results["current_pe"] = 0.0
        results["pe_history"] = []

    # 保存
    output = f"/tmp/{stock_code.replace('.', '_')}_data.json"
    with open(output, "w") as f:
        json.dump({
            "price": results["price"].to_dict(),
            "eps": results["eps"].to_dict(),
            "dividend": results["dividend"].to_dict(),
            "current_pe": results["current_pe"],
            "pe_history": results["pe_history"]
        }, f, default=str)

    print(f"\n📁 数据已保存: {output}")

    # 汇总
    print(f"\n{'='*50}")
    print("数据概况")
    print(f"{'='*50}")
    if len(results["price"]) > 0:
        print(f"📈 价格: {results['price']['year'].min()}-{results['price']['year'].max()}年, 最新价 {results['price']['price'].iloc[-1]:.2f}元")
    if len(results["eps"]) > 0:
        print(f"📊 EPS:  {results['eps']['year'].min()}-{results['eps']['year'].max()}年, 最新 {results['eps']['eps'].iloc[-1]:.2f}元")
    if len(results["dividend"]) > 0:
        avg_div = results["dividend"]["dividend"].mean()
        latest_price = results["price"]["price"].iloc[-1] if len(results["price"]) > 0 else 1
        print(f"💰 分红: {results['dividend']['year'].min()}-{results['dividend']['year'].max()}年, 估算股息率 {avg_div/latest_price*100:.2f}%")
    print(f"📉 PE:   {results['current_pe']:.2f}倍")
    print(f"{'='*50}")

if __name__ == "__main__":
    import sys
    stock = sys.argv[1] if len(sys.argv) > 1 else "601088.SH"
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    get_stock_data(stock, years)