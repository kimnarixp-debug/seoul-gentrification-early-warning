"""6단계: 과거 검증 (간편 방식, 사용자 결정 2026-11-24).

- 유형: 4단계 유형 그대로 (2022Q1~2026Q1 전체 자료로 만든 군집)
- 전이확률: t<=12 (2024년 4분기까지) 자료로만 추정 -> 4분기 뒤 t=16 (2025년 4분기) 예측
- 예측: run/05b_predict.py reports/step6 300 12 결과 (geosnap predict_markov_labels 300회)

비교 대상
  (1) 유형 유지: t=16 유형 = t=12 유형 (설계서 기준)
  (2) 비공간 전이확률: geosnap transition(w_type=None)으로 t<=12에서 추정한 행렬 P의 4제곱에서
      기준 유형 행을 읽은 값 (이웃 효과 없이 같은 마르코프 모형)
  (3) 공간 모형: 위 300회 시뮬레이션 비율 (이웃 효과 포함)

실제값: (A) t=16 한 분기 유형, (B) 2025년 기간 유형(t=13~16 최빈, 동률이면 최근)
지표: 전체 유형 적중률, 경보 대상 안에서 AUC와 상위 N곳 적중 수 (sklearn roc_auc_score)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import geopandas as gpd
import numpy as np
import pandas as pd
from geosnap.analyze import transition
from sklearn.metrics import roc_auc_score
from seoul_to_geosnap import load_boundaries

OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/step6"
BASE, H = 12, 4
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
LOW = ["안정형", "교체형"]  # 5단계 경보와 같은 기준: 쇠퇴형 제외, 점포 10곳 이상
MIN_STORES = 10

t = pd.read_parquet("reports/step4/types.parquet")
prob = pd.read_csv(os.path.join(OUT, f"predict_probs_base{BASE}.csv"), dtype={"trade_area_code": str}).set_index("trade_area_code")


def period_type(d):
    vc = d["type_name"].value_counts()
    top = vc[vc == vc.max()].index
    return top[0] if len(top) == 1 else d[d["type_name"].isin(top)].sort_values("t")["type_name"].iloc[-1]


def ptype(a, b):
    return t[(t.t >= a) & (t.t <= b)].groupby("trade_area_code").apply(period_type, include_groups=False)


df = pd.DataFrame({
    "name": t.drop_duplicates("trade_area_code").set_index("trade_area_code")["trade_area_name"],
    "district": t.drop_duplicates("trade_area_code").set_index("trade_area_code")["district"],
    "base": t[t.t == BASE].set_index("trade_area_code")["type_name"],
    "p2024": ptype(9, 12),
    "actual_q": t[t.t == BASE + H].set_index("trade_area_code")["type_name"],
    "actual_y": ptype(13, 16),
}).join(prob[[f"p_{k}" for k in TYPES]])

# 비공간 전이확률 (t<=12)
g = gpd.GeoDataFrame(load_boundaries().merge(t[t.t <= BASE], on="trade_area_code"))
m = transition(g, "type", temporal_index="t", unit_index="trade_area_code", w_type=None)
P4 = np.linalg.matrix_power(np.asarray(m.p), H)
for j, k in enumerate(TYPES):
    df[f"a_{k}"] = df["base"].map({kk: P4[i, j] for i, kk in enumerate(TYPES)})

# ---------------------------------------------------------------- 1) 전체 유형 적중률
df["pred_persist"] = df["base"]
df["pred_spatial"] = df[[f"p_{k}" for k in TYPES]].idxmax(axis=1).str[2:]
df["pred_aspatial"] = df[[f"a_{k}" for k in TYPES]].idxmax(axis=1).str[2:]
rows = []
for target, lab in [("actual_q", "2025년 4분기 유형"), ("actual_y", "2025년 기간 유형")]:
    for pred, plab in [("pred_persist", "유형 유지"), ("pred_aspatial", "비공간 전이확률"), ("pred_spatial", "공간 모형")]:
        rows.append({"실제값": lab, "방법": plab, "적중률(%)": round((df[pred] == df[target]).mean() * 100, 1)})
acc = pd.DataFrame(rows)
acc.to_csv(os.path.join(OUT, "accuracy.csv"), index=False, encoding="utf-8-sig")
print(acc.to_string(index=False))
print("공간 모형 최빈 예측이 유형 유지와 같은 비율:", round((df.pred_spatial == df.pred_persist).mean() * 100, 1), "%")


# ---------------------------------------------------------------- 2) 경보 성능
def evaluate(name, cand, goal):
    rows = []
    for target, lab in [("actual_q", "2025년 4분기"), ("actual_y", "2025년 기간")]:
        y = (cand[target] == goal).astype(int)
        res = {"경보": name, "실제값": lab, "대상 상권": len(cand), "실제로 바뀐 상권": int(y.sum()),
               "기본 비율(%)": round(y.mean() * 100, 1)}
        for col, lab2 in [(f"p_{goal}", "공간"), (f"a_{goal}", "비공간")]:
            s = cand[col]
            res[f"AUC {lab2}"] = round(roc_auc_score(y, s), 3) if 0 < y.sum() < len(y) else np.nan
            for n in (20, 50):
                res[f"상위{n} 적중 {lab2}"] = int(y[s.sort_values(ascending=False, kind="mergesort").index[:n]].sum())
        res["AUC 유형 유지"] = 0.5
        rows.append(res)
    return rows


panel = pd.read_parquet("data/processed/geosnap_panel.parquet")
df["stores_recent"] = panel[(panel["t"] >= BASE - 3) & (panel["t"] <= BASE)].groupby("trade_area_code")["stores"].mean()
spread = df[df["p2024"].isin(LOW) & df["base"].isin(LOW) & (df["stores_recent"] >= MIN_STORES)]
over = df[(df["p2024"] == "청년상권형") & (df["base"] == "청년상권형") & (df["stores_recent"] >= MIN_STORES)]
warn = pd.DataFrame(evaluate("확산(→청년상권형)", spread, "청년상권형") + evaluate("과열(→고매출밀집형)", over, "고매출밀집형"))
warn.to_csv(os.path.join(OUT, "warning_performance.csv"), index=False, encoding="utf-8-sig")
print(warn.T.to_string())

# 상위 20 목록 (확산)
top = spread.sort_values("p_청년상권형", ascending=False).head(20)[["name", "district", "p2024", "base", "p_청년상권형", "actual_q", "actual_y"]]
top.to_csv(os.path.join(OUT, "spread_top20_2024Q4.csv"), encoding="utf-8-sig")
print(top.to_string())
topo = over.sort_values("p_고매출밀집형", ascending=False).head(20)[["name", "district", "p2024", "base", "p_고매출밀집형", "actual_q", "actual_y"]]
topo.to_csv(os.path.join(OUT, "overheat_top20_2024Q4.csv"), encoding="utf-8-sig")
print(topo.to_string())

# 검증 대상 상권 (설계서: 성수, 용리단길, 신당)
check = ["3110127", "3110132", "3110134", "3120044", "3110062", "3120039", "3110056", "3110057", "3110131", "3120052"]
c = df.loc[df.index.isin(check), ["name", "p2024", "base", "p_청년상권형", "p_고매출밀집형", "actual_q", "actual_y"]]
c.to_csv(os.path.join(OUT, "validation_areas.csv"), encoding="utf-8-sig")
print(c.round(3).to_string())
df.to_csv(os.path.join(OUT, "backtest_table.csv"), encoding="utf-8-sig")
