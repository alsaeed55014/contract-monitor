import pandas as pd

df = pd.DataFrame({"Name": ["Ali"], "الجنسية": ["Filipino"], "Gender": ["Male"]})
cols = list(df.columns)
idx = cols.index("الجنسية")
df.insert(idx, f"🚩_الجنسية", ["flag"])
print(list(df.columns))
