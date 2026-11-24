#!/usr/bin/env bash
# 1단계: 서울 열린데이터광장 원자료 내려받기 (2026-11-24 실행)
# 필요 네트워크: data.seoul.go.kr, datafile.seoul.go.kr
# 시트 다운로드는 Playwright(Chromium)로 화면의 "내려받기(CSV)" 버튼 기능을 호출한다.
set -euo pipefail
OUT=${1:-data/raw/seoul_opendata}
TMP=$(mktemp -d)
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"

# 연도별 파일: 데이터셋 페이지의 파일 목록(downloadFile(seq))과 같은 요청
file_dl() {  # infId seq 저장파일
  curl -sS -m 900 -X POST "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false" \
    --data-urlencode "infId=$1" --data-urlencode "seqNo=" --data-urlencode "seq=$2" --data-urlencode "infSeq=3" -o "$3"
}
file_dl OA-15560 5 "$OUT/OA-15560_trade_area_shp.zip"
for y in 1 2 3 4 5; do
  file_dl OA-15577 $((15 + y)) "$OUT/OA-15577_stores_202$y.zip"
  file_dl OA-15572 $((46 + y)) "$OUT/OA-15572_sales_202$y.zip"
done

# 시트: 최근 자료(점포·매출은 2025~최신, 인구 3종은 전체 기간)
for x in OA-15577:OA-15577_stores_sheet OA-15572:OA-15572_sales_sheet \
         OA-15568:OA-15568_floating_population_sheet OA-15584:OA-15584_resident_population_sheet \
         OA-15569:OA-15569_working_population_sheet; do
  node "$HERE/sheet_download.js" "${x%%:*}" "$TMP/${x##*:}.csv"
  gzip -9 -n -c "$TMP/${x##*:}.csv" > "$OUT/${x##*:}.csv.gz"
done
rm -rf "$TMP"
