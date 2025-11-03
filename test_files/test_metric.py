import streamlit as st
import numpy as np 

with st.container():
    data = {
        "Omission": [1, 2, 3, 4, 5],
        "Insertion": [0, 1, 2, 3, 4],
        "Mispronunciations": [1, 0, 2, 1, 3]
    }
    st.metric("What you should improve", "reflections")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Omission", value=10, chart_data=data["Omission"], chart_type="line")
    metric_cols[1].metric("Insertion", value=5, chart_data=data["Insertion"], chart_type="line")
    metric_cols[2].metric("Mispronunciations", value=8, chart_data=data["Mispronunciations"], chart_type="line")


