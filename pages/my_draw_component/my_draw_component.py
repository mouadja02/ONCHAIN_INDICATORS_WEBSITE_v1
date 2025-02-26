import os
import streamlit.components.v1 as components

# If True, render the component in "development mode" (localhost).
# If False, render from the built frontend within the 'build' folder.
_RELEASE = False

if not _RELEASE:
    # Development (hot reload) mode
    _component_func = components.declare_component(
        "my_draw_component",
        url="http://localhost:3000"
    )
else:
    # Production mode: path to the build folder
    build_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
    _component_func = components.declare_component("my_draw_component", path=build_dir)


def st_my_draw_component(x=None, y=None, key=None):
    """
    Wrapper function to call our custom drawing component.
    x, y => data arrays to plot
    Returns the shape events from the front-end if any.
    """
    # We pass the data to the front end as "args"
    component_value = _component_func(
        x=x,
        y=y,
        key=key,
    )
    return component_value
