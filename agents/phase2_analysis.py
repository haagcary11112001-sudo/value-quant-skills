#!/usr/bin/env python3
"""
Phase 2: 三大拟合测试
"""

import json
import numpy as np
import pandas as pd
from scipy import stats

def load_data(stock_code: str):
    with open(f"/tmp/{stock_code.replace('.', '_')}_data.json") as f:
        data = json.load(f)
    return pd.DataFrame(data["price"]), pd.DataFrame(data["eps"]), pd.DataFrame(data["dividend"]), data["current_pe"], data["pe_history"]

def test1_cagr(price_df, eps_df):
    print("\n" + "="*50)
    print("【测试一】绝对偏离度测试 (CAGR)")
    print("="*50)

    merged = pd.merge(price_df, eps_df, on="year", how="inner")
    if len(merged) < 2:
        print("❌ 数据不足")
        return None, False, None

    P = merged["price"].values.astype(float)
    EPS = merged["eps"].values.astype(float)
    years = merged["year"].values
    n = len(P)

    CAGR_P = (P[-1] / P[0]) ** (1 / (n - 1)) - 1 if P[0] > 0 else 0
    CAGR_EPS = (EPS[-1] / EPS[0]) ** (1 / (n - 1)) - 1 if EPS[0] > 0 else 0
    deviation = abs(CAGR_P - CAGR_EPS)

    print(f"\n📊 计算结果:")
    print(f"   数据: {n}年 ({merged['year'].min()}-{merged['year'].max()})")
    print(f"   期初→期末: {P[0]:.2f}→{P[-1]:.2f}元")
    print(f"   期初→期末: {EPS[0]:.2f}→{EPS[-1]:.2f]}元")
    print(f"\n   股价CAGR: {CAGR_P:+.2%}")
    print(f"   业绩CAGR: {CAGR_EPS:+.2%}")
    print(f"   偏离度:   {deviation:.2%}")

    passed = deviation < 0.05

    print(f"\n🎯 通过条件: |偏离度| < 5%")
    if passed:
        print("   ✅ 通过 - 股价与业绩完美耦合!")
        print("   💡 底层利润扎实转化为市值，典型的业绩驱动型股票")
    else:
        if CAGR_P > CAGR_EPS:
            print("   ❌ 未通过 - 估值泡沫型")
            print(f"   💡 股价涨幅({CAGR_P:+.1%})远超EPS({CAGR_EPS:+.1%})，估值在扩张")
        else:
            print("   ❌ 未通过 - 估值还债型")
            print(f"   💡 股价涨幅({CAGR_P:+.1%})低于EPS({CAGR_EPS:+.1%})，在消化高估值")

    return CAGR_P, passed, "估值泡沫型" if CAGR_P > CAGR_EPS else "估值还债型"

def test2_elasticity(price_df, eps_df):
    print("\n" + "="*50)
    print("【测试二】弹性与运行轨迹测试 (β & R²)")
    print("="*50)

    merged = pd.merge(price_df, eps_df, on="year", how="inner")
    if len(merged) < 2:
        print("❌ 数据不足")
        return None, None, False

    log_P = np.log(merged["price"].values)
    log_EPS = np.log(merged["eps"].values)

    slope, intercept, r_value, _, _ = stats.linregress(log_EPS, log_P)
    beta, R2 = slope, r_value ** 2

    print(f"\n📊 计算结果:")
    print(f"   β = {beta:.3f}")
    print(f"   R² = {R2:.3f}")

    print(f"\n🔍 通俗解释:")
    if beta > 1:
        print(f"   β={beta:.2f} → EPS每涨1%，股价涨{beta:.1f}% (高弹性)")
    elif beta < 1:
        print(f"   β={beta:.2f} → EPS每涨1%，股价只涨{beta:.1f}% (低弹性)")
    else:
        print(f"   β≈1.0 → 完美线性耦合")

    if R2 < 0.6:
        print(f"   ⚠️ R²={R2:.2f} < 0.6，股价变动仅{R2*100:.1f}%由基本面解释")

    passed = (0.8 <= beta <= 1.2) and (R2 >= 0.6)
    print(f"\n🎯 通过条件: β∈[0.8,1.2] 且 R²≥0.6")
    print("   ✅ 通过" if passed else "   ❌ 未通过")

    return beta, R2, passed

def test3_pe(current_pe, pe_history):
    print("\n" + "="*50)
    print("【测试三】期末估值异常度测试 (Z-Score)")
    print("="*50)

    if len(pe_history) >= 3:
        pe_mean = np.mean(pe_history)
        pe_std = np.std(pe_history)
        z_score = (current_pe - pe_mean) / pe_std if pe_std > 0 else 0
    else:
        pe_mean, pe_std, z_score = current_pe, 0, 0

    print(f"\n📊 计算结果:")
    print(f"   当前PE: {current_pe:.2f}倍")
    print(f"   历史均值: {pe_mean:.2f}倍")
    print(f"   Z-Score: {z_score:.2f}")

    print(f"\n🔍 解释:")
    if z_score > 1.5:
        print(f"   Z={z_score:.1f}>1.5，当前估值显著高于历史，可能遭遇戴维斯双杀")
    elif z_score < -1.5:
        print(f"   Z={z_score:.1f}<-1.5，明显低估，可能是困境反转机会")
    else:
        print(f"   Z={z_score:.1f}，估值处于正常区间")

    passed = z_score <= 1.5
    print(f"\n🎯 通过条件: Z≤1.5")
    print("   ✅ 通过" if passed else "   ❌ 未通过")

    return z_score, passed

def main():
    stock = "601088.SH"
    print("="*50)
    print(f"🔬 Phase 2: 三大拟合测试 - {stock}")
    print("="*50)

    price_df, eps_df, dividend_df, current_pe, pe_history = load_data(stock)

    print(f"\n📋 数据: 价格{len(price_df)}条, EPS{len(eps_df)}条")

    cagr_p, passed1, fail_type = test1_cagr(price_df, eps_df)
    beta, r2, passed2 = test2_elasticity(price_df, eps_df)
    z_score, passed3 = test3_pe(current_pe, pe_history)

    print("\n" + "="*50)
    print("📋 汇总")
    print("="*50)
    print(f"   测试一: {'✅' if passed1 else '❌'}")
    print(f"   测试二: {'✅' if passed2 else '❌'}")
    print(f"   测试三: {'✅' if passed3 else '❌'}")

    all_passed = passed1 and passed2 and passed3

    print("\n" + "="*50)
    if all_passed:
        print("🎉 最终判决: 【完美耦合型】")
        print("   建议进入Phase 4蒙特卡洛模拟")
    else:
        print(f"❌ 最终判决: 【{fail_type if fail_type else '非耦合型'}】")
        print("   建议谨慎投资")
    print("="*50)

    # 保存结果
    with open(f"/tmp/{stock.replace('.', '_')}_test_results.json", "w") as f:
        json.dump({"cagr_p": cagr_p, "passed1": passed1, "beta": beta, "r2": r2, "passed2": passed2, "z_score": z_score, "passed3": passed3, "all_passed": all_passed}, f, default=str)

if __name__ == "__main__":
    main()