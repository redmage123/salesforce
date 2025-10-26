import pandas as pd
from typing import Dict

class DataAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self._data = data

    def compute_metrics(self) -> Dict[str, Any]:
        return {
            'mean_execution_time': self._compute_mean(),
            'max_execution_time': self._compute_max()
        }

    def _compute_mean(self) -> float:
        return self._data['execution_time'].mean()

    def _compute_max(self) -> float:
        return self._data['execution_time'].max()
