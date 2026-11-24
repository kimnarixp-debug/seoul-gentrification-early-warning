"""4단계-3: 유형·전이 결과 그림.

입력: reports/step4/types.parquet (run/04b_types_transitions.py 결과)
출력: reports/figures/step4/
  F1  types_animation.gif / .mp4 : 분기별 유형 지도 애니메이션
  F1b types_interactive.html     : 분기 슬라이더 + 마우스 오버 지도 (folium)
  F2  type_profile.png           : 유형별 특성 (서울 중앙값 대비)
  F3  transition_matrix_geosnap.png : geosnap plot_transition_matrix (전체 + 이웃 유형별)
  F3b transition_matrix.png      : 전체 전이확률 (발표용)
  F4  type_flow.html / .png      : 2022 -> 2024 -> 최근 1년 유형 이동 흐름 (Sankey)
  F5  ladder_map.png             : 2022 대비 최근 1년 "한 단계 위로" 이동한 상권 지도

배경지도: Esri World Dark Gray Base (server.arcgisonline.com)
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import contextily as ctx
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from PIL import Image
from seoul_to_geosnap import VARIABLES, load_boundaries

TYPES = ["쇠퇴형", "안정형", "교체형", "청년상권형", "고매출밀집형"]
# dataviz 검증 (dark, #1a1a19): 일반 시력 기준 통과, 색약 기준은 교체형-고매출밀집형 쌍이 미달
# -> 범례, 직접 라벨, 마우스 오버로 보완 (reports/step4_types.md)
COLORS = {"쇠퇴형": "#3987e5", "안정형": "#7a7a75", "교체형": "#199e70",
          "청년상권형": "#c98500", "고매출밀집형": "#d55181"}
BG, INK, MUTED, GRID = "#1a1a19", "#ecebe7", "#9b9a95", "#3a3a37"
FONT = "NanumSquare"
plt.rcParams.update({"font.family": [FONT, "NanumGothic", "WenQuanYi Zen Hei"], "axes.unicode_minus": False,
                     "figure.facecolor": BG, "axes.facecolor": BG, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})
BASEMAP = dict(ctx.providers.Esri.WorldGrayCanvas)
BASEMAP.update(name="Esri.WorldDarkGrayBase", attribution="Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap",
               url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}")
BASEMAP = ctx.providers.Esri.WorldGrayCanvas.__class__(BASEMAP)
# 지명: (라벨, x오프셋, y오프셋) 포인트 단위
LANDMARKS = {"3110131": ("성수", 30, 26), "3120044": ("용리단길(삼각지)", -40, -46), "3120039": ("신당", 26, 30),
             "3120102": ("홍대", -40, 30), "3120189": ("강남역", 26, -36), "3110080": ("해방촌", 34, -10),
             "3120028": ("명동", -30, 34)}

IN = sys.argv[1] if len(sys.argv) > 1 else "reports/step4"
OUT = sys.argv[2] if len(sys.argv) > 2 else "reports/figures/step4"
os.makedirs(OUT, exist_ok=True)

t = pd.read_parquet(os.path.join(IN, "types.parquet"))
bound = load_boundaries().to_crs(3857)
g = gpd.GeoDataFrame(bound.merge(t, on="trade_area_code"), crs=3857)
g["color"] = g["type_name"].map(COLORS)
quarters = sorted(g["quarter_code"].unique())
qlabel = {q: f"{q[:4]}년 {q[4]}분기" for q in quarters}
units = g.drop_duplicates("trade_area_code").set_index("trade_area_code")


def basemap_image(ax_extent):
    img, ext = ctx.bounds2img(*ax_extent, source=BASEMAP, zoom=12)
    return img, ext


xmin, ymin, xmax, ymax = bound.total_bounds
pad = 2500
EXTENT = (xmin - pad, ymin - pad, xmax + pad, ymax + pad)
BIMG, BEXT = basemap_image(EXTENT)
seongsu = g[g["seongsu_area"]].drop_duplicates("trade_area_code").dissolve()


def draw_base(ax):
    ax.imshow(BIMG, extent=BEXT, interpolation="bilinear", zorder=0)
    ax.set_xlim(EXTENT[0], EXTENT[2]); ax.set_ylim(EXTENT[1], EXTENT[3]); ax.set_axis_off()


def draw_landmarks(ax, color=INK):
    import matplotlib.patheffects as pe
    for code, (name, dx, dy) in LANDMARKS.items():
        if code not in units.index:
            continue
        c = units.loc[code, "geometry"].centroid
        ax.annotate(name, xy=(c.x, c.y), xytext=(dx, dy), textcoords="offset points", fontsize=13,
                    color=color, fontweight="bold", ha="left" if dx >= 0 else "right", va="center", zorder=6,
                    path_effects=[pe.withStroke(linewidth=3, foreground=BG)],
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.9, shrinkA=2, shrinkB=0))


def attribution(fig):
    fig.text(0.99, 0.01, "자료: 서울 열린데이터광장, 서울시 상권분석서비스 · 배경지도 © Esri, © OpenStreetMap",
             ha="right", va="bottom", fontsize=9, color=MUTED)


# ---------------------------------------------------------------- F1 애니메이션
def frame(q):
    fig = plt.figure(figsize=(16, 9), dpi=100)
    ax = fig.add_axes([0.0, 0.0, 0.66, 1.0])
    draw_base(ax)
    cur = g[g["quarter_code"] == q]
    cur.plot(ax=ax, color=cur["color"], linewidth=0, alpha=0.95, zorder=2)
    seongsu.boundary.plot(ax=ax, color="white", linewidth=1.6, zorder=4)
    draw_landmarks(ax)
    # 오른쪽 패널
    fig.text(0.68, 0.90, "서울 상권 유형 지도", fontsize=30, fontweight="bold", color=INK)
    fig.text(0.68, 0.855, "외식업 기준 1,418개 상권 · geosnap 군집(k-means, 5유형)", fontsize=13, color=MUTED)
    fig.text(0.68, 0.74, qlabel[q], fontsize=44, fontweight="bold", color=INK)
    share = cur["type_name"].value_counts(normalize=True).reindex(TYPES).fillna(0) * 100
    first = g[g["quarter_code"] == quarters[0]]["type_name"].value_counts(normalize=True).reindex(TYPES).fillna(0) * 100
    bx = fig.add_axes([0.68, 0.18, 0.28, 0.48])
    y = np.arange(len(TYPES))[::-1]
    bx.barh(y, share.values, color=[COLORS[k] for k in TYPES], height=0.62)
    bx.scatter(first.values, y, marker="|", s=420, color=INK, linewidths=2, zorder=3)
    for yi, k in zip(y, TYPES):
        bx.text(-1, yi, k, ha="right", va="center", fontsize=16, color=INK, fontweight="bold")
        bx.text(share[k] + 1, yi, f"{share[k]:.1f}%", ha="left", va="center", fontsize=14, color=INK)
    bx.set_xlim(0, 60); bx.set_yticks([]); bx.set_xticks([])
    for s in bx.spines.values():
        s.set_visible(False)
    fig.text(0.68, 0.14, "│ 표시: 2022년 1분기 비중", fontsize=12, color=MUTED)
    fig.text(0.68, 0.105, "흰 테두리: 성수 일대 13개 상권", fontsize=12, color=MUTED)
    attribution(fig)
    buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor=BG); plt.close(fig)
    return Image.open(buf).convert("RGB")


frames = [frame(q) for q in quarters]
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)  # 보고서 애니메이션 페이지용 JPEG
for q, f in zip(quarters, frames):
    f.save(os.path.join(OUT, "frames", f"types_{q}.jpg"), quality=82, optimize=True)
frames[-1].save(os.path.join(OUT, "types_map_latest.png"))
frames[0].save(os.path.join(OUT, "types_map_first.png"))
durations = [900] * (len(frames) - 1) + [2500]
pal = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT) for f in frames]
pal[0].save(os.path.join(OUT, "types_animation.gif"), save_all=True, append_images=pal[1:],
            duration=durations, loop=0, optimize=True)
import imageio.v2 as imageio
with imageio.get_writer(os.path.join(OUT, "types_animation.mp4"), fps=1, codec="libx264", quality=8,
                        macro_block_size=1) as w:
    for f in frames + [frames[-1]] * 2:
        w.append_data(np.asarray(f))
print("F1 done")

# ---------------------------------------------------------------- F1b 인터랙티브 지도 (folium)
import folium
import plotly.graph_objects as go
from folium.plugins import TimeSliderChoropleth

simp = bound[bound["trade_area_code"].isin(units.index)].copy()
simp["geometry"] = simp.geometry.simplify(15)  # 화면 표시용 단순화(15m)
simp = simp.to_crs(4326).reset_index(drop=True)
ts = {q: int(pd.Timestamp(f"{q[:4]}-{(int(q[4]) - 1) * 3 + 1:02d}-01").timestamp()) for q in quarters}
style = {}
for fid, code in enumerate(simp["trade_area_code"]):
    d = t[t["trade_area_code"] == code].set_index("quarter_code")["type_name"]
    style[str(fid)] = {str(ts[q]): {"color": COLORS[d[q]], "opacity": 0.85} for q in quarters if q in d.index}
info = t.sort_values("t").groupby("trade_area_code").agg(
    name=("trade_area_name", "first"), district=("district", "first"),
    first=("type_name", "first"), last=("type_name", "last"))
simp = simp.join(info, on="trade_area_code")
simp["path"] = simp["first"] + " → " + simp["last"]
m = folium.Map(location=[37.555, 126.99], zoom_start=12, tiles=None, control_scale=True)
folium.TileLayer(tiles=BASEMAP["url"], attr="Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap",
                 name="Esri Dark Gray", max_zoom=16).add_to(m)
TimeSliderChoropleth(simp[["geometry"]].to_json(), styledict=style, date_options="YYYY년 Q분기",
                     stroke_width=0, stroke_opacity=0, name="상권 유형").add_to(m)
folium.GeoJson(simp[["geometry", "name", "district", "path"]].to_json(), name="상권 정보",
               style_function=lambda f: {"fillOpacity": 0, "weight": 0},
               highlight_function=lambda f: {"weight": 2, "color": "#ffffff"},
               tooltip=folium.GeoJsonTooltip(["name", "district", "path"], aliases=["상권", "자치구", "2022년 1분기 → 2026년 1분기"])
               ).add_to(m)
folium.GeoJson(seongsu.to_crs(4326)[["geometry"]].to_json(), name="성수 일대",
               style_function=lambda f: {"fillOpacity": 0, "color": "#ffffff", "weight": 2.5}).add_to(m)
legend = "".join(f'<div><span style="display:inline-block;width:14px;height:14px;background:{COLORS[k]};'
                 f'margin-right:8px;border-radius:3px;vertical-align:-2px"></span>{k}</div>' for k in TYPES)
m.get_root().html.add_child(folium.Element(
    f'<div style="position:fixed;top:14px;left:60px;z-index:9999;background:rgba(26,26,25,.88);color:{INK};'
    f'padding:12px 16px;border-radius:8px;font:14px NanumSquare,"Malgun Gothic","Apple SD Gothic Neo",sans-serif;line-height:1.7">'
    f'<div style="font-size:19px;font-weight:700;margin-bottom:4px">서울 상권 유형 지도</div>'
    f'<div style="color:{MUTED};font-size:12px;margin-bottom:6px">위쪽 슬라이더로 분기 이동 · 상권에 마우스를 올리면 정보 표시<br>'
    f'흰 테두리: 성수 일대 13개 상권</div>{legend}'
    f'<div style="color:{MUTED};font-size:11px;margin-top:6px">자료: 서울 열린데이터광장, 서울시 상권분석서비스</div></div>'))
folium.LayerControl(collapsed=True).add_to(m)
m.save(os.path.join(OUT, "types_interactive.html"))
print("F1b done")

# ---------------------------------------------------------------- F2 유형 특성
LABEL = {"sales_per_store": "점포당 매출", "sales_yoy": "매출 증가율(전년 대비)", "franchise_share": "프랜차이즈 비중",
         "open_rate": "개업률", "close_rate": "폐업률", "young_sales_share": "20~30대 매출 비중",
         "store_density": "점포 밀도"}
UNIT = {"sales_per_store": "만 원", "sales_yoy": "%", "franchise_share": "%", "open_rate": "%",
        "close_rate": "%", "young_sales_share": "%", "store_density": "개/ha"}
cols = list(VARIABLES)
med = t.groupby("type_name")[cols].median().reindex(TYPES)
allmed = t[cols].median()
ratio = med / allmed.replace(0, np.nan)
rel = np.log2(ratio.clip(lower=1 / 8, upper=8))
# sales_yoy는 0 근처 값이라 비율 대신 차이(%p)를 같은 색 척도로 표시 (±8%p -> ±3)
rel["sales_yoy"] = ((med["sales_yoy"] - allmed["sales_yoy"]) / 8 * 3).clip(-3, 3)
fig, ax = plt.subplots(figsize=(16, 7.5))
from matplotlib.colors import LinearSegmentedColormap
div = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#3a3a37", "#eb6834"])
ax.imshow(rel.values, cmap=div, vmin=-2, vmax=2, aspect="auto")
for i, k in enumerate(TYPES):
    for j, c in enumerate(cols):
        v = med.loc[k, c]
        txt = f"{v / 1e4:,.0f}" if c == "sales_per_store" else f"{v:.1f}"
        ax.text(j, i, f"{txt}{UNIT[c] if c != 'sales_per_store' else ''}", ha="center", va="center", fontsize=15,
                color=INK, fontweight="bold")
ax.set_xticks(range(len(cols)), [f"{LABEL[c]}\n({UNIT[c]})" if c == "sales_per_store" else LABEL[c] for c in cols],
              fontsize=13, color=INK)
ax.set_yticks(range(len(TYPES)), [""] * len(TYPES))
for i, k in enumerate(TYPES):
    share = (t["type_name"] == k).mean() * 100
    ax.text(-0.6, i, f"{k}  ", ha="right", va="center", fontsize=17, fontweight="bold", color=COLORS[k])
    ax.text(-0.6, i + 0.3, f"{share:.0f}%  ", ha="right", va="center", fontsize=11, color=MUTED)
ax.tick_params(length=0); ax.xaxis.tick_top()
for s in ax.spines.values():
    s.set_visible(False)
ax.set_xticks(np.arange(-.5, len(cols)), minor=True); ax.set_yticks(np.arange(-.5, len(TYPES)), minor=True)
ax.grid(which="minor", color=BG, linewidth=4); ax.tick_params(which="minor", length=0)
fig.suptitle("상권 유형별 특성 (중앙값)", x=0.02, ha="left", fontsize=24, fontweight="bold", y=0.99)
fig.text(0.02, 0.02, "색: 서울 전체 중앙값보다 높으면 주황, 낮으면 파랑. 숫자 아래 작은 글씨: 전체 상권-분기 중 비중. "
         "2022년 1분기~2026년 1분기, 1,418개 상권.", fontsize=11, color=MUTED)
fig.subplots_adjust(left=0.13, right=0.99, top=0.82, bottom=0.07)
fig.savefig(os.path.join(OUT, "type_profile.png"), dpi=150, facecolor=BG); plt.close(fig)
print("F2 done")

# ---------------------------------------------------------------- F3 전이행렬 (geosnap 함수)
from geosnap.visualize import plot_transition_matrix
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "text.color": "black",
                     "axes.labelcolor": "black", "xtick.color": "black", "ytick.color": "black"})
gg = gpd.GeoDataFrame(g.drop(columns=["color"]), crs=3857)
np.random.seed(0)
plot_transition_matrix(gg, cluster_col="type", w_type="knn", w_options={"k": 6}, temporal_index="t",
                       unit_index="trade_area_code", savefig=os.path.join(OUT, "transition_matrix_geosnap.png"),
                       dpi=150, suptitle="Spatial Markov, knn=6 (0 decline, 1 stable, 2 churn, 3 youth, 4 high-sales)")
plt.close("all")
plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG, "text.color": INK, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
print("F3 done")

# ---------------------------------------------------------------- F3b 전체 전이확률 (발표용)
P = pd.read_csv(os.path.join(IN, "transition_global.csv"), index_col=0).reindex(index=TYPES, columns=TYPES)
fig, ax = plt.subplots(figsize=(11, 9))
seq = LinearSegmentedColormap.from_list("seq", ["#222221", "#184f95", "#3987e5", "#9ec5f4"])
ax.imshow(P.values, cmap=seq, vmin=0, vmax=1)
for i in range(5):
    for j in range(5):
        v = P.values[i, j]
        ax.text(j, i, f"{v * 100:.0f}%" if v >= 0.005 else "·", ha="center", va="center", fontsize=17,
                fontweight="bold", color="#0b0b0b" if v > 0.6 else INK)
ax.set_xticks(range(5), TYPES, fontsize=14); ax.set_yticks(range(5), TYPES, fontsize=14)
for lab, k in zip(ax.get_xticklabels(), TYPES):
    lab.set_color(COLORS[k]); lab.set_fontweight("bold")
for lab, k in zip(ax.get_yticklabels(), TYPES):
    lab.set_color(COLORS[k]); lab.set_fontweight("bold")
ax.xaxis.tick_top(); ax.tick_params(length=0)
ax.set_xlabel("다음 분기 유형 →", fontsize=13, color=MUTED, labelpad=14); ax.xaxis.set_label_position("top")
ax.set_ylabel("이번 분기 유형 ↓", fontsize=13, color=MUTED, rotation=0, ha="right", va="bottom", labelpad=10)
ax.yaxis.set_label_coords(-0.02, 1.02)
ax.set_xticks(np.arange(-.5, 5), minor=True); ax.set_yticks(np.arange(-.5, 5), minor=True)
ax.grid(which="minor", color=BG, linewidth=4); ax.tick_params(which="minor", length=0)
for s in ax.spines.values():
    s.set_visible(False)
fig.suptitle("한 분기 뒤 유형이 바뀔 확률", x=0.03, ha="left", fontsize=24, fontweight="bold")
fig.text(0.03, 0.02, "geosnap transition (마르코프 전이확률), 2022년 1분기~2026년 1분기, 1,418개 상권. "
         "대각선 = 유형 유지.", fontsize=11, color=MUTED)
fig.subplots_adjust(left=0.2, right=0.97, top=0.8, bottom=0.07)
fig.savefig(os.path.join(OUT, "transition_matrix.png"), dpi=150, facecolor=BG); plt.close(fig)
print("F3b done")


# ---------------------------------------------------------------- F4 이동 흐름 (Sankey)
def period_type(d):
    """기간 안 최빈 유형. 동률이면 가장 최근 분기의 유형."""
    vc = d["type_name"].value_counts()
    top = vc[vc == vc.max()].index
    if len(top) == 1:
        return top[0]
    return d[d["type_name"].isin(top)].sort_values("t")["type_name"].iloc[-1]


PERIODS = {"2022년": (1, 4), "2024년": (9, 12), "최근 1년": (14, 17)}  # 최근 1년 = 2025Q2~2026Q1
pt = pd.DataFrame({name: t[(t.t >= a) & (t.t <= b)].groupby("trade_area_code").apply(period_type, include_groups=False)
                   for name, (a, b) in PERIODS.items()})
pt.join(units[["trade_area_name", "district"]]).to_csv(os.path.join(IN, "period_types.csv"))
names = list(PERIODS)
nodes, idx = [], {}
for p in names:
    for k in TYPES:
        idx[(p, k)] = len(nodes); nodes.append((p, k))
src, dst, val, lcol = [], [], [], []
for a, b in zip(names[:-1], names[1:]):
    ct = pd.crosstab(pt[a], pt[b])
    for ka in ct.index:
        for kb in ct.columns:
            if ct.loc[ka, kb] > 0:
                src.append(idx[(a, ka)]); dst.append(idx[(b, kb)]); val.append(int(ct.loc[ka, kb]))
                up = TYPES.index(kb) > TYPES.index(ka) and kb in ("청년상권형", "고매출밀집형")
                c = COLORS[kb]
                lcol.append(f"rgba({int(c[1:3], 16)},{int(c[3:5], 16)},{int(c[5:7], 16)},{0.75 if up else 0.18})")
counts = {(p, k): int((pt[p] == k).sum()) for p in names for k in TYPES}
sk = go.Figure(go.Sankey(
    arrangement="fixed",
    node=dict(label=[f"{k} {counts[(p, k)]}" for p, k in nodes], color=[COLORS[k] for p, k in nodes],
              pad=18, thickness=22, line=dict(width=0),
              x=[0.01 + 0.98 * names.index(p) / (len(names) - 1) for p, k in nodes],
              y=[0.02 + 0.96 * TYPES[::-1].index(k) / (len(TYPES) - 1) for p, k in nodes],
              hovertemplate="%{label}개 상권<extra></extra>"),
    link=dict(source=src, target=dst, value=val, color=lcol,
              hovertemplate="%{source.label} → %{target.label}: %{value}개 상권<extra></extra>"),
))
for i, p in enumerate(names):
    sk.add_annotation(x=i / (len(names) - 1), y=1.07, xref="paper", yref="paper", text=f"<b>{p}</b>",
                      showarrow=False, font=dict(size=18, color=INK))
sk.update_layout(
    title=dict(text="상권 유형은 어디서 어디로 이동했나 <span style='font-size:14px;color:#9b9a95'>"
                    "· 진한 띠: 청년상권형·고매출밀집형으로 올라간 이동</span>", x=0.02, font=dict(size=24)),
    paper_bgcolor=BG, font=dict(family="NanumSquare, Malgun Gothic, Apple SD Gothic Neo, sans-serif", color=INK, size=14),
    margin=dict(l=30, r=30, t=110, b=50), height=760, width=1400)
sk.add_annotation(x=0, y=-0.06, xref="paper", yref="paper", showarrow=False, font=dict(size=11, color=MUTED),
                  text="각 기간(4분기) 안에서 가장 많이 속한 유형 기준. 1,418개 상권. 최근 1년 = 2025년 2분기~2026년 1분기.")
sk.write_html(os.path.join(OUT, "type_flow.html"), include_plotlyjs=True)
try:
    sk.write_image(os.path.join(OUT, "type_flow.png"), scale=2)
except Exception as e:  # kaleido가 브라우저를 못 찾는 경우 run/04d에서 캡처
    print("Sankey PNG 저장 실패:", type(e).__name__, str(e)[:200])
print("F4 done")

# ---------------------------------------------------------------- F5 "한 단계 위로" 지도
up1 = pt[(pt["2022년"].isin(["안정형", "교체형", "쇠퇴형"])) & (pt["최근 1년"] == "청년상권형")].index
up2 = pt[(pt["2022년"] == "청년상권형") & (pt["최근 1년"] == "고매출밀집형")].index
up0 = pt[(pt["2022년"].isin(["안정형", "교체형", "쇠퇴형"])) & (pt["최근 1년"] == "고매출밀집형")].index
pd.DataFrame({"구분": ["안정·교체·쇠퇴→청년상권형"] * len(up1) + ["청년상권형→고매출밀집형"] * len(up2)
              + ["안정·교체·쇠퇴→고매출밀집형"] * len(up0)}, index=list(up1) + list(up2) + list(up0)) \
    .join(pt).join(units[["trade_area_name", "district", "trade_area_type"]]) \
    .to_csv(os.path.join(IN, "moved_up.csv"), encoding="utf-8-sig")
fig = plt.figure(figsize=(16, 9), dpi=100)
ax = fig.add_axes([0.0, 0.0, 0.7, 1.0]); draw_base(ax)
u = units.reset_index()
u = gpd.GeoDataFrame(u, geometry="geometry", crs=3857)
u.plot(ax=ax, color="#4a4a47", linewidth=0, zorder=1)
u[u["trade_area_code"].isin(up1)].plot(ax=ax, color=COLORS["청년상권형"], edgecolor=COLORS["청년상권형"], linewidth=1.2, zorder=3)
u[u["trade_area_code"].isin(up2)].plot(ax=ax, color=COLORS["고매출밀집형"], edgecolor=COLORS["고매출밀집형"], linewidth=1.2, zorder=3)
u[u["trade_area_code"].isin(up0)].plot(ax=ax, color=COLORS["고매출밀집형"], linewidth=0.6, zorder=3, hatch="///",
                                       edgecolor="#1a1a19")
seongsu.boundary.plot(ax=ax, color="white", linewidth=1.6, zorder=4)
draw_landmarks(ax)
fig.text(0.71, 0.88, "젠트리피케이션은\n어디로 번졌나", fontsize=30, fontweight="bold", color=INK, va="top")
fig.text(0.71, 0.70, "2022년 → 최근 1년(2025년 2분기~2026년 1분기)\n유형이 한 단계 위로 올라간 상권", fontsize=14,
         color=MUTED, va="top", linespacing=1.6)
items = [(COLORS["청년상권형"], f"안정·교체형 → 청년상권형   {len(up1)}곳", None),
         (COLORS["고매출밀집형"], f"청년상권형 → 고매출밀집형   {len(up2)}곳", None),
         (COLORS["고매출밀집형"], f"안정·교체형 → 고매출밀집형   {len(up0)}곳", "///"),
         ("#4a4a47", "그 밖의 상권", None)]
for i, (c, lab, h) in enumerate(items):
    yy = 0.56 - i * 0.06
    rax = fig.add_axes([0.71, yy - 0.015, 0.022, 0.035]); rax.set_axis_off()
    rax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=c, hatch=h, edgecolor=BG if h else c, transform=rax.transAxes))
    fig.text(0.74, yy, lab, fontsize=15, color=INK, va="center")
fig.text(0.71, 0.27, "흰 테두리: 성수 일대 13개 상권", fontsize=12, color=MUTED)
fig.text(0.71, 0.23, "각 기간 안에서 가장 많이 속한 유형 기준", fontsize=12, color=MUTED)
attribution(fig)
fig.savefig(os.path.join(OUT, "ladder_map.png"), dpi=150, facecolor=BG); plt.close(fig)
print("F5 done")

# ---------------------------------------------------------------- F6 이웃 효과 (geosnap 공간 전이확률)
sp = pd.read_csv(os.path.join(IN, "transition_spatial_knn6.csv"))
glob_p = P
fig, ax = plt.subplots(figsize=(16, 8))
rows = [("안정형", "청년상권형"), ("교체형", "청년상권형"), ("청년상권형", "고매출밀집형")]
lags = ["안정형", "교체형", "청년상권형", "고매출밀집형"]
width = 0.19
for r, (a, b) in enumerate(rows):
    for j, lag in enumerate(lags):
        v = sp[(sp["이웃유형"] == lag) & (sp["이번분기"] == a)][b].iloc[0] * 100
        x = r + (j - 1.5) * (width + 0.02)
        ax.bar(x, v, width=width, color=COLORS[lag], zorder=2)
        import matplotlib.patheffects as pe
        ax.text(x, v + 0.3, f"{v:.1f}%", ha="center", va="bottom", fontsize=13, color=INK, fontweight="bold",
                zorder=5, path_effects=[pe.withStroke(linewidth=4, foreground=BG)])
    gv = glob_p.loc[a, b] * 100
    ax.hlines(gv, r - 0.45, r + 0.45, colors=INK, linestyles=(0, (4, 3)), lw=1.4, zorder=3)
    ax.text(r + 0.46, gv, f"전체 평균\n{gv:.1f}%", va="center", ha="left", fontsize=11, color=MUTED)
ax.set_xticks(range(len(rows)), [f"{a} → {b}" for a, b in rows], fontsize=16, color=INK)
ax.set_yticks([]); ax.set_ylim(0, None); ax.tick_params(length=0)
for s_ in ax.spines.values():
    s_.set_visible(False)
ax.axhline(0, color=GRID, lw=1)
handles = [Patch(color=COLORS[l], label=f"이웃 상권이 주로 {l}") for l in lags]
ax.legend(handles=handles, loc="upper right", frameon=False, fontsize=13, labelcolor=INK)
fig.suptitle("이웃이 뜨면 나도 뜬다: 한 분기 뒤 한 단계 위 유형으로 바뀔 확률", x=0.03, ha="left", fontsize=24,
             fontweight="bold")
fig.text(0.03, 0.02, "geosnap transition(w_type='knn', k=6): 가장 가까운 6개 상권 중 가장 많은 유형별 전이확률. "
         "Spatial Markov 검정 Q=448.6, p<0.001. 2022년 1분기~2026년 1분기, 1,418개 상권.", fontsize=11, color=MUTED)
fig.subplots_adjust(left=0.03, right=0.93, top=0.86, bottom=0.12)
fig.savefig(os.path.join(OUT, "neighbor_effect.png"), dpi=150, facecolor=BG); plt.close(fig)
print("F6 done")
