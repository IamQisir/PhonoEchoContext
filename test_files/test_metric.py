import streamlit as st

with st.container():
    st.metric("What you should improve", "relfections")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Omission", 2, delta=1)
    metric_cols[1].metric("Insertion", 0, delta=0)
    metric_cols[2].metric("Mispronunciations", 1, delta=-1)


