# 원 코드에서 바꾼 것

| 날짜 | 대상 | 변경 내용 | 사유 |
|---|---|---|---|
| 2026-11-24 | - | 없음 | 0~1단계에서 외부 코드를 수정하지 않았다. seoul_commerce는 커밋 `b44d8f8` 그대로 하위 모듈로 고정. |

## 참고: 원 코드를 바꾸지 않고 호출 방식만 맞춘 것
- geosnap 공식 예제 05는 v0.17.0에서 제거된 `Community` 클래스를 쓴다. 같은 기능을 v0.17.0의 함수형 API(`geosnap.analyze.cluster`, `transition`, `sequence`)로 호출해야 한다. 함수 자체는 바꾸지 않는다.
- `run/00_reproduce_example07.py`: 예제 07 노트북의 호출을 그대로 옮기고 그림 저장 인자(`save_fig`, `dpi`)만 추가했다.

- seoul_commerce 수집기(`collector.py`) 대신 `adapters/opendata_to_contract.py`가 같은 출력 형식(필수 컬럼 + 관리 컬럼 4개, utf-8-sig)을 만든다. 수집기가 접속하는 Open API에 이 환경에서 접속할 수 없어서다. 관리 컬럼 규칙은 `collector.py`의 것을 그대로 따랐다.
