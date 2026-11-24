"""5단계-4: 그림.
  F4a warning_spread.png   : 확산 경보 (최근 1년 안정·교체·쇠퇴형 -> 2027년 1분기 청년상권형일 확률)
  F4b warning_overheat.png : 과열 경보 (최근 1년 청년상권형 -> 2027년 1분기 고매출밀집형일 확률)
  F4c warning_interactive.html : 두 경보를 켜고 끄는 인터랙티브 지도 (folium)
  F5a seongsu_paths.png    : 성수 기준 7곳 + 같은 경로 상위 15곳의 분기별 유형 띠
  F5b path_clusters_geosnap.png : (05a에서 geosnap indexplot_seq로 생성)
  F6  linc_map.png         : 변화 핫스팟 (기간 LINC)
"""
import io
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
from matplotlib.colors import LinearSegmentedColormap
from seoul_to_geosnap import load_boundaries

IN = sys.argv[1] if len(sys.argv) > 1 else "reports/step5"
OUT = sys.argv[2] if len(sys.argv) > 2 else "reports/figures/step5"
os.makedirs(OUT, exist_ok=True)
TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
COLORS = {"쇠퇴형": "#3987e5", "안정형": "#7a7a75", "교체형": "#199e70",
          "청년상권형": "#c98500", "고매출밀집형": "#d55181"}
BG, INK, MUTED, GRID = "#1a1a19", "#ecebe7", "#9b9a95", "#3a3a37"
plt.rcParams.update({"font.family": ["NanumSquare", "NanumGothic"], "axes.unicode_minus": False,
                     "figure.facecolor": BG, "axes.facecolor": BG, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
BASEMAP = ctx.providers.Esri.WorldGrayCanvas.__class__(dict(
    ctx.providers.Esri.WorldGrayCanvas, name="Esri.WorldDarkGrayBase",
    url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    attribution="Tiles © Esri"))

b = load_boundaries().to_crs(3857)
t = pd.read_parquet("reports/step4/types.parquet")
period = pd.read_csv("reports/step4/period_types.csv", dtype={"trade_area_code": str}).set_index("trade_area_code")
prob = pd.read_csv(os.path.join(IN, "predict_probs_base17.csv"), dtype={"trade_area_code": str}).set_index("trade_area_code")
units = gpd.GeoDataFrame(b.merge(period.reset_index(), on="trade_area_code"), crs=3857).set_index("trade_area_code")
units = units.join(prob)
xmin, ymin, xmax, ymax = units.total_bounds
EXT = (xmin - 2500, ymin - 2500, xmax + 2500, ymax + 2500)
BIMG, BEXT = ctx.bounds2img(*EXT, source=BASEMAP, zoom=12)
seongsu = units[units.index.isin(t.loc[t["seongsu_area"], "trade_area_code"].unique())].dissolve()


def base(ax):
    ax.imshow(BIMG, extent=BEXT, interpolation="bilinear", zorder=0)
    ax.set_xlim(EXT[0], EXT[2]); ax.set_ylim(EXT[1], EXT[3]); ax.set_axis_off()


def foot(fig, text):
    fig.text(0.01, 0.012, text, fontsize=10, color=MUTED, ha="left")
    fig.text(0.99, 0.012, "자료: 서울 열린데이터광장, 서울시 상권분석서비스 · 배경지도 © Esri, © OpenStreetMap",
             fontsize=9, color=MUTED, ha="right")


# ---------------------------------------------------------------- 경보 표
# 확산 경보 대상: 최근 1년도, 기준 분기(2026년 1분기)도 아직 안정·교체·쇠퇴형인 상권.
# 기준 분기에 이미 청년상권형으로 바뀐 상권은 마르코프 예측이 '현재 유형'만 보므로 확률이 높게 나온다 -> 별도 표
low = ["안정형", "교체형", "쇠퇴형"]
already = units[units["최근 1년"].isin(low) & (units["base_type"] == "청년상권형")].copy()
already["warn"] = already["p_청년상권형"]
already.drop(columns="geometry").sort_values("warn", ascending=False).to_csv(
    os.path.join(IN, "warning_spread_already_flipped.csv"), encoding="utf-8-sig")
spread = units[units["최근 1년"].isin(low) & units["base_type"].isin(low)].copy()
spread["warn"] = spread["p_청년상권형"]
over_all = units[units["최근 1년"] == "청년상권형"].copy()
over_all["warn"] = over_all["p_고매출밀집형"]
over_all[over_all["base_type"] == "고매출밀집형"].drop(columns="geometry").to_csv(
    os.path.join(IN, "warning_overheat_already_flipped.csv"), encoding="utf-8-sig")
over = over_all[over_all["base_type"] != "고매출밀집형"].copy()
for name, d, col in [("spread", spread, "p_청년상권형"), ("overheat", over, "p_고매출밀집형")]:
    d.drop(columns="geometry").sort_values("warn", ascending=False).to_csv(
        os.path.join(IN, f"warning_{name}.csv"), encoding="utf-8-sig")


def warning_map(d, hue, title, sub, fname, label_from, top_n=12):
    fig = plt.figure(figsize=(16, 9), dpi=100)
    ax = fig.add_axes([0.0, 0.0, 0.62, 1.0]); base(ax)
    units.plot(ax=ax, color="#3d3d3a", linewidth=0, zorder=1)
    cmap = LinearSegmentedColormap.from_list("w", ["#3d3d3a", hue])
    vmax = max(0.3, np.ceil(d["warn"].quantile(0.99) * 10) / 10)
    vmin = np.floor(d["warn"].quantile(0.05) * 20) / 20  # 대부분 상권이 비슷한 기본 확률을 가져 하위 5%를 바닥색으로
    d.sort_values("warn").plot(ax=ax, column="warn", cmap=cmap, vmin=vmin, vmax=vmax, linewidth=0, zorder=2)
    top = d.sort_values("warn", ascending=False).head(top_n)
    top.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=1.1, zorder=3)
    for rank, (code, r) in enumerate(top.iterrows(), 1):
        c = r.geometry.centroid
        ax.text(c.x, c.y, str(rank), fontsize=11, fontweight="bold", color=INK, ha="center", va="center", zorder=5,
                path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    seongsu.boundary.plot(ax=ax, color="white", linewidth=1.2, linestyle=(0, (2, 2)), zorder=4)
    fig.text(0.64, 0.92, title, fontsize=27, fontweight="bold", color=INK)
    fig.text(0.64, 0.875, sub, fontsize=13, color=MUTED)
    y0 = 0.80
    for rank, (code, r) in enumerate(top.iterrows(), 1):
        y = y0 - rank * 0.047
        fig.text(0.64, y, f"{rank:>2}", fontsize=14, color=MUTED, ha="left", va="center", fontweight="bold")
        fig.text(0.67, y, f"{r['trade_area_name']}", fontsize=14, color=INK, va="center", fontweight="bold")
        fig.text(0.67, y - 0.019, f"{r['district']} · 최근 1년 {r[label_from]}", fontsize=10, color=MUTED, va="center")
        bx = fig.add_axes([0.85, y - 0.012, 0.09, 0.024]); bx.set_axis_off()
        bx.barh([0], [r["warn"]], color=hue, height=1); bx.set_xlim(0, vmax)
        fig.text(0.945, y, f"{r['warn'] * 100:.0f}%", fontsize=13, color=INK, va="center", fontweight="bold")
    cax = fig.add_axes([0.03, 0.08, 0.18, 0.018])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.outline.set_visible(False); cb.ax.tick_params(colors=MUTED, labelsize=10)
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    fig.text(0.03, 0.105, "2027년 1분기에 해당 유형일 확률", fontsize=11, color=MUTED)
    foot(fig, "geosnap predict_markov_labels(knn=6) 300회 시뮬레이션. 점선: 성수 일대. 번호: 확률 상위 상권.")
    fig.savefig(os.path.join(OUT, fname), dpi=150, facecolor=BG); plt.close(fig)


warning_map(spread, COLORS["청년상권형"], "다음 성수는 어디인가: 확산 경보",
            f"아직 안정·교체·쇠퇴형인 {len(spread)}개 상권이 1년 뒤 청년상권형이 될 확률", "warning_spread.png", "최근 1년")
warning_map(over, COLORS["고매출밀집형"], "과열 경보",
            f"아직 고매출밀집형이 아닌 청년상권형 {len(over)}곳이 1년 뒤 고매출밀집형이 될 확률", "warning_overheat.png", "최근 1년")
print("F4 done")

# ---------------------------------------------------------------- 인터랙티브 경보 지도
import folium

g4 = units.to_crs(4326).copy()
g4["geometry"] = g4.geometry.simplify(0.00015)
m = folium.Map(location=[37.555, 126.99], zoom_start=12, tiles=None, control_scale=True)
folium.TileLayer(tiles=BASEMAP["url"], attr="Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap", name="배경지도").add_to(m)


def layer(d, hue, name, show):
    d = d.to_crs(4326).copy(); d["geometry"] = d.geometry.simplify(0.00015)
    d = d.reset_index()
    d["확률"] = (d["warn"] * 100).round(1).astype(str) + "%"
    vmax = max(0.3, d["warn"].quantile(0.99))
    cmap = LinearSegmentedColormap.from_list("w", ["#3d3d3a", hue])
    d["fill"] = d["warn"].clip(0, vmax).div(vmax).map(lambda v: matplotlib.colors.to_hex(cmap(v)))
    folium.GeoJson(d[["geometry", "trade_area_name", "district", "2022년", "2024년", "최근 1년", "확률", "fill"]].to_json(),
                   name=name, show=show,
                   style_function=lambda f: {"fillColor": f["properties"]["fill"], "fillOpacity": 0.9, "weight": 0},
                   highlight_function=lambda f: {"weight": 2, "color": "#ffffff"},
                   tooltip=folium.GeoJsonTooltip(["trade_area_name", "district", "2022년", "2024년", "최근 1년", "확률"],
                                                 aliases=["상권", "자치구", "2022년", "2024년", "최근 1년", "1년 뒤 확률"])
                   ).add_to(m)


layer(spread, COLORS["청년상권형"], "확산 경보 (→ 청년상권형)", True)
layer(over, COLORS["고매출밀집형"], "과열 경보 (→ 고매출밀집형)", False)
folium.GeoJson(seongsu.to_crs(4326)[["geometry"]].to_json(), name="성수 일대",
               style_function=lambda f: {"fillOpacity": 0, "color": "#ffffff", "weight": 2, "dashArray": "4 4"}).add_to(m)
m.get_root().html.add_child(folium.Element(
    f'<div style="position:fixed;top:14px;left:60px;z-index:9999;background:rgba(26,26,25,.9);color:{INK};padding:12px 16px;'
    f'border-radius:8px;font:14px NanumSquare,"Malgun Gothic","Apple SD Gothic Neo",sans-serif;line-height:1.6;max-width:360px">'
    f'<div style="font-size:19px;font-weight:700">서울 상권 조기경보</div>'
    f'<div style="color:{MUTED};font-size:12px">오른쪽 위 메뉴에서 확산·과열 경보를 바꿔 보세요. 색이 진할수록 1년 뒤(2027년 1분기) '
    f'그 유형이 될 확률이 높습니다. 상권에 마우스를 올리면 유형 이력과 확률이 나옵니다.</div>'
    f'<div style="margin-top:6px"><span style="color:{COLORS["청년상권형"]}">■</span> 확산: 안정·교체·쇠퇴형 → 청년상권형<br>'
    f'<span style="color:{COLORS["고매출밀집형"]}">■</span> 과열: 청년상권형 → 고매출밀집형</div>'
    f'<div style="color:{MUTED};font-size:11px;margin-top:6px">geosnap predict_markov_labels 300회 · 자료: 서울시 상권분석서비스</div></div>'))
folium.LayerControl(collapsed=False).add_to(m)
m.save(os.path.join(OUT, "warning_interactive.html"))
print("F4c done")

# ---------------------------------------------------------------- 성수와 같은 경로 (유형 띠)
paths = pd.read_csv(os.path.join(IN, "path_labels.csv"), dtype={"trade_area_code": str}).set_index("trade_area_code")
like = pd.read_csv(os.path.join(IN, "seongsu_like_paths.csv"), dtype={"trade_area_code": str}).set_index("trade_area_code")
moved = pd.read_csv("reports/step4/moved_up.csv", index_col=0, dtype=str)
REF = moved[(moved["구분"] == "안정·교체·쇠퇴→청년상권형") & (moved["district"] == "성동구")
            & moved["trade_area_name"].str.contains("성수|성원|경수|금북|성동구보건소")].index.tolist()
rows = [("성수 주변 (기준)", c) for c in REF] + [("같은 경로", c) for c in like.head(15).index]
quarters = sorted(t["quarter_code"].unique())
fig, ax = plt.subplots(figsize=(16, 10))
for i, (grp, code) in enumerate(rows):
    seq = paths.loc[code, "seq"]
    seq = str(seq).zfill(len(quarters))
    for j, ch in enumerate(seq):
        ax.add_patch(plt.Rectangle((j + 0.04, -i - 0.42), 0.92, 0.84, color=COLORS[TYPES[int(ch)]], lw=0))
    nm = paths.loc[code, "trade_area_name"]
    ax.text(-0.3, -i, f"{nm}", ha="right", va="center", fontsize=12, color=INK, fontweight="bold")
    ax.text(len(quarters) + 0.3, -i, paths.loc[code, "district"], ha="left", va="center", fontsize=10, color=MUTED)
sep = len(REF) - 0.5
ax.axhline(-sep, color=MUTED, lw=1, ls=(0, (3, 3)))
ax.text(len(quarters) + 2.2, -(len(REF) - 1) / 2, "기준:\n성수 주변 7곳", va="center", fontsize=12, color=INK)
ax.text(len(quarters) + 2.2, -(len(REF) + 7), "출발점이 같고\n경로가 가장 비슷한\n15곳", va="center", fontsize=12, color=INK)
ax.set_xlim(-0.2, len(quarters) + 4.6); ax.set_ylim(-len(rows) + 0.4, 1.2)
ax.set_yticks([])
ax.set_xticks([j + 0.5 for j in range(0, len(quarters), 4)], [f"{q[:4]}\nQ{q[4]}" for q in quarters[::4]], fontsize=11)
ax.tick_params(length=0); ax.xaxis.tick_top()
for s in ax.spines.values():
    s.set_visible(False)
for k_i, k in enumerate(TYPES):
    fig.text(0.24 + k_i * 0.135, 0.045, "■", color=COLORS[k], fontsize=16, va="center")
    fig.text(0.255 + k_i * 0.135, 0.045, k, color=INK, fontsize=13, va="center")
fig.suptitle("성수와 같은 길을 걸은 상권", x=0.02, ha="left", fontsize=26, fontweight="bold", y=0.985)
fig.text(0.02, 0.925, "한 칸 = 한 분기의 상권 유형. 위 7곳은 2022년 안정·교체형에서 청년상권형으로 바뀐 성수 주변 상권, "
         "아래 15곳은 같은 출발점(2022년 안정·교체형)에서 가장 비슷한 경로를 밟은 상권", fontsize=11, color=MUTED)
fig.text(0.02, 0.01, "geosnap sequence(dist_type='hamming') 경로 거리 기준 순위.", fontsize=10, color=MUTED)
fig.subplots_adjust(left=0.2, right=0.98, top=0.86, bottom=0.08)
fig.savefig(os.path.join(OUT, "seongsu_paths.png"), dpi=150, facecolor=BG); plt.close(fig)
print("F5 done")

# ---------------------------------------------------------------- LINC 지도
lincs = pd.read_csv(os.path.join(IN, "lincs.csv"), dtype={"trade_area_code": str}).set_index("trade_area_code")
gl = units.join(lincs[["linc_period"]])
fig = plt.figure(figsize=(16, 9), dpi=100)
ax = fig.add_axes([0.0, 0.0, 0.68, 1.0]); base(ax)
seq = LinearSegmentedColormap.from_list("s", ["#2b2b29", "#184f95", "#3987e5", "#9ec5f4"])
gl.sort_values("linc_period").plot(ax=ax, column="linc_period", cmap=seq, vmin=0.25, vmax=1, linewidth=0)
seongsu.boundary.plot(ax=ax, color="white", linewidth=1.2, linestyle=(0, (2, 2)))
fig.text(0.70, 0.88, "변화 핫스팟", fontsize=28, fontweight="bold")
fig.text(0.70, 0.835, "2022년 → 2024년 → 최근 1년 사이\n같은 유형으로 묶이는 상권 무리가\n얼마나 바뀌었나 (LINC, 0~1)",
         fontsize=13, color=MUTED, va="top", linespacing=1.6)
grp = lincs.assign(path=lambda d: d["2022년"] + " → " + d["최근 1년"]).groupby("path")["linc_period"].agg(["count", "mean"])
show = grp[grp["count"] >= 5].sort_values("mean", ascending=False).head(8)
fig.text(0.70, 0.66, "유형 이동별 평균 LINC (5곳 이상)", fontsize=13, color=INK, fontweight="bold")
for i, (pth, r) in enumerate(show.iterrows()):
    y = 0.62 - i * 0.045
    fig.text(0.70, y, pth, fontsize=12, color=INK, va="center")
    fig.text(0.90, y, f"{r['mean']:.2f}", fontsize=12, color=INK, va="center", fontweight="bold")
    fig.text(0.95, y, f"{int(r['count'])}곳", fontsize=10, color=MUTED, va="center")
cax = fig.add_axes([0.70, 0.17, 0.25, 0.018])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=seq, norm=plt.Normalize(0.25, 1)), cax=cax, orientation="horizontal")
cb.outline.set_visible(False); cb.ax.tick_params(colors=MUTED)
fig.text(0.70, 0.2, "LINC: 1에 가까울수록 변화가 큼", fontsize=11, color=MUTED)
foot(fig, "geosnap lincs_from_gdf, 각 기간 최빈 유형 기준. 점선: 성수 일대.")
fig.savefig(os.path.join(OUT, "linc_map.png"), dpi=150, facecolor=BG); plt.close(fig)
print("F6 done")
