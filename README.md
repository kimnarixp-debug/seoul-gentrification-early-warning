# seoul-gentrification-early-warning

"다음 성수동은 어디인가" — 서울시 상권 젠트리피케이션 조기경보 실험.
실험설계서: [docs/experiment_design.md](docs/experiment_design.md)

## 진행 상황
- [x] 0단계: 설계서 등록, `CLAUDE.md`, geosnap 설치·API 확인 ([docs/api_notes.md](docs/api_notes.md))
- [ ] 1단계 이후: 미진행

## 사용한 외부 저장소
| 저장소 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| [oturns/geosnap](https://github.com/oturns/geosnap) | v0.17.0 (`61f9537`) | BSD-3-Clause | 분석 엔진 |
| [scksh/seoul_commerce](https://github.com/scksh/seoul_commerce) | (1단계에서 기록) | README상 MIT | 서울 데이터 수집·전처리 |

인용: Knaap, E., & Rey, S. (2024). geosnap: The Geospatial Neighborhood Analysis Package. *Proc. SciPy 2024*. https://doi.org/10.25080/FVWM4182

데이터 출처: 서울 열린데이터광장, 서울시 상권분석서비스 (공공누리 제1유형)

## 재현
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run/00_api_smoke_test.py
```
