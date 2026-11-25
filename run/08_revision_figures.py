"""발표 수정용 그림 (2026-11-25 사용자 피드백 반영, 분석 결과는 그대로).
  move_matrix.png  : 2022년 유형 -> 최근 1년 유형 이동 건수표 (7장, 기존 Sankey 대체)
  ladder_labeled.png : 한 단계 위로 올라간 상권 지도, 대본에서 언급하는 지명 표시 (8장)
입력: reports/step4/period_types.csv, reports/step4/moved_up.csv, reports/step4/types.parquet
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import contextily as ctx
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from seoul_to_geosnap import load_boundaries

OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/figures/revision"
os.makedirs(OUT, exist_ok=True)
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
COLORS = {"쇠퇴형": "#3987e5", "안정형": "#7a7a75", "교체형": "#199e70",
          "청년상권형": "#c98500", "고매출밀집형": "#d55181"}
BG, INK, MUTED, GRID = "#1a1a19", "#ecebe7", "#a3a29d", "#34342f"
plt.rcParams.update({"font.family": ["NanumSquare", "NanumGothic"], "axes.unicode_minus": False,
                     "figure.facecolor": BG, "axes.facecolor": BG, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
stroke = [pe.withStroke(linewidth=4, foreground=BG)]

# ---------------------------------------------------------------- 이동 건수표
pt = pd.read_csv("reports/step4/period_types.csv", dtype={"trade_area_code": str})
ORDER = ["안정형", "교체형", "쇠퇴형", "청년상권형", "고매출밀집형"]  # 계단 순서로 보기 쉽게
ct = pd.crosstab(pt["2022년"], pt["최근 1년"]).reindex(index=ORDER, columns=ORDER).fillna(0).astype(int)
fig = plt.figure(figsize=(16, 9))
ax = fig.add_axes([0.2, 0.1, 0.5, 0.68])
step1 = {(r, "청년상권형") for r in ["안정형", "교체형", "쇠퇴형"]}
step2 = {("청년상권형", "고매출밀집형")}
for i, r in enumerate(ORDER):
    for j, c in enumerate(ORDER):
        v = ct.loc[r, c]
        if (r, c) in step1:
            fc, tc, fw = COLORS["청년상권형"], "#141413", "bold"
        elif (r, c) in step2:
            fc, tc, fw = COLORS["고매출밀집형"], "#141413", "bold"
        elif r == c:
            fc, tc, fw = "#3a3a37", INK, "normal"
        else:
            fc, tc, fw = "#242422", MUTED, "normal"
        ax.add_patch(plt.Rectangle((j + 0.04, -i - 0.96), 0.92, 0.92, color=fc, lw=0))
        ax.text(j + 0.5, -i - 0.5, f"{v}", ha="center", va="center", fontsize=22, color=tc, fontweight=fw)
ax.set_xlim(0, 5); ax.set_ylim(-5, 0); ax.set_axis_off()
for j, c in enumerate(ORDER):
    ax.text(j + 0.5, 0.15, c, ha="center", va="bottom", fontsize=15, color=COLORS[c], fontweight="bold")
for i, r in enumerate(ORDER):
    ax.text(-0.12, -i - 0.5, r, ha="right", va="center", fontsize=15, color=COLORS[r], fontweight="bold")
fig.text(0.45, 0.865, "최근 1년(2025년 2분기~2026년 1분기)의 유형 →", ha="center", fontsize=14, color=MUTED)
fig.text(0.035, 0.44, "2022년의\n유형\n↓", ha="left", va="center", fontsize=14, color=MUTED, linespacing=1.4)
fig.suptitle("상권 1,418곳, 2022년과 최근 1년 사이에 유형이 어떻게 바뀌었나", x=0.03, ha="left", fontsize=25,
             fontweight="bold", y=0.975)
# 오른쪽 요약
X = 0.74
n1 = sum(ct.loc[r, c] for r, c in step1); n2 = ct.loc["청년상권형", "고매출밀집형"]
stay = int(np.trace(ct.values))
fig.text(X, 0.70, f"{stay}곳", fontsize=40, fontweight="bold", color=INK)
fig.text(X, 0.655, "같은 유형에 머묾 (대각선 회색 칸)", fontsize=14, color=MUTED)
fig.text(X, 0.52, f"{n1}곳", fontsize=40, fontweight="bold", color=COLORS["청년상권형"])
fig.text(X, 0.475, "1단계: 안정·교체·쇠퇴형 → 청년상권형\n(주황 칸 세 개의 합)", fontsize=14, color=MUTED, va="top",
         linespacing=1.5)
fig.text(X, 0.32, f"{n2}곳", fontsize=40, fontweight="bold", color=COLORS["고매출밀집형"])
fig.text(X, 0.275, "2단계: 청년상권형 → 고매출밀집형\n(분홍 칸)", fontsize=14, color=MUTED, va="top", linespacing=1.5)
fig.text(0.03, 0.025, "칸 안 숫자 = 상권 수. 각 기간(4분기) 안에서 가장 많이 속한 유형 기준. "
         "geosnap cluster(k-means) 결과.", fontsize=11, color=MUTED)
fig.savefig(os.path.join(OUT, "move_matrix.png"), dpi=150, facecolor=BG); plt.close(fig)
print("move_matrix", n1, n2, stay)

# ---------------------------------------------------------------- 지명 표시 확산 지도
BASEMAP = ctx.providers.Esri.WorldGrayCanvas.__class__(dict(
    ctx.providers.Esri.WorldGrayCanvas, name="Esri.WorldDarkGrayBase",
    url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attribution="Tiles © Esri"))
t = pd.read_parquet("reports/step4/types.parquet")
b = load_boundaries().to_crs(3857)
units = b[b["trade_area_code"].isin(t["trade_area_code"].unique())].set_index("trade_area_code")
moved = pd.read_csv("reports/step4/moved_up.csv", index_col=0, dtype=str)
up1 = moved.index[moved["구분"] == "안정·교체·쇠퇴→청년상권형"]
up2 = moved.index[moved["구분"] == "청년상권형→고매출밀집형"]
seongsu = units.loc[t.loc[t["seongsu_area"], "trade_area_code"].unique()].dissolve()
xmin, ymin, xmax, ymax = units.total_bounds
EXT = (xmin - 2000, ymin - 2500, xmax + 2000, ymax + 2000)
img, ext = ctx.bounds2img(*EXT, source=BASEMAP, zoom=12)
fig = plt.figure(figsize=(16, 9), dpi=100)
ax = fig.add_axes([0.0, 0.0, 0.64, 1.0])
ax.imshow(img, extent=ext, interpolation="bilinear"); ax.set_xlim(EXT[0], EXT[2]); ax.set_ylim(EXT[1], EXT[3]); ax.set_axis_off()
units.plot(ax=ax, color="#4a4a47", linewidth=0)
for codes, col in [(up1, COLORS["청년상권형"]), (up2, COLORS["고매출밀집형"])]:
    g = units.loc[codes]
    g.plot(ax=ax, color=col, linewidth=0, zorder=3)
    c = g.geometry.centroid
    ax.scatter(c.x, c.y, s=90, facecolors="none", edgecolors=col, linewidths=1.6, zorder=4)
seongsu.boundary.plot(ax=ax, color="white", linewidth=1.3, linestyle=(0, (2, 2)), zorder=5)
# 대본에서 말하는 곳만 표시: (상권 코드 목록, 라벨, 색, x오프셋, y오프셋)
LABELS = [
    (["3110127", "3110132", "3110134", "3110129", "3110136", "3110106", "3110117"], "성수 주변 7곳", "청년상권형", 70, -55),
    (["3110540", "3130185"], "망원", "청년상권형", -40, 34),
    (["3110509"], "연희", "청년상권형", -30, 40),
    (["3110061"], "효창동", "청년상권형", -46, -10),
    (["3110291"], "한성대입구", "청년상권형", -10, 44),
    (["3110835"], "상도", "청년상권형", -40, -30),
    (["3110890"], "봉천", "청년상권형", 10, -44),
    (["3110902"], "사당", "청년상권형", 40, -34),
    (["3120044", "3110062"], "용리단길(삼각지)", "고매출밀집형", -30, -44),
    (["3110057"], "황학동(신당 인근)", "고매출밀집형", 40, 45),
    (["3110555"], "홍대", "고매출밀집형", -40, 10),
    (["3120178"], "신사역", "고매출밀집형", 36, -30),
    (["3130066"], "행당시장", "고매출밀집형", 46, 6),
]
for codes, name, ty, dx, dy in LABELS:
    c = units.loc[codes].geometry.union_all().centroid
    ax.annotate(name, xy=(c.x, c.y), xytext=(dx, dy), textcoords="offset points", fontsize=14, color=COLORS[ty],
                fontweight="bold", ha="left" if dx >= 0 else "right", va="center", zorder=7, path_effects=stroke,
                arrowprops=dict(arrowstyle="-", color=COLORS[ty], lw=1.1))
fig.text(0.665, 0.88, "젠트리피케이션은\n어디로 번졌나", fontsize=30, fontweight="bold", va="top")
fig.text(0.665, 0.70, "2022년 → 최근 1년(2025년 2분기~2026년 1분기)\n유형이 한 단계 위로 올라간 상권", fontsize=14,
         color=MUTED, va="top", linespacing=1.6)
items = [(COLORS["청년상권형"], f"1단계: 안정·교체형 → 청년상권형  {len(up1)}곳"),
         (COLORS["고매출밀집형"], f"2단계: 청년상권형 → 고매출밀집형  {len(up2)}곳"),
         ("#4a4a47", "그 밖의 상권")]
for i, (c, lab) in enumerate(items):
    y = 0.56 - i * 0.065
    fig.text(0.665, y, "●", color=c, fontsize=20, va="center")
    fig.text(0.69, y, lab, fontsize=15, va="center")
fig.text(0.665, 0.33, "동그라미: 작은 상권도 보이도록 표시한 위치\n흰 점선: 성수 일대\n이름: 발표에서 언급하는 곳", fontsize=12,
         color=MUTED, va="top", linespacing=1.7)
fig.text(0.99, 0.012, "자료: 서울 열린데이터광장, 서울시 상권분석서비스 · 배경지도 © Esri, © OpenStreetMap", fontsize=9,
         color=MUTED, ha="right")
fig.savefig(os.path.join(OUT, "ladder_labeled.png"), dpi=150, facecolor=BG); plt.close(fig)
print("ladder_labeled")
