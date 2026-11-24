# geosnap API 확인 기록 (v0.17.0)

- 확인일: 2026-11-24
- 설치: `pip install geosnap==0.17.0` (PyPI), Python 3.13
- 원 저장소 태그 `v0.17.0` = 커밋 `61f95373aa206b6795aa67274381154d720b785f`
- 함께 설치된 주요 패키지: giddy 2.3.9, libpysal 4.15.1, tobler 0.14.1, pandas 3.1.1, geopandas 1.2.0, scikit-learn 1.9.1
- 확인 방법: 설치된 소스의 `inspect.signature`와 함수 본문을 읽음 + `run/00_api_smoke_test.py`로 실제 호출

## 1. 함수 인자 (설치된 소스에서 직접 확인)

설계서 4.1과 다른 부분은 **굵게** 표시.

```python
# geosnap.analyze
find_k(gdf, method=None, columns=None, temporal_index='year', unit_index='geoid', scaler='std',
       pooling='fixed', random_state=None, cluster_kwargs=None, min_k=2, max_k=10, return_table=False)
cluster(gdf, n_clusters=6, method=None, best_model=False, columns=None, verbose=False,
        temporal_index='year', unit_index='geoid', scaler='std', pooling='fixed',
        random_state=None, cluster_kwargs=None, model_colname=None, return_model=False)
transition(gdf, cluster_col, temporal_index='year', unit_index='geoid', w_type='rook',
           w_options=None, permutations=0)
sequence(gdf, cluster_col, seq_clusters=5, subs_mat=None, dist_type=None, indel=None,
         temporal_index='year', unit_index='geoid')
predict_markov_labels(gdf, unit_index='geoid', temporal_index='year', cluster_col=None, w_type='rook',
                      w_options=None, base_year=None, new_colname=None, time_steps=1, increment=None,
                      seed=None, verbose=True)
lincs_from_gdf(gdf, unit_index, temporal_index, cluster_col, periods='all')
draw_sequence_from_gdf(gdf, w, label_column, smk, time_column, start_time=None, time_steps=1,
                       increment=None, seed=None, aspatial=False)

# geosnap.visualize
plot_timeseries(gdf, column, title='', temporal_index='year', time_subset=None, scheme='quantiles', k=5,
                pooled=True, cmap=None, legend=True, categorical=False, save_fig=None, dpi=200, ...,
                ctxmap='default', alpha=0.7, web_mercator=True)
animate_timeseries(gdf, column=None, filename=None, title='', temporal_index='year', time_periods=None,
                   ..., categorical=False, ..., ctxmap='default', ...)
plot_transition_matrix(gdf=None, cluster_col=None, w_type='rook', w_options=None, temporal_index='year',
                       unit_index='geoid', permutations=0, ..., savefig=None, dpi=300, transition_model=None)
plot_violins_by_cluster(df, columns, cluster_col, violin_kwargs=None, figsize=(12, 8), nrows=None,
                        ncols=None, titles=None, savefig=None, dpi=200)
indexplot_seq(df_traj, clustering, years=['1970','1980','1990','2000','2010'], k=None, ncols=3,
              palette='Set1', save_fig=None, dpi=500)
```

- `find_k`: **`return_table=True`이면 결과가 (최적 k, 지표표) 튜플**로 나온다.
- `cluster`: 결과 군집 컬럼 이름은 `method` 이름(예: `kmeans`)이 기본. `model_colname`으로 바꿀 수 있다.
- `transition`: **`w_type` 기본값이 `'rook'`(면 인접)이라 점 데이터에서는 반드시 바꿔야 한다.** `w_type=None`이면 공간 조건 없는 일반 전이행렬(giddy `Markov`), 값을 주면 주변 유형 조건부 전이행렬(giddy `Spatial_Markov`).
- `sequence`: 결과는 `(gdf, df_wide, 거리행렬)` 3개. `df_wide`의 열은 시간 값 그대로이고 마지막 열이 `{dist_type}_{seq_clusters}` (예: `hamming_5`).
- `indexplot_seq`: **`years` 기본값이 1970~2010 문자열 목록**이다. 서울 분기 자료에서는 `years=`에 `df_wide`의 실제 시간 열 이름을 넘겨야 한다.
- `w_type` 허용값: `rook`, `queen`, `voronoi`, `distanceband`, `knn`, `kernel` (설계서와 동일). `knn`은 `w_options={"k": 5}`처럼 이웃 수를 준다.

## 2. 시간 축(분기) 처리 — 설계서 4.1의 미확정 사항 해결

`predict_markov_labels` 본문(analyze/dynamics.py)에서 다음 시점을 `current_time = base_year + increment`로 **단순 덧셈**한다.
`draw_sequence_from_gdf`도 `start_time + increment * step`이다.

- 분기 코드 `20214`에 1을 더하면 `20215`(존재하지 않는 분기)가 된다.
- **결론: 분기를 1, 2, 3… 순번으로 바꿔 넣는다.** (설계서 4.1에서 "문제가 있으면"이라고 적은 대안을 기본으로 채택)
- `time_steps>1`이면 `increment`가 필수다 (없으면 오류). 순번을 쓰면 `increment=1`.
- `base_year`는 실제 자료에 있는 시점이어야 한다.

## 3. 실제 호출 점검 (`run/00_api_smoke_test.py`)

가짜 점 자료(상권 60개 × 8분기, 좌표계 EPSG:5181)로 아래 설정이 오류 없이 도는 것을 확인했다. 수치는 의미 없음.

| 함수 | 설정 | 결과 |
|---|---|---|
| find_k | kmeans, k=2~5, `temporal_index='quarter'`, `unit_index='trade_area_code'` | 정상 |
| cluster | kmeans, k=4 | 정상, `kmeans` 컬럼 추가 |
| transition | `w_type=None` | 정상, 4×4 전이행렬 |
| transition | `w_type='knn'`, k=5 (점 좌표) | 정상, 주변 유형별 전이행렬 4개 |
| sequence | hamming, 3개 경로 군집 | 정상 |
| predict_markov_labels | knn, `base_year=8`, `time_steps=4`, `increment=1` | 정상, 시점 8~12 생성 |
| lincs_from_gdf | 기본 | 정상 |

## 4. 공식 예제 상태

| 예제 | v0.17.0에서 실행 | 비고 |
|---|---|---|
| 04, 05, 06 | **그대로는 실행 불가** | 제거된 `Community` 클래스(`Community.from_ltdb` 등)를 사용. 같은 기능은 위의 함수형 API로 호출해야 함 |
| 05의 원자료 | **이 환경에서 불러올 수 없음** | LTDB(브라운대 미국 센서스 자료)는 사용자가 직접 내려받아 `io.store_ltdb()`로 저장해야 함. geosnap 자체 CI도 비공개 주소에서 받음 |
| 07 | **실행 성공** | 저장소 동봉 자료 `examples/data/LA_sequences.csv` 사용. `reports/figures/step0/ex07_*.png` |

## 5. 환경 관련 확인 사항

- geosnap을 pip으로 설치하면 `DataStore`(미국 자료 로딩)에 필요한 `ibis-framework[duckdb]`가 함께 설치되지 않는다 → 별도 설치.
- `DataStore`는 시작할 때 DuckDB `spatial` 확장을 `extensions.duckdb.org`에서 내려받는데, 이 실행 환경의 네트워크 정책이 그 주소를 막는다. 그래서 미국 예제 데이터(S3 `spatial-ucr`)를 불러오는 경로 전체가 막힌다. (S3 자체는 접속됨)
- **서울 프로젝트 본 분석에는 `DataStore`가 필요 없다.** 분석 함수(cluster, transition 등)는 우리가 만든 GeoDataFrame을 직접 받으므로 이 문제의 영향을 받지 않는다.
- 같은 네트워크 점검에서 `data.seoul.go.kr`(서울 열린데이터광장)도 차단, `openapi.seoul.go.kr`은 주소 조회 실패 → 1단계 수집기 실행이 막힐 가능성이 높다.
- 2026-11-24 확인: openapi.seoul.go.kr:8088은 네트워크 허용 후에도 이 환경에서 주소 조회 실패. 열린데이터광장 파일 다운로드(datafile.seoul.go.kr)는 동작.
