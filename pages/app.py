import streamlit as st
from my_draw_component import st_my_draw_component

st.set_page_config(page_title="Drawable Plotly App", layout="wide")

st.title("My Drawable Plotly Chart (Deployed on Streamlit)")

# Some data to pass to the front-end
x_data = [1, 2, 3, 4]
y_data = [10, 15, 5, 12]

shapes_info = st_my_draw_component(x=x_data, y=y_data, key="draw1")

st.write("Shape data (or relayout data) from the front-end:")
st.json(shapes_info)
