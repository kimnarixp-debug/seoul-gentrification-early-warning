"""발표용 방법론 그림: 유형 수와 표준화 방식을 어떻게 정했나 (값은 reports/step4/find_k.csv 등 기존 결과).
  clustering_choice.png
QuantileTransformer 실루엣 값은 4단계 비교 실행 출력(reports/step4_types.md 1절)에서 옮김.
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/figures/revision"
os.makedirs(OUT, exist_ok=True)
BG, INK, MUTED, GRID = "#1a1a19", "#ecebe7", "#a3a29d", "#34342f"
ACC, BLUE, GRAY = "#e09a1a", "#3987e5", "#7a7a75"
plt.rcParams.update({"font.family": ["NanumSquare", "NanumGothic"], "axes.unicode_minus": False,
                     "figure.facecolor": BG, "axes.facecolor": BG, "text.color": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": GRID})
stroke = [pe.withStroke(linewidth=4, foreground=BG)]
fk = pd.read_csv("reports/step4/find_k.csv")
km = fk[fk["method"] == "kmeans"]
std = km[km["scaler"] == "std"].set_index("index")["silhouette_score"]
rob = km[km["scaler"] == "robust"].set_index("index")["silhouette_score"]
qua = pd.Series([0.433, 0.479, 0.272, 0.448, 0.207, 0.239], index=range(3, 9))
ms = pd.read_csv("reports/step4/k_min_share.csv").set_index("k")["min_share"]

fig = plt.figure(figsize=(16, 9))
fig.suptitle("유형은 어떻게 나눴나: 표준화 방식 비교 → 유형 수 결정", x=0.03, ha="left", fontsize=26, fontweight="bold", y=0.965)

# (1) 표준화 방식별 실루엣
ax = fig.add_axes([0.05, 0.16, 0.4, 0.6])
for s, c, lab, dy in [(rob, GRAY, "중앙값 기준(Robust)\n극단값에 끌려 구분 실패", -0.09),
                      (qua, BLUE, "순위 기준(Quantile)\n‘개폐업 0’ 여부로만 갈림", 0.0),
                      (std, ACC, "평균·표준편차 (채택)", 0.04)]:
    ax.plot(s.index, s.values, marker="o", color=c, lw=2.5, ms=8)
    ax.text(8.2, s.loc[8] + dy, lab, color=c, fontsize=12.5, va="center", fontweight="bold", path_effects=stroke,
            linespacing=1.3)
ax.set_xlim(2.7, 10.6); ax.set_ylim(-0.2, 0.6); ax.set_xticks(range(3, 9))
ax.set_xlabel("유형 수 k", color=MUTED, fontsize=13)
ax.grid(axis="y", color=GRID, lw=0.8); ax.tick_params(length=0, labelsize=12)
for s_ in ["top", "right"]:
    ax.spines[s_].set_visible(False)
fig.text(0.05, 0.84, "① 표준화 방식 3가지 비교 (실루엣 점수)", fontsize=17, fontweight="bold")
fig.text(0.05, 0.80, "점수가 높아도 극단값·‘개폐업 0’ 상권만 갈라내면 해석할 수 없어 기각", fontsize=12, color=MUTED)

# (2) 유형 수별 가장 작은 유형 비중
ax2 = fig.add_axes([0.56, 0.16, 0.4, 0.6])
cols = [ACC if k == 5 else ("#4a4a47" if k in (4, 6) else GRAY) for k in ms.index]
ax2.axvspan(3.5, 5.5, color="#2a2a27", zorder=0)
ax2.text(4.5, 31.5, "설계서 권고 범위\n4~5개", ha="center", fontsize=12, color=MUTED, va="top")
ax2.bar(ms.index, ms.values, color=cols, width=0.62, zorder=2)
for k, v in ms.items():
    ax2.text(k, v + 0.6, f"{v:.1f}%", ha="center", fontsize=13, color=INK, fontweight="bold", zorder=3, path_effects=stroke)
ax2.text(4, 6.5, "극단값\n유형", ha="center", fontsize=11, color=MUTED)
ax2.text(6, 5.5, "극단값\n유형", ha="center", fontsize=11, color=MUTED)
ax2.set_xticks(ms.index); ax2.set_ylim(0, 33); ax2.set_yticks([])
ax2.set_xlabel("유형 수 k (평균·표준편차 표준화, k-means)", color=MUTED, fontsize=13)
ax2.tick_params(length=0, labelsize=12)
for s_ in ["top", "right", "left"]:
    ax2.spines[s_].set_visible(False)
fig.text(0.56, 0.84, "② 유형 수별 ‘가장 작은 유형’의 비중", fontsize=17, fontweight="bold")
fig.text(0.56, 0.80, "4개·6개는 극단값 상권만 모인 1% 미만 유형이 생김 → 5개로 결정", fontsize=12, color=MUTED)
fig.text(0.05, 0.03, "geosnap find_k·cluster (k-means), 1,418개 상권 × 17분기, 변수 7개. 실루엣: 같은 유형끼리 가깝고 다른 유형과 멀수록 1에 가까움.",
         fontsize=11, color=MUTED)
fig.savefig(os.path.join(OUT, "clustering_choice.png"), dpi=150, facecolor=BG)
print("saved")
