"""4단계-1: 유형 수 결정. geosnap find_k를 표준화 방식 2가지로 실행한다."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "adapters"))
import pandas as pd
from sklearn.preprocessing import RobustScaler
from geosnap.analyze import find_k
from seoul_to_geosnap import load_geosnap_input, VARIABLES, UNIT, TIME

out = sys.argv[1]
gdf = load_geosnap_input(balanced_only=True, start_quarter="20221")
cols = list(VARIABLES)
rows = []
for sname, scaler in [("std", "std"), ("robust", RobustScaler())]:
    for method in ["kmeans", "ward"]:
        best, table = find_k(gdf, method=method, columns=cols, temporal_index=TIME, unit_index=UNIT,
                             scaler=scaler, pooling="fixed", random_state=0, min_k=3, max_k=8,
                             return_table=True)
        table = table.reset_index().assign(scaler=sname, method=method)
        print(sname, method, "best:", dict(best) if hasattr(best, "items") else best)
        rows.append(table)
res = pd.concat(rows)
res.to_csv(out, index=False)
print(res.to_string())
