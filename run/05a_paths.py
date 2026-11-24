"""5단계-1 (S6): 변화 경로 군집과 "성수와 같은 경로" 상권 (RQ3).

- geosnap sequence(dist_type='hamming', seq_clusters=6): 17분기 유형 순서열을 군집
- 같은 함수가 돌려주는 상권 간 경로 거리표(해밍 거리 = 17분기 중 유형이 다른 분기 수)로
  성수 주변 기준 7곳과의 평균 거리를 구해 순위를 매긴다 (정렬만, 새 계산 없음)
- geosnap indexplot_seq로 경로 군집 그림

성수 기준 경로 (4단계 결정): 2022년 안정·교체형 -> 최근 1년 청년상권형으로 바뀐 성수 주변 7곳
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from geosnap.analyze import sequence
from geosnap.visualize import indexplot_seq
from seoul_to_geosnap import load_boundaries

OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/step5"
FIG = sys.argv[2] if len(sys.argv) > 2 else "reports/figures/step5"
os.makedirs(OUT, exist_ok=True); os.makedirs(FIG, exist_ok=True)
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
K = 6

t = pd.read_parquet("reports/step4/types.parquet")
moved = pd.read_csv("reports/step4/moved_up.csv", index_col=0, dtype=str)
REF = moved[(moved["구분"] == "안정·교체·쇠퇴→청년상권형") & (moved["district"] == "성동구")
            & moved["trade_area_name"].str.contains("성수|성원|경수|금북|성동구보건소")].index.tolist()
g = gpd.GeoDataFrame(load_boundaries().merge(t, on="trade_area_code"))

gn, wide, D = sequence(g, "type", seq_clusters=K, dist_type="hamming", temporal_index="t",
                       unit_index="trade_area_code")
col = f"hamming_{K}"
qcols = [c for c in wide.columns if c != col]
D = pd.DataFrame(D, index=wide.index, columns=wide.index)

# 경로 군집 이름: 전 기간 유형 구성으로 정한다
names = {}
for c in sorted(wide[col].unique()):
    vals = pd.Series(wide.loc[wide[col] == c, qcols].values.ravel()).map(dict(enumerate(TYPES)))
    share = vals.value_counts(normalize=True)
    top, s1 = share.index[0], share.iloc[0]
    names[c] = f"{top} 지속" if s1 >= 0.9 else (f"{top} 중심" if s1 >= 0.6 else f"{top}·{share.index[1]} 혼합")
prof = []
for c, nm in names.items():
    sub = wide[wide[col] == c]
    row = {"경로군집": c, "이름": nm, "상권 수": len(sub)}
    for k, ty in enumerate(TYPES):
        row[f"{ty}(%)"] = round((sub[qcols].values == k).mean() * 100, 1)
    row["평균 유형 변경 횟수"] = round((sub[qcols].diff(axis=1).iloc[:, 1:] != 0).sum(axis=1).mean(), 1)
    row["성수 기준 7곳 포함"] = int(sub.index.isin(REF).sum())
    prof.append(row)
prof = pd.DataFrame(prof)
prof.to_csv(os.path.join(OUT, "path_clusters.csv"), index=False, encoding="utf-8-sig")
print(prof.to_string(index=False))

units = t.drop_duplicates("trade_area_code").set_index("trade_area_code")[["trade_area_name", "district", "trade_area_type"]]
out = wide[[col]].rename(columns={col: "path_cluster"}).join(units)
out["path_name"] = out["path_cluster"].map(names)
out["seq"] = wide[qcols].apply(lambda r: "".join(str(int(v)) for v in r), axis=1)
out.to_csv(os.path.join(OUT, "path_labels.csv"), encoding="utf-8-sig")

# 성수 기준 7곳과의 경로 거리 (기준 7곳 제외)
dist = D.loc[:, REF].mean(axis=1).rename("성수기준_평균거리")
# 출발점이 같은 상권만 (2022년 기간 유형이 안정·교체형). 이 조건이 없으면 처음부터 청년상권형인 상권이 상위를 차지한다
period = pd.read_csv("reports/step4/period_types.csv", index_col=0, dtype={"trade_area_code": str})
period.index = period.index.astype(str)
same_start = period.index[period["2022년"].isin(["안정형", "교체형"])]
rank = out.join(dist).join(period[["2022년", "2024년", "최근 1년"]]).drop(index=REF)
rank_all = rank.sort_values("성수기준_평균거리")
rank = rank[rank.index.isin(same_start)].sort_values("성수기준_평균거리")
rank_all.head(50).to_csv(os.path.join(OUT, "seongsu_like_paths_all.csv"), encoding="utf-8-sig")
rank.head(50).to_csv(os.path.join(OUT, "seongsu_like_paths.csv"), encoding="utf-8-sig")
print("\n성수 기준 7곳:", ", ".join(units.loc[REF, "trade_area_name"]))
print("기준 7곳의 서로 간 평균 거리:", round(D.loc[REF, REF].values[np.triu_indices(len(REF), 1)].mean(), 2))
print(rank.head(25)[["trade_area_name", "district", "path_name", "seq", "성수기준_평균거리", "최근 1년"]].to_string())
print("\n상위 25곳 중 최근 1년 청년상권형:", (rank.head(25)["최근 1년"] == "청년상권형").sum())

# geosnap indexplot_seq 그림 (원 함수 그대로)
plt.rcParams["font.family"] = ["NanumSquare", "NanumGothic"]
w2 = wide.copy()
w2.columns = [str(c) for c in w2.columns]
indexplot_seq(w2, clustering=col, years=[str(c) for c in qcols], ncols=3, palette="pastel",
              save_fig=os.path.join(FIG, "path_clusters_geosnap.png"), dpi=150)
plt.close("all")
print("saved")
