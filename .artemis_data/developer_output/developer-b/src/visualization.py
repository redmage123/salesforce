import plotly.express as px
import pandas as pd
from plotly.graph_objects import Figure

class Visualizer:
    def __init__(self, data: pd.DataFrame):
        self._data = data

    def generate_interactive_plot(self, x_col: str, y_col: str) -> Figure:
        return px.line(self._data, x=x_col, y=y_col, title='Execution Time Analysis')
