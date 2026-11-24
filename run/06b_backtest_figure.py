"""6단계 그림: 과거 검증 결과 (reports/step6/*.csv -> reports/figures/step6/backtest.png)"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd

IN = sys.argv[1] if len(sys.argv) > 1 else "reports/step6"
OUT = sys.argv[2] if len(sys.argv) > 2 else "reports/figures/step6"
os.makedirs(OUT, exist_ok=True)
BG, INK, MUTED, GRID = "#1a1a19", "#ecebe7", "#9b9a95", "#3a3a37"
C = {"유형 유지": "#7a7a75", "비공간 전이확률": "#3987e5", "공간 모형": "#c98500"}
plt.rcParams.update({"font.family": ["NanumSquare", "NanumGothic"], "figure.facecolor": BG, "axes.facecolor": BG,
                     "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.unicode_minus": False})
acc = pd.read_csv(os.path.join(IN, "accuracy.csv"))
warn = pd.read_csv(os.path.join(IN, "warning_performance.csv"))
stroke = [pe.withStroke(linewidth=4, foreground=BG)]

fig = plt.figure(figsize=(16, 8.4))
# (1) 전체 적중률
ax = fig.add_axes([0.04, 0.14, 0.42, 0.62])
targets = ["2025년 4분기 유형", "2025년 기간 유형"]
methods = ["유형 유지", "비공간 전이확률", "공간 모형"]
for i, tg in enumerate(targets):
    for j, m in enumerate(methods):
        v = acc[(acc["실제값"] == tg) & (acc["방법"] == m)]["적중률(%)"].iloc[0]
        x = i + (j - 1) * 0.27
        ax.bar(x, v, width=0.24, color=C[m])
        ax.text(x, v + 1, f"{v:.0f}%", ha="center", fontsize=15, fontweight="bold", color=INK, path_effects=stroke)
ax.set_xticks(range(2), ["한 분기(2025년 4분기)", "1년 최빈(2025년)"], fontsize=13, color=INK)
ax.set_ylim(0, 92); ax.set_yticks([]); ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.axhline(0, color=GRID)
fig.text(0.04, 0.84, "1년 뒤 유형 적중률", fontsize=19, fontweight="bold")
fig.text(0.04, 0.80, "1,418개 상권, 2024년 4분기 자료로 1년 뒤 예측", fontsize=12, color=MUTED)
for k, (m, c) in enumerate(C.items()):
    fig.text(0.04 + k * 0.14, 0.06, "■", color=c, fontsize=15, va="center")
    fig.text(0.055 + k * 0.14, 0.06, m if m != "공간 모형" else "공간 모형(이웃 반영)", fontsize=12, va="center")

# (2) 확산 경보 상위 N 적중
ax2 = fig.add_axes([0.55, 0.14, 0.42, 0.62])
row = warn[(warn["경보"].str.startswith("확산")) & (warn["실제값"] == "2025년 4분기")].iloc[0]
base = row["기본 비율(%)"] / 100
groups = [("상위 20곳", 20), ("상위 50곳", 50)]
for i, (lab, n) in enumerate(groups):
    vals = [("무작위로 고르면", base * n, "#7a7a75"), ("비공간 전이확률", row[f"상위{n} 적중 비공간"], "#3987e5"),
            ("공간 모형", row[f"상위{n} 적중 공간"], "#c98500")]
    for j, (nm, v, c) in enumerate(vals):
        x = i + (j - 1) * 0.27
        ax2.bar(x, v, width=0.24, color=c)
        ax2.text(x, v + 0.12, f"{v:.1f}곳" if j == 0 else f"{int(v)}곳", ha="center", fontsize=14, fontweight="bold",
                 color=INK, path_effects=stroke)
ax2.set_xticks(range(2), [g[0] for g in groups], fontsize=13, color=INK)
ax2.set_yticks([]); ax2.tick_params(length=0); ax2.set_ylim(0, 6)
for s in ax2.spines.values():
    s.set_visible(False)
ax2.axhline(0, color=GRID)
fig.text(0.55, 0.84, "확산 경보: 상위권에서 실제로 청년상권형이 된 상권 수", fontsize=19, fontweight="bold")
fig.text(0.55, 0.80, f"대상 {int(row['대상 상권'])}곳 중 실제 전환 {int(row['실제로 바뀐 상권'])}곳({row['기본 비율(%)']}%). "
         f"AUC 공간 {row['AUC 공간']:.2f} · 비공간 {row['AUC 비공간']:.2f} · 무작위 0.50", fontsize=12, color=MUTED)
fig.suptitle("과거 검증: 2024년 4분기 자료로 2025년 4분기를 맞혔나", x=0.04, ha="left", fontsize=25, fontweight="bold", y=0.985)
fig.text(0.55, 0.06, "■ 회색: 무작위로 고를 때 기대 적중 수", fontsize=12, color=MUTED, va="center")
fig.savefig(os.path.join(OUT, "backtest.png"), dpi=150, facecolor=BG)
print("saved")
