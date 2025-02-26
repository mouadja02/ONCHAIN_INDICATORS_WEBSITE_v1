import streamlit as st
from my_draw_component import st_my_draw_component

st.set_page_config(page_title="Drawable Plotly App", layout="wide")

st.title("My Drawable Plotly Chart")

# Provide data to the component
x_data = [1,2,3,4]
y_data = [10,15,5,12]

# Call your custom component
drawn_shapes = st_my_draw_component(x=x_data, y=y_data, key="chart1")

st.write("Shapes or relayout data from the front-end:")
st.json(drawn_shapes)
