import streamlit as st
from my_draw_component import my_draw_component

st.set_page_config(layout="wide")

st.title("My Custom Drawable Plotly Component")

# Provide data or arguments to your component
shapes_data = st_my_draw_component(
    x=[1,2,3,4],
    y=[10,15,5,12],
    key="draw1"
)

st.write("Shapes (relayout data) returned from the front-end:")
st.json(shapes_data)
