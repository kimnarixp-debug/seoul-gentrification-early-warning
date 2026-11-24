"""4단계-2: 상권 유형화(geosnap cluster)와 전이확률(geosnap transition).

설정 (근거: reports/step4_types.md)
- 표본: 21분기 연속 관측 1,418개 상권, 2022Q1~2026Q1 (17분기)
- 변수 7개, 표준화 std(전 기간 한 번에, pooling='fixed'), k-means, 유형 5개, random_state=0
- 공간 전이: w_type='knn', k=6

유형 이름은 군집 중심값을 보고 붙인 규칙(아래 name_types)으로 정한다. 군집 번호는
실행마다 바뀔 수 있어서 번호가 아니라 특성으로 이름을 찾는다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import numpy as np
import pandas as pd
from geosnap.analyze import cluster, transition
from seoul_to_geosnap import load_geosnap_input, VARIABLES, UNIT, TIME

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
COLS = list(VARIABLES)
K, SEED, KNN = 5, 0, 6

# 유형 이름 (뜨거운 순서). 숫자는 그림 색 순서로 쓴다.
TYPE_ORDER = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]


def name_types(med: pd.DataFrame) -> dict:
    """군집 중앙값 표 -> {군집번호: 유형 이름}. 규칙은 reports/step4_types.md 2절."""
    left = list(med.index)
    names = {}
    hot = med.loc[left, "sales_per_store"].idxmax(); names[hot] = "고매출밀집형"; left.remove(hot)
    dec = med.loc[left, "close_rate"].idxmax(); names[dec] = "쇠퇴형"; left.remove(dec)
    young = med.loc[left, "young_sales_share"].idxmax(); names[young] = "청년상권형"; left.remove(young)
    churn = med.loc[left, "open_rate"].idxmax(); names[churn] = "교체형"; left.remove(churn)
    names[left[0]] = "안정형"
    return names


gdf = load_geosnap_input(balanced_only=True, start_quarter="20221")
g = cluster(gdf, n_clusters=K, method="kmeans", columns=COLS, temporal_index=TIME, unit_index=UNIT,
            scaler="std", pooling="fixed", random_state=SEED)
med = g.groupby("kmeans")[COLS].median()
names = name_types(med)
g["type_name"] = g["kmeans"].map(names)
g["type"] = g["type_name"].map({n: i for i, n in enumerate(TYPE_ORDER)}).astype(int)

# 유형 표 저장
labels = g[[UNIT, TIME, "quarter_code", "trade_area_name", "trade_area_type", "district",
            "type", "type_name", "seongsu_core", "seongsu_area", *COLS]].copy()
labels.to_parquet(os.path.join(OUT, "types.parquet"), index=False)

profile = g.groupby("type_name")[COLS].median().reindex(TYPE_ORDER)
profile.insert(0, "비중(%)", (g["type_name"].value_counts(normalize=True) * 100).reindex(TYPE_ORDER))
profile.insert(1, "상권-분기 수", g["type_name"].value_counts().reindex(TYPE_ORDER))
profile.round(2).to_csv(os.path.join(OUT, "type_profile_median.csv"))
g.groupby("type_name")[COLS].mean().reindex(TYPE_ORDER).round(2).to_csv(os.path.join(OUT, "type_profile_mean.csv"))
print(profile.round(1).to_string())

# 전이확률: 비공간 / 공간(knn)
m = transition(g, "type", temporal_index=TIME, unit_index=UNIT, w_type=None)
P = pd.DataFrame(m.p, index=TYPE_ORDER, columns=TYPE_ORDER)
P.round(4).to_csv(os.path.join(OUT, "transition_global.csv"))
print("\n전이확률 (행: 이번 분기 -> 열: 다음 분기)\n", P.round(3).to_string())
counts = pd.DataFrame(m.transitions, index=TYPE_ORDER, columns=TYPE_ORDER).astype(int)
counts.to_csv(os.path.join(OUT, "transition_counts.csv"))

np.random.seed(SEED)
sm = transition(g, "type", temporal_index=TIME, unit_index=UNIT, w_type="knn", w_options={"k": KNN})
rows = []
for lag_i, lag_name in enumerate(TYPE_ORDER):
    Pi = pd.DataFrame(sm.P[lag_i], index=TYPE_ORDER, columns=TYPE_ORDER)
    Ni = pd.DataFrame(sm.T[lag_i], index=TYPE_ORDER, columns=TYPE_ORDER).astype(int)
    rows.append(Pi.assign(이웃유형=lag_name, 관측수=Ni.sum(axis=1).values).reset_index(names="이번분기"))
pd.concat(rows).round(4).to_csv(os.path.join(OUT, "transition_spatial_knn6.csv"), index=False)
print(f"\n공간 전이 검정 (주변 유형이 전이에 영향을 주는가): Q={sm.Q:.1f}, p={sm.Q_p_value:.4g}, "
      f"LR={sm.LR:.1f}, p={sm.LR_p_value:.4g}")
pd.Series({"Q": sm.Q, "Q_p": sm.Q_p_value, "LR": sm.LR, "LR_p": sm.LR_p_value, "k": KNN}).to_csv(
    os.path.join(OUT, "spatial_markov_test.csv"))

# 성수 기준 상권
s = labels[labels["seongsu_area"]].pivot(index="trade_area_name", columns="quarter_code", values="type_name")
s.to_csv(os.path.join(OUT, "seongsu_types.csv"))
print("\n성수 일대 유형\n", s.to_string())
