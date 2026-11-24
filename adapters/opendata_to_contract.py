"""서울 열린데이터광장에서 내려받은 원자료를 seoul_commerce 수집기 출력 형식으로 바꾼다.

배경: 이 실행 환경에서는 seoul_commerce 수집기가 쓰는 서울시 Open API
(openapi.seoul.go.kr:8088)에 접속할 수 없다. 그래서 같은 데이터셋을 열린데이터광장
파일/시트 다운로드로 받았고, 이 스크립트는 그 파일을 수집기가 만들었을 CSV와 같은
형식(external/seoul_commerce/config/data_contracts.yml)으로 맞춘다.

하는 일 (값은 바꾸지 않는다):
1. 한국어 컬럼명 -> Open API 영문 컬럼명 (seoul_commerce의 column_mapping_ko.yml을 역으로 사용)
2. 계약서의 required_columns만 남기고 관리 컬럼 4개 추가 (수집기 collector.py와 같은 규칙)
3. 연도별 파일(2021~2025)과 시트(2025~최신)를 합친다. 겹치는 분기는 연도별 파일을 쓴다.
4. utf-8-sig로 저장 (수집기와 같은 인코딩)

사용법:
    python adapters/opendata_to_contract.py data/raw/seoul_opendata data/raw/contract
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys
import zipfile
from datetime import datetime

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC_CONFIG = os.path.join(ROOT, "external", "seoul_commerce", "config")

# 열린데이터광장 원본 헤더 중 seoul_commerce 한국어 명칭과 규칙으로 맞지 않는 것 (직접 확인)
EXPLICIT = {
    "점포_수": "일반_점포_수",  # 점포_수 + 프랜차이즈_점포_수 = 유사_업종_점포_수 (2024년 자료에서 100% 성립 확인)
    "폐업_률": "폐업_율",
    "전체_점포_수": "유사_업종_점포_수",  # 시트 표기. 2025년 연도별 파일의 similr_induty_stor_co와 값 100% 일치 확인
    # 원본 시트의 건수 시간대 헤더가 '시간대_건수~06' 형태로 깨져 있음. 금액 열과 같은 순서
    "시간대_건수~06_매출_건수": "시간대_00_06_매출_건수",
    "시간대_건수~11_매출_건수": "시간대_06_11_매출_건수",
    "시간대_건수~14_매출_건수": "시간대_11_14_매출_건수",
    "시간대_건수~17_매출_건수": "시간대_14_17_매출_건수",
    "시간대_건수~21_매출_건수": "시간대_17_21_매출_건수",
    "시간대_건수~24_매출_건수": "시간대_21_24_매출_건수",
}

# 영역-상권 shapefile의 dbf 필드명은 10자로 잘려 있다
SHP_FIELDS = {
    "TRDAR_SE_C": "TRDAR_SE_CD", "TRDAR_SE_1": "TRDAR_SE_CD_NM", "TRDAR_CD": "TRDAR_CD",
    "TRDAR_CD_N": "TRDAR_CD_NM", "XCNTS_VALU": "XCNTS_VALUE", "YDNTS_VALU": "YDNTS_VALUE",
    "SIGNGU_CD": "SIGNGU_CD", "SIGNGU_CD_": "SIGNGU_CD_NM", "ADSTRD_CD": "ADSTRD_CD",
    "ADSTRD_CD_": "ADSTRD_CD_NM", "RELM_AR": "RELM_AR",
}

# 데이터셋 -> (계약서 키, 연도별 zip 패턴, 시트 파일)
SOURCES = {
    "stores": ("OA-15577_stores_*.zip", "OA-15577_stores_sheet.csv.gz"),
    "sales": ("OA-15572_sales_*.zip", "OA-15572_sales_sheet.csv.gz"),
    "floating_population": (None, "OA-15568_floating_population_sheet.csv.gz"),
    "resident_population": (None, "OA-15584_resident_population_sheet.csv.gz"),
    "working_population": (None, "OA-15569_working_population_sheet.csv.gz"),
}


def _norm(name: str) -> str:
    """원본 한국어 헤더를 seoul_commerce 한국어 명칭 표기로 맞춘 뒤 비교용으로 정규화."""
    name = EXPLICIT.get(name, name)
    name = name.replace("당월_매출", "분기_매출").replace("직장_인구", "직장인구")
    name = re.sub(r"시간대_(\d\d)~(\d\d)", r"시간대_\1_\2", name)
    name = re.sub(r"(남성|여성)연령대_(\d+)", r"\1_\2대", name)
    name = re.sub(r"연령대_(\d+)", r"\1대", name)
    return re.sub(r"[_\s]", "", name)


def _rename_map(dataset: str, header: list[str], required: list[str], ko: dict) -> dict:
    # 2025년 점포 파일처럼 헤더가 이미 Open API 영문명(소문자)인 경우
    if all(c.lower() in header for c in required):
        return {c.lower(): c for c in required}
    api_to_ko = {**ko["common"], **ko.get(dataset, {})}
    by_norm = {_norm(h): h for h in header}
    mapping, missing = {}, []
    for api in required:
        src = by_norm.get(re.sub(r"[_\s]", "", api_to_ko.get(api, "")))
        if src is None:
            missing.append(api)
        else:
            mapping[src] = api
    if missing:
        raise ValueError(f"{dataset}: 원본에서 찾지 못한 필수 컬럼 {missing}")
    return mapping


def _read_csv(data: bytes | str) -> pd.DataFrame:
    src = io.BytesIO(data) if isinstance(data, bytes) else data
    return pd.read_csv(src, encoding="cp949", dtype=str, keep_default_na=False)


def _add_management(df: pd.DataFrame, ds: dict, schema_version: str, collected_at: str) -> pd.DataFrame:
    df["SOURCE_DATASET_ID"] = ds["dataset_id"]
    df["COLLECTED_AT"] = collected_at
    if "STDR_YYQU_CD" in df.columns:
        df["SOURCE_BASE_DATE"] = df["STDR_YYQU_CD"].astype("string")
    else:
        df["SOURCE_BASE_DATE"] = ds.get("reported_source_base_date", pd.NA)
    df["SCHEMA_VERSION"] = schema_version
    return df


def convert(raw_dir: str, out_dir: str) -> dict[str, pd.DataFrame]:
    con = yaml.safe_load(open(os.path.join(SC_CONFIG, "data_contracts.yml"), encoding="utf-8"))
    ko = yaml.safe_load(open(os.path.join(SC_CONFIG, "column_mapping_ko.yml"), encoding="utf-8"))
    collected_at = datetime.now().astimezone().isoformat(timespec="seconds")
    os.makedirs(out_dir, exist_ok=True)
    report = {}

    # 1) 영역-상권: shapefile 속성표
    import geopandas as gpd
    shp = os.path.join(raw_dir, "OA-15560_trade_area_shp.zip")
    g = gpd.read_file(f"zip://{shp}")
    ds = con["datasets"]["trade_area"]
    ta = pd.DataFrame(g.drop(columns="geometry")).rename(columns=SHP_FIELDS)[ds["required_columns"]]
    ta = _add_management(ta, ds, con["schema_version"], collected_at)
    ta.to_csv(os.path.join(out_dir, "trade_area.csv"), index=False, encoding="utf-8-sig")
    report["trade_area"] = ta

    # 2) 분기 자료
    for name, (zip_pattern, sheet) in SOURCES.items():
        ds = con["datasets"][name]
        def to_api(raw: pd.DataFrame) -> pd.DataFrame:
            mapping = _rename_map(name, list(raw.columns), ds["required_columns"], ko)
            return raw[list(mapping)].rename(columns=mapping)[ds["required_columns"]]

        frames = []  # 파일마다 헤더 표기가 달라서 각각 영문명으로 바꾼 뒤 합친다
        if zip_pattern:
            for z in sorted(glob.glob(os.path.join(raw_dir, zip_pattern))):
                with zipfile.ZipFile(z) as zf:
                    (member,) = [m for m in zf.namelist() if m.lower().endswith(".csv")]
                    frames.append(to_api(_read_csv(zf.read(member))))
        yearly_quarters = set(pd.concat(frames)["STDR_YYQU_CD"]) if frames else set()
        sh = to_api(_read_csv(os.path.join(raw_dir, sheet)))
        frames.append(sh.loc[~sh["STDR_YYQU_CD"].isin(yearly_quarters)])
        df = pd.concat(frames, ignore_index=True)
        df = _add_management(df, ds, con["schema_version"], collected_at)
        df = df.sort_values(["STDR_YYQU_CD", "TRDAR_CD"] + (["SVC_INDUTY_CD"] if "SVC_INDUTY_CD" in df else []))
        df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False, encoding="utf-8-sig")
        report[name] = df
    return report


if __name__ == "__main__":
    raw_dir, out_dir = sys.argv[1], sys.argv[2]
    for name, df in convert(raw_dir, out_dir).items():
        q = sorted(df["STDR_YYQU_CD"].unique()) if "STDR_YYQU_CD" in df else []
        span = f"{q[0]}~{q[-1]} ({len(q)}개 분기)" if q else "-"
        print(f"{name:22s} 행 {len(df):>9,}  상권 {df['TRDAR_CD'].nunique():>5,}  분기 {span}")
