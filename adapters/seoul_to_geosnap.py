"""3단계 어댑터: seoul_commerce 전처리 결과 -> geosnap 입력 (long-form GeoDataFrame).

설계서 S3: "업종을 상권 단위로 합산, 비율 변수 계산, 좌표 결합". 분석 알고리즘은 없다.

입력
- data/processed/seoul_commerce/english/commercial_quarter.csv  (분기 x 상권 x 외식업 10종)
- data/processed/seoul_commerce/english/segment_comparison.csv  (연령대별 매출)
- data/raw/seoul_opendata/OA-15560_trade_area_shp.zip          (상권 경계, EPSG:5181)

출력
- data/processed/geosnap_panel.parquet  : 상권 x 분기 속성표 (geometry 없음, 저장소에 커밋)
- load_geosnap_input()                  : 위 표 + 상권 경계를 붙인 GeoDataFrame을 돌려준다

변수 정의는 VARIABLES와 docs/variables.md 참고.

사용법:
    python adapters/seoul_to_geosnap.py
"""
from __future__ import annotations

import os

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC_OUT = os.path.join(ROOT, "data", "processed", "seoul_commerce", "english")
SHP_ZIP = os.path.join(ROOT, "data", "raw", "seoul_opendata", "OA-15560_trade_area_shp.zip")
PANEL = os.path.join(ROOT, "data", "processed", "geosnap_panel.parquet")

UNIT = "trade_area_code"      # geosnap unit_index
TIME = "t"                    # geosnap temporal_index (1, 2, 3... 순번. docs/api_notes.md 2절)

# 설계서 4절 유형화 변수 7개 (이름: 설명)
VARIABLES = {
    "sales_per_store": "점포당 분기 매출액(원) = 매출 합계 / 매출이 추정된 업종의 점포 수 합계",
    "sales_yoy": "전년 동기 대비 매출 증가율(%) = (이번 분기 매출 / 4분기 전 매출 - 1) x 100",
    "franchise_share": "프랜차이즈 점포 비중(%) = 프랜차이즈 점포 수 / 전체 점포 수 x 100",
    "open_rate": "개업률(%) = 개업 점포 수 / 전체 점포 수 x 100",
    "close_rate": "폐업률(%) = 폐업 점포 수 / 전체 점포 수 x 100",
    "young_sales_share": "20~30대 매출 비중(%) = 20대+30대 매출 / 연령대가 확인된 매출 x 100",
    "store_density": "점포 밀도(개/ha) = 전체 점포 수 / 상권 면적(ha)",
}

# RQ3 성수동 기준 상권 (docs/variables.md 3절)
SEONGSU_CORE = ["3110131", "3120052"]  # 성수동카페거리, 성수역
SEONGSU_AREA = [  # 성동구 성수·서울숲·뚝섬 일대 (지도 강조용)
    "3110120", "3110124", "3110126", "3110127", "3110131", "3110132", "3110134",
    "3110137", "3120050", "3120051", "3120052", "3130070", "3130071",
]


def _div(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a / b.where(b > 0)).astype("float64")


def build_panel() -> pd.DataFrame:
    cq = pd.read_csv(
        os.path.join(SC_OUT, "commercial_quarter.csv"),
        dtype={"quarter_code": str, "trade_area_code": str},
        usecols=["quarter_code", "trade_area_code", "trade_area_name", "trade_area_type_name",
                 "district_name", "area_ha", "has_sales", "quarterly_sales_amount",
                 "total_store_count", "franchise_store_count", "opened_store_count",
                 "closed_store_count"],
    )
    cq["stores_with_sales"] = cq["total_store_count"].where(cq["has_sales"].astype(bool), 0)
    keys = ["trade_area_code", "quarter_code"]
    p = cq.groupby(keys, as_index=False).agg(
        trade_area_name=("trade_area_name", "first"),
        trade_area_type=("trade_area_type_name", "first"),
        district=("district_name", "first"),
        area_ha=("area_ha", "first"),
        has_sales=("has_sales", "any"),
        sales=("quarterly_sales_amount", "sum"),
        stores=("total_store_count", "sum"),
        stores_with_sales=("stores_with_sales", "sum"),
        franchise=("franchise_store_count", "sum"),
        opened=("opened_store_count", "sum"),
        closed=("closed_store_count", "sum"),
    )
    p.loc[~p["has_sales"], "sales"] = np.nan

    # 연령대 매출 (외식업 10종 합계)
    seg = pd.read_csv(
        os.path.join(SC_OUT, "segment_comparison.csv"),
        dtype={"quarter_code": str, "trade_area_code": str, "segment_code": str},
        usecols=["quarter_code", "trade_area_code", "segment_type", "segment_code", "sales_amount"],
    )
    age = seg[seg["segment_type"] == "age"]
    age = age.groupby(keys).apply(
        lambda g: pd.Series({
            "age_sales_total": g["sales_amount"].sum(),
            "young_sales": g.loc[g["segment_code"].isin(["20", "30"]), "sales_amount"].sum(),
        }), include_groups=False,
    ).reset_index()
    p = p.merge(age, on=keys, how="left", validate="one_to_one")

    # 비율 변수
    p["sales_per_store"] = _div(p["sales"], p["stores_with_sales"])
    p["franchise_share"] = _div(p["franchise"], p["stores"]) * 100
    p["open_rate"] = _div(p["opened"], p["stores"]) * 100
    p["close_rate"] = _div(p["closed"], p["stores"]) * 100
    p["young_sales_share"] = _div(p["young_sales"], p["age_sales_total"]) * 100
    p["store_density"] = _div(p["stores"], p["area_ha"])

    # 시간 순번과 전년 동기 대비 증가율
    quarters = sorted(p["quarter_code"].unique())
    p[TIME] = p["quarter_code"].map({q: i + 1 for i, q in enumerate(quarters)}).astype(int)
    p["year"] = p["quarter_code"].str[:4].astype(int)
    p["qtr"] = p["quarter_code"].str[4].astype(int)
    p = p.sort_values([UNIT, TIME]).reset_index(drop=True)
    prev = p[[UNIT, TIME, "sales"]].assign(**{TIME: p[TIME] + 4}).rename(columns={"sales": "sales_4q_ago"})
    p = p.merge(prev, on=[UNIT, TIME], how="left")
    p["sales_yoy"] = (_div(p["sales"], p["sales_4q_ago"]) - 1) * 100

    # 표본 표시
    obs = p.assign(ok=p["has_sales"] & (p["stores"] > 0)).groupby(UNIT)["ok"].sum()
    p["balanced_panel"] = p[UNIT].map(obs == len(quarters))
    p["complete_vars"] = p[list(VARIABLES)].notna().all(axis=1)
    p["seongsu_core"] = p[UNIT].isin(SEONGSU_CORE)
    p["seongsu_area"] = p[UNIT].isin(SEONGSU_AREA)

    cols = [UNIT, TIME, "quarter_code", "year", "qtr", "trade_area_name", "trade_area_type", "district",
            "area_ha", *VARIABLES, "sales", "sales_4q_ago", "stores", "stores_with_sales", "franchise",
            "opened", "closed", "young_sales", "age_sales_total", "has_sales", "balanced_panel",
            "complete_vars", "seongsu_core", "seongsu_area"]
    return p[cols]


def load_boundaries() -> gpd.GeoDataFrame:
    g = gpd.read_file(f"zip://{SHP_ZIP}")[["TRDAR_CD", "geometry"]]
    return g.rename(columns={"TRDAR_CD": UNIT}).assign(**{UNIT: lambda d: d[UNIT].astype(str)})


def load_geosnap_input(panel_path: str = PANEL, balanced_only: bool = False,
                       start_quarter: str | None = None) -> gpd.GeoDataFrame:
    """geosnap 함수에 넘길 long-form GeoDataFrame (EPSG:5181, 상권 경계 면).

    balanced_only=True면 21분기 연속 관측 상권만, start_quarter='20221'이면 그 분기부터.
    시간 순번 t는 잘라낸 뒤 1부터 다시 매긴다.
    """
    p = pd.read_parquet(panel_path)
    if balanced_only:
        p = p[p["balanced_panel"]]
    if start_quarter:
        p = p[p["quarter_code"] >= start_quarter].copy()
        p[TIME] = p[TIME] - p[TIME].min() + 1
    g = load_boundaries().merge(p, on=UNIT, how="inner", validate="one_to_many")
    return gpd.GeoDataFrame(g, geometry="geometry", crs=load_boundaries().crs)


if __name__ == "__main__":
    panel = build_panel()
    panel.to_parquet(PANEL, index=False)
    print(f"저장: {PANEL} ({len(panel):,}행, 상권 {panel[UNIT].nunique():,}, 분기 {panel[TIME].max()})")
