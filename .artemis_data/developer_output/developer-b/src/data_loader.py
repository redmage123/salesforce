from abc import ABC, abstractmethod
import pandas as pd
from typing import Protocol, Any

class DataLoaderStrategy(Protocol):
    def load_data(self, file_path: str) -> pd.DataFrame:
        pass

class CSVDataLoader(DataLoaderStrategy):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path)

class DataLoader:
    def __init__(self, strategy: DataLoaderStrategy):
        self._strategy = strategy

    def load(self, file_path: str) -> pd.DataFrame:
        return self._strategy.load_data(file_path)
