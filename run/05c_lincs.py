"""5단계-3 (S8): 변화 핫스팟. geosnap lincs_from_gdf (Local Indicator of Neighborhood Change, Rey 2011).

LINC(0~1): 한 상권과 "같은 유형으로 묶이는 상권들"의 구성이 기간 사이에 얼마나 바뀌었나.
분기 유형은 출렁임이 커서 두 가지로 계산한다.
  (a) 기간 유형 3개 (2022년 / 2024년 / 최근 1년, 각 기간 최빈 유형) -> 주 결과
  (b) 분기 유형 17개 -> 참고
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import geopandas as gpd
import pandas as pd
from geosnap.analyze import lincs_from_gdf
from seoul_to_geosnap import load_boundaries

OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/step5"
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
b = load_boundaries()

period = pd.read_csv("reports/step4/period_types.csv", dtype={"trade_area_code": str}).set_index("trade_area_code")
long = period[["2022년", "2024년", "최근 1년"]].stack().rename("type_name").reset_index()
long.columns = ["trade_area_code", "period", "type_name"]
long["type"] = long["type_name"].map({k: i for i, k in enumerate(TYPES)})
long["p"] = long["period"].map({"2022년": 1, "2024년": 2, "최근 1년": 3})
gp = gpd.GeoDataFrame(b.merge(long, on="trade_area_code"))
la = lincs_from_gdf(gp, unit_index="trade_area_code", temporal_index="p", cluster_col="type")

t = pd.read_parquet("reports/step4/types.parquet")
gq = gpd.GeoDataFrame(b.merge(t[["trade_area_code", "t", "type"]], on="trade_area_code"))
lq = lincs_from_gdf(gq, unit_index="trade_area_code", temporal_index="t", cluster_col="type")

res = period.join(la.set_index("trade_area_code")["linc"].rename("linc_period")) \
            .join(lq.set_index("trade_area_code")["linc"].rename("linc_quarter"))
res.to_csv(os.path.join(OUT, "lincs.csv"), encoding="utf-8-sig")
print(res[["linc_period", "linc_quarter"]].describe().round(3).to_string())
print("\n기간 LINC 상위 20")
print(res.sort_values("linc_period", ascending=False).head(20)[
    ["trade_area_name", "district", "2022년", "2024년", "최근 1년", "linc_period"]].to_string())
print("\n유형 경로별 평균 기간 LINC")
res["path"] = res["2022년"] + "→" + res["최근 1년"]
print(res.groupby("path")["linc_period"].agg(["count", "mean"]).sort_values("mean", ascending=False).round(3).head(12).to_string())
