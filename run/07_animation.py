"""7단계: 분기별 결과 애니메이션 (발표용).

한 장면(분기)마다:
  - 왼쪽 지도: 상권 유형 색. 이번 분기에 한 단계 위(청년상권형·고매출밀집형)로 올라간 상권은 흰색으로 빛남
  - 오른쪽: 분기 이름, 유형 비중 누적 면적 그래프(현재 분기 표시), 이번 분기 이동 수(올라감/내려감),
           2022년 1분기 대비 청년상권형·고매출밀집형 상권 수 변화
마지막 두 장면(2026-11-25 추가, 슬라이드와 맞춤):
  - end_ladder: 2022년 -> 최근 1년 한 단계 위로 올라간 상권 + 발표에서 언급하는 지명 (슬라이드 '어디로 번졌나')
  - end_warn_on/off: 확산 경보 상위 7곳이 깜빡임 (슬라이드 '다음 성수는 어디인가', 5단계 수정 필터 기준)
출력: reports/figures/final/anim/ (JPEG 프레임, MP4 부드러운 전환, GIF)
입력: reports/step4/types.parquet (geosnap cluster 결과), reports/step4/moved_up.csv, reports/step5/warning_spread.csv
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import contextily as ctx
import geopandas as gpd
import imageio.v2 as imageio
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from seoul_to_geosnap import load_boundaries

OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/figures/final/anim"
os.makedirs(OUT, exist_ok=True)
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
COLORS = {"쇠퇴형": "#3987e5", "안정형": "#7a7a75", "교체형": "#199e70",
          "청년상권형": "#c98500", "고매출밀집형": "#d55181"}
HIGH = {"청년상권형", "고매출밀집형"}
BG, INK, MUTED, GRID = "#141413", "#ecebe7", "#9b9a95", "#3a3a37"
plt.rcParams.update({"font.family": ["NanumSquare", "NanumGothic"], "axes.unicode_minus": False,
                     "figure.facecolor": BG, "axes.facecolor": BG, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
BASEMAP = ctx.providers.Esri.WorldGrayCanvas.__class__(dict(
    ctx.providers.Esri.WorldGrayCanvas, name="Esri.WorldDarkGrayBase",
    url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attribution="Tiles © Esri"))
LANDMARKS = {"3110131": ("성수", 30, 26), "3120044": ("용리단길", -36, -40), "3120039": ("신당", 26, 30),
             "3120102": ("홍대", -40, 30), "3120189": ("강남역", 26, -36), "3120028": ("명동", -30, 34)}

t = pd.read_parquet("reports/step4/types.parquet")
b = load_boundaries().to_crs(3857)
g = gpd.GeoDataFrame(b.merge(t, on="trade_area_code"), crs=3857)
quarters = sorted(t["quarter_code"].unique())
lab = {q: f"{q[:4]}년 {q[4]}분기" for q in quarters}
wide = t.pivot(index="trade_area_code", columns="quarter_code", values="type_name")
share = t.groupby(["quarter_code", "type_name"]).size().unstack().reindex(columns=TYPES).fillna(0)
share = share.div(share.sum(axis=1), axis=0) * 100
high0 = {k: (wide[quarters[0]] == k).sum() for k in HIGH}

units = g.drop_duplicates("trade_area_code").set_index("trade_area_code")
xmin, ymin, xmax, ymax = b[b["trade_area_code"].isin(units.index)].total_bounds
EXT = (xmin - 2000, ymin - 2500, xmax + 2000, ymax + 2000)
BIMG, BEXT = ctx.bounds2img(*EXT, source=BASEMAP, zoom=12)
seongsu = units[units["seongsu_area"]].dissolve()
stroke = [pe.withStroke(linewidth=4, foreground=BG)]


def moves(i):
    if i == 0:
        return pd.Index([]), pd.Index([])
    prev, cur = wide[quarters[i - 1]], wide[quarters[i]]
    up = cur.index[cur.isin(HIGH) & ~prev.isin(HIGH) | ((cur == "고매출밀집형") & (prev == "청년상권형"))]
    down = cur.index[~cur.isin(HIGH) & prev.isin(HIGH) | ((cur == "청년상권형") & (prev == "고매출밀집형"))]
    return up, down


def frame(i):
    q = quarters[i]
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = fig.add_axes([0.0, 0.0, 0.6, 1.0])
    ax.imshow(BIMG, extent=BEXT, interpolation="bilinear", zorder=0)
    ax.set_xlim(EXT[0], EXT[2]); ax.set_ylim(EXT[1], EXT[3]); ax.set_axis_off()
    cur = g[g["quarter_code"] == q]
    cur.plot(ax=ax, color=cur["type_name"].map(COLORS), linewidth=0, alpha=0.93, zorder=2)
    up, down = moves(i)
    if len(up):
        u = units.loc[up]
        u.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=5, alpha=0.25, zorder=3)  # 빛 번짐
        u.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=1.6, zorder=4)
    seongsu.boundary.plot(ax=ax, color="white", linewidth=1.1, linestyle=(0, (2, 2)), zorder=4)
    for code, (name, dx, dy) in LANDMARKS.items():
        c = units.loc[code, "geometry"].centroid
        ax.annotate(name, xy=(c.x, c.y), xytext=(dx, dy), textcoords="offset points", fontsize=14, color=INK,
                    fontweight="bold", ha="left" if dx >= 0 else "right", va="center", zorder=6, path_effects=stroke,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.9))
    # 지도 아래 시간 막대
    tx = fig.add_axes([0.03, 0.035, 0.54, 0.03]); tx.set_axis_off(); tx.set_xlim(-0.5, len(quarters) - 0.5); tx.set_ylim(0, 1)
    for j, qq in enumerate(quarters):
        tx.add_patch(plt.Rectangle((j - 0.42, 0.25), 0.84, 0.5, color=INK if j <= i else GRID, lw=0))
        if qq[4] == "1":
            tx.text(j - 0.42, 1.25, qq[:4], fontsize=11, color=INK if j <= i else MUTED, va="bottom")
    # 오른쪽 패널
    X = 0.63
    fig.text(X, 0.925, "서울 상권, 17분기의 이동", fontsize=30, fontweight="bold")
    fig.text(X, 0.885, "외식업 1,418개 상권 · 5개 유형 (geosnap 군집)", fontsize=14, color=MUTED)
    fig.text(X, 0.79, lab[q], fontsize=52, fontweight="bold")
    # 누적 면적
    sx = fig.add_axes([X, 0.42, 0.33, 0.29])
    xs = np.arange(len(quarters))
    sx.stackplot(xs, *[share[k].values for k in TYPES], colors=[COLORS[k] for k in TYPES], linewidth=0, alpha=0.95)
    sx.axvspan(i + 0.5, len(quarters), color=BG, alpha=0.72, lw=0, zorder=3)
    sx.axvline(i, color="white", lw=2, zorder=4)
    bottom = 0
    for k in TYPES:
        v = share.loc[q, k]
        if v >= 4:
            sx.text(len(quarters) - 0.6, bottom + v / 2, f"{k} {v:.0f}%", fontsize=12, color=INK, ha="right",
                    va="center", fontweight="bold", zorder=5, path_effects=stroke)
        bottom += v
    sx.set_xlim(0, len(quarters) - 1); sx.set_ylim(0, 100); sx.set_yticks([]); sx.set_xticks([])
    for s in sx.spines.values():
        s.set_visible(False)
    fig.text(X, 0.725, "유형 비중 (%)", fontsize=13, color=MUTED)
    # 이번 분기 이동
    fig.text(X, 0.345, "이번 분기", fontsize=15, color=MUTED)
    fig.text(X, 0.27, f"▲ {len(up)}", fontsize=40, fontweight="bold", color="#ffffff")
    fig.text(X, 0.235, "청년상권형·고매출밀집형으로\n올라간 상권 (지도에서 흰 테두리)", fontsize=12, color=MUTED, va="top")
    fig.text(X + 0.17, 0.27, f"▼ {len(down)}", fontsize=40, fontweight="bold", color=MUTED)
    fig.text(X + 0.17, 0.235, "내려간 상권", fontsize=12, color=MUTED, va="top")
    # 2022년 1분기 대비
    y0 = 0.13
    fig.text(X, y0 + 0.025, "2022년 1분기 대비 상권 수", fontsize=13, color=MUTED)
    for k_i, k in enumerate(["청년상권형", "고매출밀집형"]):
        n = int((wide[q] == k).sum()); d = n - high0[k]
        fig.text(X + k_i * 0.17, y0 - 0.02, f"{k}", fontsize=14, color=COLORS[k], fontweight="bold")
        fig.text(X + k_i * 0.17, y0 - 0.065, f"{n}곳  {'+' if d >= 0 else ''}{d}", fontsize=22, fontweight="bold")
    fig.text(0.985, 0.012, "자료: 서울 열린데이터광장, 서울시 상권분석서비스 · 배경지도 © Esri, © OpenStreetMap · 점선: 성수 일대",
             fontsize=10, color=MUTED, ha="right")
    buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor=BG); plt.close(fig)
    return Image.open(buf).convert("RGB")



# ---------------------------------------------------------------- 마지막 두 장면
moved = pd.read_csv("reports/step4/moved_up.csv", index_col=0, dtype=str)
UP1 = moved.index[moved["구분"] == "안정·교체·쇠퇴→청년상권형"]
UP2 = moved.index[moved["구분"] == "청년상권형→고매출밀집형"]
# 지명 표시: run/08_revision_figures.py 와 같은 목록 (상권 코드, 이름, 색 기준 유형, x/y 오프셋)
LABELS = [
    (["3110127", "3110132", "3110134", "3110129", "3110136", "3110106", "3110117"], "성수 주변 7곳", "청년상권형", 70, -55),
    (["3110540", "3130185"], "망원", "청년상권형", -40, 34), (["3110509"], "연희", "청년상권형", -30, 40),
    (["3110061"], "효창동", "청년상권형", -46, -10), (["3110291"], "한성대입구", "청년상권형", -10, 44),
    (["3110835"], "상도", "청년상권형", -40, -30), (["3110890"], "봉천", "청년상권형", 10, -44),
    (["3110902"], "사당", "청년상권형", 40, -34), (["3120044", "3110062"], "용리단길(삼각지)", "고매출밀집형", -30, -44),
    (["3110057"], "황학동(신당 인근)", "고매출밀집형", 40, 45), (["3110555"], "홍대", "고매출밀집형", -40, 10),
    (["3120178"], "신사역", "고매출밀집형", 36, -30), (["3130066"], "행당시장", "고매출밀집형", 46, 6),
]
warn = pd.read_csv("reports/step5/warning_spread.csv", dtype={"trade_area_code": str}).sort_values("warn", ascending=False).head(7)
# 경보 상위 7곳 라벨 위치 (겹치지 않게 수동 지정)
WOFF = [(60, 40), (-60, 40), (-60, -40), (10, 75), (70, 0), (-60, 60), (-70, 0)]


def base_map(fig):
    ax = fig.add_axes([0.0, 0.0, 0.6, 1.0])
    ax.imshow(BIMG, extent=BEXT, interpolation="bilinear", zorder=0)
    ax.set_xlim(EXT[0], EXT[2]); ax.set_ylim(EXT[1], EXT[3]); ax.set_axis_off()
    return ax


def to_img(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor=BG); plt.close(fig)
    return Image.open(buf).convert("RGB")


def foot(fig, extra=""):
    fig.text(0.985, 0.012, "자료: 서울 열린데이터광장, 서울시 상권분석서비스 · 배경지도 © Esri, © OpenStreetMap" + extra,
             fontsize=10, color=MUTED, ha="right")


def end_ladder():
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = base_map(fig)
    units.plot(ax=ax, color="#4a4a47", linewidth=0, zorder=2)
    for codes, col in [(UP1, COLORS["청년상권형"]), (UP2, COLORS["고매출밀집형"])]:
        gg = units.loc[codes]
        gg.plot(ax=ax, color=col, linewidth=0, zorder=3)
        c = gg.geometry.centroid
        ax.scatter(c.x, c.y, s=110, facecolors="none", edgecolors=col, linewidths=1.8, zorder=4)
    seongsu.boundary.plot(ax=ax, color="white", linewidth=1.3, linestyle=(0, (2, 2)), zorder=5)
    for codes, name, ty, dx, dy in LABELS:
        c = units.loc[codes].geometry.union_all().centroid
        ax.annotate(name, xy=(c.x, c.y), xytext=(dx, dy), textcoords="offset points", fontsize=16, color=COLORS[ty],
                    fontweight="bold", ha="left" if dx >= 0 else "right", va="center", zorder=7, path_effects=stroke,
                    arrowprops=dict(arrowstyle="-", color=COLORS[ty], lw=1.2))
    X = 0.63
    fig.text(X, 0.925, "4년 동안, 어디로 번졌나", fontsize=30, fontweight="bold")
    fig.text(X, 0.885, "2022년 → 최근 1년(2025년 2분기~2026년 1분기) 유형 비교", fontsize=14, color=MUTED)
    fig.text(X, 0.72, f"{len(UP1)}곳", fontsize=60, fontweight="bold", color=COLORS["청년상권형"])
    fig.text(X, 0.675, "1단계: 안정·교체·쇠퇴형 → 청년상권형", fontsize=17, color=INK, va="top")
    fig.text(X, 0.50, f"{len(UP2)}곳", fontsize=60, fontweight="bold", color=COLORS["고매출밀집형"])
    fig.text(X, 0.455, "2단계: 청년상권형 → 고매출밀집형", fontsize=17, color=INK, va="top")
    fig.text(X, 0.33, "성수에서 시작된 변화가 망원·연희·효창동 등\n서울 곳곳의 골목으로 번졌고,\n용리단길·황학동·홍대는 한 단계 더 올라갔다.",
             fontsize=16, color=MUTED, va="top", linespacing=1.7)
    fig.text(X, 0.12, "동그라미: 작은 상권도 보이도록 표시 · 흰 점선: 성수 일대", fontsize=12, color=MUTED)
    foot(fig)
    return to_img(fig)


def end_warn(on):
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
    ax = base_map(fig)
    units.plot(ax=ax, color="#3a3a37", linewidth=0, zorder=2)
    units.loc[units.index.intersection(UP1.union(UP2))].plot(ax=ax, color=COLORS["청년상권형"], alpha=0.45, linewidth=0, zorder=2)
    seongsu.boundary.plot(ax=ax, color="white", linewidth=1.1, linestyle=(0, (2, 2)), zorder=4)
    W = units.loc[warn["trade_area_code"]]
    c = W.geometry.centroid
    if on:
        for s_, a_ in [(2600, 0.10), (1300, 0.22), (520, 0.45)]:
            ax.scatter(c.x, c.y, s=s_, color="#ffcf5a", alpha=a_, linewidths=0, zorder=5)
    ax.scatter(c.x, c.y, s=150, color="#ffcf5a" if on else "#8a6a20", edgecolors="white", linewidths=1.4, zorder=6)
    for (_, r), (dx, dy), x, y in zip(warn.iterrows(), WOFF, c.x, c.y):
        ax.annotate(f"{r['trade_area_name']} {r['warn'] * 100:.0f}%", xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                    fontsize=15, color="#ffcf5a" if on else INK, fontweight="bold", ha="left" if dx >= 0 else "right",
                    va="center", zorder=7, path_effects=stroke, arrowprops=dict(arrowstyle="-", color=INK, lw=0.9))
    X = 0.63
    fig.text(X, 0.925, "그렇다면, 다음 성수는 어디인가", fontsize=30, fontweight="bold")
    fig.text(X, 0.885, "확산 경보: 1년 뒤(2027년 1분기) 청년상권형이 될 확률 상위 7곳", fontsize=14, color=MUTED)
    for k, (_, r) in enumerate(warn.iterrows()):
        y = 0.80 - k * 0.075
        fig.text(X, y, f"{k + 1}", fontsize=24, fontweight="bold", color="#ffcf5a")
        fig.text(X + 0.03, y, f"{r['trade_area_name']}", fontsize=21, fontweight="bold")
        fig.text(X + 0.03, y - 0.03, f"{r['district']} · 지금 {r['최근 1년']}", fontsize=12, color=MUTED)
        fig.text(X + 0.31, y, f"{r['warn'] * 100:.0f}%", fontsize=24, fontweight="bold", ha="right", color="#ffcf5a")
    fig.text(X, 0.215, "공간 마르코프 체인 모의실험 300번 (geosnap predict_markov_labels)\n"
             "대상: 지금 안정·교체형이고 외식업 점포 10곳 이상인 727곳\n확률 값보다 순위로 읽는다 (과거 검증: 상위 20곳 중 3곳 적중)",
             fontsize=13, color=MUTED, va="top", linespacing=1.7)
    fig.text(X, 0.07, "● 옅은 주황: 지난 4년 한 단계 올라간 상권", fontsize=12, color=COLORS["청년상권형"])
    foot(fig)
    return to_img(fig)

frames = [frame(i) for i in range(len(quarters))]
for q, f in zip(quarters, frames):
    f.save(os.path.join(OUT, f"q_{q}.jpg"), quality=84, optimize=True)
E_LADDER, E_ON, E_OFF = end_ladder(), end_warn(True), end_warn(False)
for n, f in [("end_ladder", E_LADDER), ("end_warn_on", E_ON), ("end_warn_off", E_OFF)]:
    f.save(os.path.join(OUT, f"{n}.jpg"), quality=86, optimize=True)

# MP4: 분기마다 1.6초 정지 + 0.5초 교차 전환 (12fps)
FPS, HOLD, FADE = 12, 19, 6
with imageio.get_writer(os.path.join(OUT, "seoul_types_17q.mp4"), fps=FPS, codec="libx264", quality=8,
                        macro_block_size=1) as w:
    for i, f in enumerate(frames):
        a = np.asarray(f)
        for _ in range(HOLD + (12 if i == len(frames) - 1 else 0)):
            w.append_data(a)
        if i + 1 < len(frames):
            nb = np.asarray(frames[i + 1]).astype(np.float32)
            for k in range(1, FADE + 1):
                w.append_data((a * (1 - k / (FADE + 1)) + nb * (k / (FADE + 1))).astype(np.uint8))
    # 마지막 두 장면: 교차 전환 후 정지, 경보는 0.5초 간격으로 깜빡임
    seq = [frames[-1], E_LADDER, E_OFF]
    for x, y in zip(seq[:-1], seq[1:]):
        xa, ya = np.asarray(x).astype(np.float32), np.asarray(y).astype(np.float32)
        for k in range(1, 2 * FADE + 1):
            w.append_data((xa * (1 - k / (2 * FADE + 1)) + ya * (k / (2 * FADE + 1))).astype(np.uint8))
        if y is E_LADDER:
            for _ in range(FPS * 5):
                w.append_data(np.asarray(E_LADDER))
    for r in range(10):
        for _ in range(FPS // 2):
            w.append_data(np.asarray(E_ON if r % 2 == 0 else E_OFF))
    for _ in range(FPS * 2):
        w.append_data(np.asarray(E_ON))
# GIF (가벼운 버전, 960px)
gframes = frames + [E_LADDER, E_ON, E_OFF, E_ON, E_OFF, E_ON]
small = [f.resize((960, 540), Image.LANCZOS).quantize(colors=200, method=Image.Quantize.MEDIANCUT) for f in gframes]
small[0].save(os.path.join(OUT, "seoul_types_17q.gif"), save_all=True, append_images=small[1:],
              duration=[1300] * (len(frames) - 1) + [2000, 4000, 500, 500, 500, 500, 3000], loop=0, optimize=True)
pd.DataFrame({"quarter": quarters, "up": [len(moves(i)[0]) for i in range(len(quarters))],
              "down": [len(moves(i)[1]) for i in range(len(quarters))]}).to_csv(os.path.join(OUT, "moves.csv"), index=False)
print("saved", len(frames))
