import streamlit as st
import pandas as pd
import numpy as np

# Test if index columns are frozen in UI
df = pd.DataFrame({
    'Col1': np.random.randn(10),
    'Col2': np.random.randn(10),
    'Col3': np.random.randn(10),
    'Col4': np.random.randn(10),
    'Col5': np.random.randn(10),
    'Col6': np.random.randn(10),
    'Col7': np.random.randn(10),
    'Col8': np.random.randn(10),
    'Col9': np.random.randn(10),
})
df = df.set_index(['Col1', 'Col2'])

st.dataframe(df, selection_mode="single-row")
