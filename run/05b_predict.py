"""5단계-2 (S7): 향후 4분기 유형 예측과 조기경보 확률.

geosnap predict_markov_labels는 한 번 부를 때마다 공간 전이확률(이웃 유형 조건부)에 따라
무작위로 한 번 뽑는 시뮬레이션이다. 같은 함수를 시드만 바꿔 N번 불러, 각 상권이
4분기 뒤(2027년 1분기)에 각 유형일 비율을 확률로 쓴다. 새로운 계산은 '비율 세기'뿐이다.

설정: base=t17(2026년 1분기), time_steps=4, increment=1, w_type='knn', k=6

사용법: python run/05b_predict.py reports/step5 [N=300] [base_t=17] [types_parquet]
  - base_t와 입력을 바꾸면 6단계 과거 검증에도 같은 스크립트를 쓴다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import geopandas as gpd
import numpy as np
import pandas as pd
from geosnap.analyze import predict_markov_labels
from seoul_to_geosnap import load_boundaries

OUT = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
BASE = int(sys.argv[3]) if len(sys.argv) > 3 else 17
SRC = sys.argv[4] if len(sys.argv) > 4 else "reports/step4/types.parquet"
STEPS = 4
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
os.makedirs(OUT, exist_ok=True)

t = pd.read_parquet(SRC)
t = t[t["t"] <= BASE]  # 기준 분기까지의 자료만으로 전이확률을 추정 (과거 검증 시 미래 정보 차단)
g = gpd.GeoDataFrame(load_boundaries().merge(t[["trade_area_code", "t", "type"]], on="trade_area_code"))

counts = None
for i in range(N):
    p = predict_markov_labels(g, unit_index="trade_area_code", temporal_index="t", cluster_col="type",
                              w_type="knn", w_options={"k": 6}, base_year=BASE, time_steps=STEPS,
                              increment=1, seed=i, verbose=False)
    last = p[p["t"] == BASE + STEPS].set_index("trade_area_code")["predicted"].astype(int)
    onehot = pd.get_dummies(last).reindex(columns=range(len(TYPES)), fill_value=0).astype(int)
    counts = onehot if counts is None else counts.add(onehot, fill_value=0)
    if (i + 1) % 50 == 0:
        print(f"{i + 1}/{N}", flush=True)

prob = (counts / N).rename(columns=dict(enumerate(TYPES)))
prob.columns = [f"p_{c}" for c in prob.columns]
prob["base_type"] = t[t["t"] == BASE].set_index("trade_area_code")["type_name"]
prob["n_sims"] = N
prob["base_t"] = BASE
prob.to_csv(os.path.join(OUT, f"predict_probs_base{BASE}.csv"), encoding="utf-8-sig")
print("saved", len(prob))
