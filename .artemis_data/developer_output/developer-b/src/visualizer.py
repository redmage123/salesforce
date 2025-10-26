import pandas as pd
import matplotlib.pyplot as plt

class Visualizer:
    def __init__(self, data: pd.DataFrame):
        self._data = data

    def plot_histogram(self, column_name: str) -> None:
        plt.figure(figsize=(10, 6))
        self._data[column_name].hist()
        plt.title(f'Histogram of {column_name}')
        plt.xlabel(column_name)
        plt.ylabel('Frequency')
        plt.show()

    def plot_scatter(self, column_x: str, column_y: str) -> None:
        plt.figure(figsize=(10, 6))
        plt.scatter(self._data[column_x], self._data[column_y])
        plt.title(f'Scatter plot of {column_x} vs {column_y}')
        plt.xlabel(column_x)
        plt.ylabel(column_y)
        plt.show()
