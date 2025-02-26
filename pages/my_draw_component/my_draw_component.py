import os
import streamlit.components.v1 as components

# Decide if you're in release mode
_RELEASE = True

if not _RELEASE:
    # For local dev server (if you used npm start on your front end)
    _component_func = components.declare_component(
        "my_draw_component",
        url="http://localhost:3000"
    )
else:
    # Production: serve from build folder
    build_dir = os.path.join(os.path.dirname(__file__), "build")
    _component_func = components.declare_component(
        "my_draw_component", 
        path=build_dir
    )

def st_my_draw_component(x=None, y=None, key=None):
    """
    This function is called in your app. It sends data to the front-end
    and returns shape data from the front-end.
    """
    component_value = _component_func(
        x=x,
        y=y,
        key=key
    )
    return component_value
