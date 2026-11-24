"""0단계: geosnap 공식 예제 07(visualizing_neighborhood_sequences)을 원자료 그대로 재현.

원 노트북: https://github.com/oturns/geosnap/blob/v0.17.0/examples/07_visualizing_neighborhood_sequences.ipynb
원자료: 같은 저장소 examples/data/LA_sequences.csv (인자로 경로 전달)
노트북 셀의 호출을 그대로 옮기고, 그림 저장(save_fig)만 추가했다.
"""
import sys
import matplotlib
matplotlib.use("Agg")
import pandas as pd
from geosnap.visualize import indexplot_seq

csv_path, out_dir = sys.argv[1], sys.argv[2]
df_LA = pd.read_csv(csv_path, converters={"GEO2010": lambda x: str(x)})
print(df_LA.head())
indexplot_seq(df_LA, clustering="seqC1", palette="pastel", save_fig=f"{out_dir}/ex07_seqC1.png", dpi=150)
indexplot_seq(df_LA, clustering="seqC2", palette="pastel", save_fig=f"{out_dir}/ex07_seqC2.png", dpi=150)
print("saved")
