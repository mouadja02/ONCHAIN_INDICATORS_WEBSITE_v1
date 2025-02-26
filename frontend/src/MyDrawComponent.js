/* 
  A plain JS approach. If you prefer React, you'll need to 
  import React and create a React component. 
*/

// We assume window.streamlit is provided by the Streamlit component environment.
const MyDrawComponent = () => {
  // This function is called once the component receives data from Python
  const renderChart = (args) => {
    const rootDiv = document.getElementById("root");
    if (!rootDiv) return;

    // Create the chart data from 'args.data' or fallback if none
    const trace = {
      x: args?.x || [1, 2, 3],
      y: args?.y || [10, 15, 5],
      mode: "lines+markers",
      name: "Sample",
    };

    const layout = {
      dragmode: "drawline",
      newshape: {
        line: { color: "cyan" },
      },
      width: 800,
      height: 500,
    };

    const config = {
      modeBarButtonsToAdd: ["drawline", "drawrect", "drawcircle", "drawopenpath", "eraseshape"],
      scrollZoom: true,
    };

    Plotly.newPlot(rootDiv, [trace], layout, config).then((gd) => {
      // Listen for shape events
      gd.on("plotly_relayout", (eventData) => {
        // 'plotly_relayout' is fired for many actions (zoom, pan, shape drawing, etc.)
        // If shapes were added or changed, eventData might have shape info. 
        // For example: {'shapes[0].x0':..., 'shapes[0].y0':...}
        // We can pass this back to Python:
        window.streamlit.setComponentValue(eventData);
      });
    });
  };

  // Listen for Streamlit messages
  if (window.streamlit) {
    window.streamlit.onRender((event) => {
      // event.detail contains the args from Python
      renderChart(event.detail);
    });
  }

  // Return an object with some optional methods
  return {};
};

// Initialize
MyDrawComponent();
