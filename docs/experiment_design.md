# "다음 성수동은 어디인가" — 서울시 상권 젠트리피케이션 조기경보 실험설계 (v3)

> 작성 기준일: 2026-11-24 · 대상지: 서울특별시 전역 · 실행 도구: Claude Code + GitHub
> 작업 저장소: https://github.com/kimnarixp-debug/seoul-gentrification-early-warning
>
> 원 프롬프트: "최근 **상권 젠트리피케이션 조기경보** 연구를 위해서 최근 연구된 이론이나 알고리즘 서치하고, 국내 서울을 중심으로 추진하기 위한 code generator 실험설계를 md로 만들어줘."

## 0. 원칙: 새로 만들지 않는다

**분석 로직과 알고리즘은 GitHub에 공개된 것을 그대로 쓴다.** 직접 하는 일은 세 가지뿐이다.

1. 서울 데이터를 기존 코드가 요구하는 입력 형식으로 바꾼다 (어댑터 1개).
2. 기존 코드를 설정값만 바꿔 실행한다.
3. 결과를 시각화한다 (기존 코드의 시각화 함수 우선).

원 코드에서 바꾼 부분은 전부 `docs/changes_from_upstream.md`에 기록한다.

---

## 1. 연구 질문

- **RQ1**: 서울 상권은 매출·점포 구성 기준으로 몇 가지 유형으로 나뉘며, 2021년 이후 유형 간 이동(전이)은 어떤 패턴인가?
- **RQ2**: "과열형"으로 넘어갈 확률이 높은 상권은 어디인가? (조기경보)
- **RQ3**: 성수동 상권과 같은 변화 경로를 밟는 상권은 어디인가?

---

## 2. 사용할 GitHub 저장소 (2026-11-24 직접 확인)

### 2.1 채택

| 역할 | 저장소 | 확인 내용 | 그대로 쓰는 것 |
|---|---|---|---|
| **분석 엔진** | [oturns/geosnap](https://github.com/oturns/geosnap) | ★279, BSD-3-Clause, 2026-03 갱신, PyPI v0.17.0 설치 확인 | 유형화, 경로 군집, 전이확률, 미래 유형 예측, 지도·애니메이션 |
| **서울 데이터 수집·전처리** | [scksh/seoul_commerce](https://github.com/scksh/seoul_commerce) | ★22, 2026-11 갱신. README에 "소스 코드는 MIT License" 명시 (단, LICENSE 파일은 저장소에 없음) | 서울 열린데이터광장 상권분석서비스 7종 수집기, 전처리, 컬럼 사전, 상권 마스터(1,650개 상권 좌표) |

**geosnap**: 근린 변화 분석 전용 패키지. 미국 센서스 예제가 기본이지만 임의 지역의 long-form GeoDataFrame을 받는다. 근거 문헌은 Knaap & Rey (2024, SciPy Proceedings), 방법론 계보는 Delmelle (2016, *AAAG*)의 변화 경로 군집.

**seoul_commerce**: 이 연구와 같은 원자료(서울시 상권분석서비스)를 쓰는 프로젝트. 분석 범위가 2021년 1분기~2026년 1분기, 외식업 10개 업종(`CS100001`~`CS100010`)으로 설정되어 있다. 산출물 `data/analysis/english/commercial_quarter.csv`(분기 × 상권 × 업종)가 geosnap 입력에 거의 그대로 맞는다. 저장소에 `data/raw/trade_area.csv`(상권 마스터)가 이미 들어 있다.

### 2.2 참고만 하는 저장소

| 저장소 | 내용 | 채택하지 않는 이유 |
|---|---|---|
| [chaeni1105/gentrification](https://github.com/chaeni1105/gentrification) | 서울 상권 2019~2022, 입지계수(LQ) 변화로 젠트리피케이션 지수 산출 | 라이선스 없음. 지수 정의 아이디어만 인용 |
| [HojunJangSkku/Understanding-the-Commercial-gentrification-in-Seoul](https://github.com/HojunJangSkku/Understanding-the-Commercial-gentrification-in-Seoul) | 서울 400m 격자, 다중과제 신경망 + 설명가능 AI (2017년 기준 자료) | 라이선스 없음, 학습 코드 없이 자료와 가중치만 공개 |
| [jreades/urb-studies-predicting-gentrification](https://github.com/jreades/urb-studies-predicting-gentrification) | 런던, 랜덤포레스트 예측 (★46, MIT, *Urban Studies* 2019) | 2019년 이후 갱신 없음, 센서스 10년 주기 전제. 시간이 남으면 선택 과제 |
| [urban-displacement/displacement-typologies](https://github.com/urban-displacement/displacement-typologies) | 미국 Urban Displacement Project 유형 지도 (★50, GPL-3.0) | 미국 센서스 변수 전용 |

### 2.3 이론 배경 (발표용)
- Mueller, Hoque & Pearsall (2024), *CEUS* 111: 젠트리피케이션 ML 연구 종합 리뷰.
- Delmelle (2016), *AAAG* 106(1): 두 시점 비교가 아니라 변화 경로를 군집화. geosnap `sequence`가 이 계열.
- Reades, De Souza & Hubbard (2019), *Urban Studies* 56(5): 코드·데이터를 공개한 예측 연구의 대표 사례.
- 김경선·김동섭 (2019), 한국콘텐츠학회논문지 19(2): 서울 158개 상권 로짓 + 기계학습.
- 공백: 서울 전체 상권에 전이확률 기반 조기경보를 적용한 사례는 검색 범위 내에서 찾지 못함.

---

## 3. 서울 데이터

서울 열린데이터광장 "서울시 상권분석서비스" (공공누리 제1유형, 출처표시)

| 데이터 | ID | 용도 |
|---|---|---|
| 영역-상권 | OA-15560 | 상권 좌표, 구분, 면적 |
| 점포-상권 | OA-15577 | 점포수, 개폐업, 프랜차이즈 |
| 추정매출-상권 | OA-15572 | 매출, 연령대·요일·시간대별 매출 |
| 길단위인구-상권 | OA-15568 | 유동인구 (선택) |

**제약**
- 추정매출은 2021년 이후분만 제공된다(2024년 공간 단위 개편, 2026-07-03 적용). 약 21분기.
- 상권 위치는 경계가 아니라 점 좌표(`XCNTS_VALUE`, `YDNTS_VALUE`)다. → geosnap 공간 가중치는 `w_type="knn"`을 쓴다.

**수집 경로 (위에서부터 시도)**
1. seoul_commerce 수집기: 서울 열린데이터광장 인증키(무료)를 `.env`에 넣고 `uv run seoul-commerce sales --quarter 20211` 식으로 수집.
2. 실행 환경에서 서울시 API 접속이 막혀 있으면: 사용자가 CSV를 직접 내려받아 저장소 `data/raw/`에 올린다. 파일명과 컬럼은 seoul_commerce의 `config/data_contracts.yml` 형식에 맞춘다.

원자료는 공개 데이터이므로 저장소에 포함한다(파일당 100MB 미만 확인).

---

## 4. 실험 절차

| 단계 | 사용 코드 | 입력 → 출력 |
|---|---|---|
| S1 수집 | seoul_commerce `collector` | API → `data/raw/*.csv` |
| S2 전처리 | seoul_commerce `preprocessing` | raw → `commercial_quarter.csv` |
| S3 어댑터 (직접 작성) | - | 업종을 상권 단위로 합산, 비율 변수 계산, 좌표 결합 → long-form GeoDataFrame (`trade_area_code`, `quarter`, `geometry`, 변수) |
| S4 유형화 | geosnap `find_k`, `cluster` | 상권 유형 k개. 유형 이름은 군집 중심값을 보고 사람이 붙임 (예: 침체형, 안정형, 성장형, 과열형) |
| S5 전이 | geosnap `transition` | 유형 간 전이확률 (주변 상권 유형에 따른 조건부 포함) |
| S6 경로 | geosnap `sequence` | 변화 경로 군집 → 성수동과 같은 경로의 상권 목록 |
| S7 예측 | geosnap `predict_markov_labels` | 향후 4분기 유형 → 과열형 전이 예상 상권 |
| S8 핫스팟 | geosnap `lincs_from_gdf` | 변화가 유난히 큰 상권 |
| S9 시각화 | geosnap `visualize` + folium | 5장 그림 |

**유형화 변수** (원자료의 단순 비율·증가율만)
점포당 매출, 전년 동기 대비 매출 증가율, 프랜차이즈 점포 비중, 개업률, 폐업률, 20~30대 매출 비중, 점포 밀도

**검증**
- 과거 검증: 2024년 4분기까지의 자료로 2025년 유형을 예측하고 실제와 비교. 비교 기준은 "유형이 그대로 유지된다".
- 타당성: 언론·선행연구가 과열로 지목한 상권(성수, 용리단길, 신당 등)이 과열형 또는 전이 예상에 잡히는지 확인.

### 4.1 확인된 geosnap 함수 (v0.17.0)

시간·단위 인자의 기본값이 `year`, `geoid`이므로 **반드시 명시**한다.

```python
from geosnap.analyze import find_k, cluster, transition, sequence, predict_markov_labels, lincs_from_gdf
from geosnap.visualize import plot_timeseries, animate_timeseries, plot_transition_matrix

cluster(gdf, n_clusters=6, method=None, columns=None, temporal_index='year', unit_index='geoid',
        scaler='std', pooling='fixed', random_state=None, return_model=False)
find_k(gdf, method=None, columns=None, temporal_index='year', unit_index='geoid', min_k=2, max_k=10)
transition(gdf, cluster_col, temporal_index='year', unit_index='geoid', w_type='rook', w_options=None)
sequence(gdf, cluster_col, seq_clusters=5, dist_type=None, temporal_index='year', unit_index='geoid')
predict_markov_labels(gdf, unit_index='geoid', temporal_index='year', cluster_col=None, w_type='rook',
                      w_options=None, base_year=None, new_colname=None, time_steps=1, increment=None, seed=None)
lincs_from_gdf(gdf, unit_index, temporal_index, cluster_col, periods='all')
```

- `w_type` 허용값: `rook`, `queen`, `voronoi`, `distanceband`, `knn`, `kernel`.
- 공식 예제: `examples/04_modeling_neighborhood_types.ipynb`, `05_modeling_neighborhood_dynamics.ipynb`, `06_simulating_neighborhood_dynamics.ipynb`, `07_visualizing_neighborhood_sequences.ipynb`.
- 분기 값(`20211` 등)을 시간 축으로 쓸 때 `increment`, `base_year`가 어떻게 해석되는지는 예제 06에서 확인한다. 문제가 있으면 분기를 1, 2, 3… 순번으로 바꿔 넣는다.

---

## 5. 시각화 산출물

| 번호 | 그림 | 만드는 방법 |
|---|---|---|
| F1 | 서울 상권 유형 지도, 분기별 애니메이션 | `plot_timeseries`, `animate_timeseries` |
| F2 | 유형별 특성 비교 | `plot_violins_by_cluster` 또는 막대 |
| F3 | 전이확률 행렬 | `plot_transition_matrix` |
| F4 | 과열형 전이 예상 상권 지도 (인터랙티브) | folium |
| F5 | 성수동과 같은 경로의 상권 목록과 경로 그림 | `indexplot_seq` |
| F6 | 과거 검증 결과표 | 표 |

(여유가 있으면) seoul_commerce의 Streamlit 대시보드를 그대로 띄워 상권별 상세 조회 화면으로 쓴다.

---

## 6. Claude Code 작업 지시

### 6.1 저장소 구조
```
seoul-gentrification-early-warning/
├── CLAUDE.md                # 6.3 내용
├── README.md                # 연구 질문, 사용한 외부 저장소와 인용, 재현 방법, 결과 그림
├── docs/
│   ├── experiment_design.md       # 이 문서
│   ├── api_notes.md               # 실제 확인한 함수 인자
│   └── changes_from_upstream.md   # 원 코드에서 바꾼 것
├── external/seoul_commerce/ # 원 저장소 복제본 (커밋 해시 기록, 수정 금지)
├── data/raw/  data/processed/
├── adapters/seoul_to_geosnap.py   # 직접 작성하는 유일한 로직
├── run/                     # geosnap 함수를 호출만 하는 스크립트 (단계별 1개)
├── reports/figures/
└── requirements.txt         # geosnap==0.17.0 고정
```

### 6.2 단계와 완료 기준

| 단계 | 과업 | 완료 기준 |
|---|---|---|
| 0 | 이 문서를 `docs/`에 넣고 `CLAUDE.md` 생성. geosnap 설치 후 공식 예제 05를 원자료 그대로 실행 | 예제 그림 재현, `docs/api_notes.md` 작성 |
| 1 | seoul_commerce를 `external/`에 가져와 테스트 실행. 수집기로 2021Q1~최신 분기 수집 시도 | 수집 성공 여부 보고. 막히면 사용자에게 CSV 업로드 요청 |
| 2 | 전처리 실행 후 `reports/data_audit.md` 작성 | 분기 범위, 상권 수, 결측, 전 기간 연속 관측 상권 수 |
| 3 | 어댑터 작성 | long-form GeoDataFrame 저장, 변수 정의표 |
| 4 | S4~S5 | 유형 수 결정 근거, 유형 특성표, 전이행렬 |
| 5 | S6~S8 | 경로 군집, 예측 유형, 핫스팟 |
| 6 | 과거 검증 | 예측 대 실제 표 |
| 7 | F1~F6 | `reports/figures/`, README에 삽입 |

단계마다 커밋하고, 무엇을 했고 설계서와 무엇이 달랐는지 요약한다. **한 번에 한 단계만 진행하고 사용자 확인을 받는다.**

### 6.3 CLAUDE.md에 넣을 규칙
1. 분석 알고리즘을 새로 구현하지 않는다. geosnap과 seoul_commerce의 함수를 호출한다. 필요한 기능이 없으면 구현하지 말고 먼저 보고한다.
2. 함수 인자와 동작은 추측하지 말고 설치된 버전의 소스나 공식 예제에서 확인한다.
3. `external/`의 코드는 수정하지 않는다. 불가피하면 사유와 diff를 `docs/changes_from_upstream.md`에 남긴다.
4. 원자료는 수정하지 않는다. 컬럼명은 파일에서 확인한다.
5. 외부 저장소의 이름, 버전(커밋 해시), 라이선스, 인용 문헌을 README에 적는다. 데이터는 "서울 열린데이터광장, 서울시 상권분석서비스" 출처를 표시한다.
6. API 키와 `.env`는 커밋하지 않는다.
7. 결과가 나쁘더라도 그대로 보고한다.
8. 사용자는 코드를 직접 짜지 않는 연구자다. 보고는 한국어로, 전문용어는 풀어서 쓴다.

### 6.4 첫 지시문 (Claude Code에 이 파일을 첨부하고 입력)
> 첨부한 `experiment_design.md`가 이 프로젝트의 실험설계서야. 6.2의 0단계만 수행해줘. 분석 로직은 새로 만들지 말고 설계서에 적힌 GitHub 저장소의 기능만 써. 끝나면 무엇을 했는지와 설계서의 가정과 달랐던 점을 알려주고, 다음 단계는 내가 확인한 뒤 진행해.

---

## 7. 위험 요인과 주제 전환 기준

| 위험 | 대응 |
|---|---|
| 실행 환경에서 서울시 API 접속 불가 | CSV 수동 다운로드 후 저장소에 업로드 |
| seoul_commerce가 Python 3.12 이상, pandas 3 등 최신 환경 요구 | `uv sync`로 저장소의 잠금 파일 그대로 설치. geosnap과 충돌하면 가상환경을 둘로 분리 |
| seoul_commerce에 LICENSE 파일이 없음 (README에는 MIT 명시) | README 문구를 근거로 인용하고, 필요하면 저자에게 issue로 확인 요청 |
| 분기 수가 짧아(약 21) 전이 관측이 적음 | 유형 수 4~5개로 제한, 필요하면 반기·연 단위 집계 |
| 코로나 회복기(2021~2022) 혼입 | 분기별 표준화 후 군집, 2023년 이후만으로 재실행해 비교 |
| seoul_commerce 범위가 외식업 10종 | 1차는 외식업으로 진행(상권 젠트리피케이션의 핵심 업종). 전 업종 확장은 설정 파일의 업종 코드만 추가 |

**대안 주제("구의회 회의록 지식그래프")로 전환하는 경우**
1. 2단계 후 전 기간 연속 관측 상권이 500개 미만이다.
2. 4단계에서 유형 간 특성 차이가 거의 없어 해석이 불가능하다.
3. 6단계에서 "유형 유지" 가정보다 나은 점이 전혀 없다. 단, 이 경우에도 유형 지도와 경로 분석(RQ1, RQ3)만으로 발표할 수 있다.

---

## 8. 수업 방법론 매핑

| 주차 | 수업 내용 | 본 실험 |
|---|---|---|
| 2 | 데이터 분석 기초, 차원 축소 | 표준화, 군집 수 결정 |
| 3 | 앙상블 | (선택) seoul_commerce의 EBM(부스팅 기반 설명가능 모델) 결과 비교 |
| 10~11 | 프롬프트 엔지니어링, 시스템 프롬프트, Tool Use | 이 설계서와 CLAUDE.md로 코드 생성기를 통제 |
| 13~14 | 에이전트, 하네스 (실행 루프, 권한, 샌드박스) | Claude Code가 외부 저장소를 가져와 실행·검증·커밋하는 과정 자체를 발표에 포함 |

---

## 9. 참고 자료

**저장소**
- https://github.com/oturns/geosnap (BSD-3-Clause)
- https://github.com/scksh/seoul_commerce (README상 MIT)
- https://github.com/chaeni1105/gentrification
- https://github.com/HojunJangSkku/Understanding-the-Commercial-gentrification-in-Seoul
- https://github.com/jreades/urb-studies-predicting-gentrification (MIT)
- https://github.com/urban-displacement/displacement-typologies (GPL-3.0)

**문헌**
- Knaap, E., & Rey, S. (2024). geosnap: The Geospatial Neighborhood Analysis Package. *Proc. 23rd Python in Science Conference*. https://doi.org/10.25080/FVWM4182
- Delmelle, E. C. (2016). Mapping the DNA of urban neighborhoods. *Annals of the AAG*, 106(1), 36–56.
- Reades, J., De Souza, J., & Hubbard, P. (2019). Understanding urban gentrification through machine learning. *Urban Studies*, 56(5), 922–942.
- Mueller, M., Hoque, S., & Pearsall, H. (2024). Machine learning to model gentrification. *Computers, Environment and Urban Systems*, 111, 102119.
- 김경선·김동섭 (2019). 서울시 상업젠트리피케이션 영향요인에 관한 연구. 한국콘텐츠학회논문지 19(2).

**데이터**
- 서울 열린데이터광장, 서울시 상권분석서비스: https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do
- 제공정보 안내: https://golmok.seoul.go.kr/images/seoul_info.pdf

> 확인 범위: 저장소의 스타 수·라이선스·파일 구성, geosnap 함수 인자는 2026-11-24에 직접 확인했다. 예제 노트북과 seoul_commerce 파이프라인을 실제로 끝까지 실행해 보지는 않았다. 문헌의 권호·쪽수는 발표 전에 원문에서 재확인한다.
