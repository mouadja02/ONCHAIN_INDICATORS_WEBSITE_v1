import os
import streamlit.components.v1 as components

_RELEASE = True  # Set to False if you want to develop with a local dev server

if not _RELEASE:
    # Dev mode: replace this URL with your local dev server if you have one
    _component_func = components.declare_component(
        "my_draw_component",
        url="http://localhost:3000"
    )
else:
    # Production mode: serve from build folder
    build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
    # E.g., path = "my_draw_component/build"
    _component_func = components.declare_component("my_draw_component", path=build_dir)


def st_my_draw_component(x=None, y=None, key=None):
    """
    Streams data to the front-end (args.x, args.y, etc.)
    Returns shape or relayout data from the front-end (a dict or None).
    """
    component_value = _component_func(
        x=x,
        y=y,
        key=key,
    )
    return component_value
