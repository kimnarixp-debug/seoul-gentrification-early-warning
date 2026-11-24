"""2단계: seoul_commerce 전처리를 집객시설(OA-15580) 없이 실행한다.

seoul_commerce의 run_preprocessing()과 같은 순서로 같은 함수를 부른다. 다른 점은 하나:
집객시설 원본을 읽는 대신 "행이 0개인 표"를 넘긴다. 그러면 seoul_commerce 코드가
스스로 has_facilities=False, 시설 수=결측으로 기록한다(값을 지어내지 않는다).
external/ 코드는 수정하지 않는다. 자세한 내용: docs/changes_from_upstream.md

실행 (seoul_commerce 가상환경에서):
    cd external/seoul_commerce
    uv run python ../../run/02_preprocess.py ../../data/raw/contract ../../data/processed/seoul_commerce
"""
import os
import sys

import pandas as pd
from seoul_commerce import preprocessing as P

input_dir, out_dir = (os.path.abspath(p) for p in sys.argv[1:3])
industry_codes = P.SELECTED_INDUSTRY_CODES

# 원 함수 load_source_data()는 7종을 모두 요구하므로, 같은 내부 함수를 6종에만 적용
source = {
    name: P._read_source_csv(name, input_dir, tuple(industry_codes), 200_000)
    for name in P.SOURCE_DATASET_NAMES if name != "facilities"
}
# 집객시설: 원본과 같은 컬럼 구성의 빈 표 (seoul_commerce 설정에서 컬럼명을 그대로 가져옴)
fac_columns = list(dict.fromkeys([*P._source_mapping("facilities").values()]))
source["facilities"] = P.optimize_dtypes(
    pd.DataFrame({c: pd.Series(dtype="string") for c in fac_columns}), "facilities"
)

# 이하 run_preprocessing() 본문과 동일
master = P.build_trade_area_master(source["trade_area"])
area = P.build_area_quarter(
    source["floating_population"], source["resident_population"],
    source["working_population"], source["facilities"], master,
)
commercial = P.build_commercial_quarter(source["stores"], source["sales"], area, industry_codes)
segments = P.build_segment_comparison(source["sales"], source["floating_population"], master, industry_codes)
datasets = {
    "trade_area_master": master, "area_quarter": area,
    "commercial_quarter": commercial, "segment_comparison": segments,
}
datasets["data_quality"] = P.build_data_quality(datasets)
for name, frame in datasets.items():
    output = P.OUTPUTS[name]
    P.write_csv_pair(frame, output["english_filename"], output["korean_filename"],
                     os.path.join(out_dir, "english"), os.path.join(out_dir, "korean"))
    print(f"저장: {output['english_filename']} ({len(frame):,}행)")
