import pandas as pd
from typing import List, Dict, Any

class DataAnalyzer:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def analyze(self) -> Dict[str, Any]:
        return {
            'mean': self.data.mean(),
            'median': self.data.median(),
            'std': self.data.std()
        }