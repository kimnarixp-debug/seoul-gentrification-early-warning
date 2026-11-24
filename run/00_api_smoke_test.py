"""0단계: geosnap 함수 호출 방식 점검 (분석 아님).

무작위로 만든 가짜 점 데이터(상권 60개 x 8분기)로 아래를 확인한다.
- temporal_index='quarter'(1,2,3… 순번), unit_index='trade_area_code' 지정 시 동작 여부
- 점 좌표에서 w_type='knn' 공간 가중치 동작 여부
- predict_markov_labels의 base_year + increment 계산 방식
결과 수치는 의미가 없다. 호출이 되는지만 본다.
"""
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import Point
from geosnap.analyze import find_k, cluster, transition, sequence, predict_markov_labels, lincs_from_gdf

rng = np.random.default_rng(0)
n, T = 60, 8
pts = [Point(xy) for xy in rng.uniform(0, 10000, size=(n, 2))]
rows = []
for q in range(1, T + 1):
    for i in range(n):
        rows.append(dict(trade_area_code=f"A{i:03d}", quarter=q, geometry=pts[i],
                         v1=rng.normal(), v2=rng.normal(), v3=rng.normal()))
gdf = gpd.GeoDataFrame(rows, crs="EPSG:5181")
kw = dict(temporal_index="quarter", unit_index="trade_area_code")
cols = ["v1", "v2", "v3"]

tbl = find_k(gdf, method="kmeans", columns=cols, min_k=2, max_k=5, return_table=True, **kw)
print("find_k OK:", type(tbl).__name__)
g = cluster(gdf, n_clusters=4, method="kmeans", columns=cols, random_state=0, **kw)
print("cluster OK, 새 컬럼:", [c for c in g.columns if c not in gdf.columns])
m = transition(g, "kmeans", w_type=None, **kw); print("transition(비공간) OK", m.p.shape)
sm = transition(g, "kmeans", w_type="knn", w_options={"k": 5}, **kw); print("transition(knn) OK", len(sm.P))
g2, wide, d = sequence(g, "kmeans", seq_clusters=3, dist_type="hamming", **kw)
print("sequence OK, wide 컬럼:", list(wide.columns))
p = predict_markov_labels(g, cluster_col="kmeans", w_type="knn", w_options={"k": 5},
                          base_year=T, time_steps=4, increment=1, seed=0, verbose=False, **kw)
print("predict_markov_labels OK, 예측 시점:", sorted(p["quarter"].unique()))
l = lincs_from_gdf(g, unit_index="trade_area_code", temporal_index="quarter", cluster_col="kmeans")
print("lincs_from_gdf OK", l.shape)
