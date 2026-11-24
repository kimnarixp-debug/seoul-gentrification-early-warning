"""3단계 확인용 지도: 어댑터 결과(상권 경계 + 변수)가 제대로 붙었는지 본다. 분석 아님."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["WenQuanYi Zen Hei", "NanumGothic", "Malgun Gothic", "AppleGothic", "sans-serif"]  # 한글 글꼴
from seoul_to_geosnap import load_geosnap_input, load_boundaries

out = sys.argv[1]
g = load_geosnap_input(balanced_only=True)
last = g[g["quarter_code"] == g["quarter_code"].max()]
fig, axes = plt.subplots(1, 2, figsize=(16, 8))
for ax, col, title in [(axes[0], "young_sales_share", "20~30대 매출 비중 (%)"),
                       (axes[1], "franchise_share", "프랜차이즈 점포 비중 (%)")]:
    load_boundaries().plot(ax=ax, color="#eeeeee", edgecolor="none")
    last.plot(ax=ax, column=col, cmap="viridis", scheme="quantiles", k=5, legend=True,
              legend_kwds={"loc": "lower left", "fontsize": 8})
    last[last["seongsu_area"]].boundary.plot(ax=ax, color="red", linewidth=0.8)
    ax.set_title(f"{title}, {last['quarter_code'].iloc[0]}"); ax.set_axis_off()
fig.suptitle("서울 상권 1,418개 (21분기 연속 관측), 빨간 선: 성수 일대 13개 상권")
fig.tight_layout(); fig.savefig(out, dpi=110)
print("saved", out)
