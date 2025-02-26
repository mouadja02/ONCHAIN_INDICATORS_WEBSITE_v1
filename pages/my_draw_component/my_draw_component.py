import os
import streamlit.components.v1 as components

_RELEASE = True  # <-- set to True for production

if not _RELEASE:
    _component_func = components.declare_component(
        "my_draw_component",
        url="http://localhost:3000"
    )
else:
    build_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
    _component_func = components.declare_component(
        "my_draw_component", 
        path=build_dir
    )

def st_my_draw_component(x=None, y=None, key=None):
    component_value = _component_func(
        x=x,
        y=y,
        key=key,
    )
    return component_value
