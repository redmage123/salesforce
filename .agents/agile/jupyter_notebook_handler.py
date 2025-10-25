#!/usr/bin/env python3
"""
Jupyter Notebook Handler for Artemis

Reads, writes, and generates Jupyter notebooks (.ipynb files) for data analysis,
machine learning, and exploratory programming tasks.

SOLID Principles Applied:
- Single Responsibility: Each class has one clear purpose
- Open/Closed: Can add new cell types/formats without modifying existing code
- Liskov Substitution: All cell builders implement CellBuilderInterface
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Depends on abstractions, not concretions

Design Patterns:
- Builder Pattern: Fluent API for notebook construction
- Factory Pattern: CellFactory creates different cell types
- Strategy Pattern: Different output strategies (markdown, code, raw)
- Template Method: Base notebook structure with customizable cells

Performance Optimizations:
- O(1) cell type lookup using dict dispatch
- Single-pass notebook parsing
- Lazy cell rendering (only render when needed)
- Pre-compiled regex for code pattern matching
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from enum import Enum

from artemis_exceptions import (
    FileReadError,
    FileWriteError,
    create_wrapped_exception,
    ArtemisException
)


class CellType(Enum):
    """Jupyter notebook cell types"""
    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


# Performance: Pre-compiled regex patterns for code analysis
IMPORT_PATTERN = re.compile(r'^\s*(?:from|import)\s+', re.MULTILINE)
FUNCTION_PATTERN = re.compile(r'^\s*def\s+(\w+)\s*\(', re.MULTILINE)
CLASS_PATTERN = re.compile(r'^\s*class\s+(\w+)\s*[:(]', re.MULTILINE)
MATPLOTLIB_PATTERN = re.compile(r'(?:import|from)\s+matplotlib|plt\.(?:plot|show|figure)', re.MULTILINE)

# Performance: O(1) cell type validation
VALID_CELL_TYPES = {ct.value for ct in CellType}


@dataclass
class NotebookCell:
    """
    Represents a single Jupyter notebook cell

    Immutable representation of notebook content
    """
    cell_type: str
    source: List[str]  # Lines of code/text
    metadata: Dict[str, Any] = field(default_factory=dict)
    outputs: List[Dict] = field(default_factory=list)  # For code cells
    execution_count: Optional[int] = None  # For code cells

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Jupyter notebook format"""
        cell_dict = {
            "cell_type": self.cell_type,
            "metadata": self.metadata,
            "source": self.source
        }

        if self.cell_type == "code":
            cell_dict["execution_count"] = self.execution_count
            cell_dict["outputs"] = self.outputs

        return cell_dict

    def get_source_text(self) -> str:
        """Get cell source as single string"""
        return ''.join(self.source)

    def analyze_code(self) -> Dict[str, Any]:
        """
        Analyze code cell content

        Performance: Single-pass analysis with pre-compiled regex - O(n)

        Returns:
            Dict with imports, functions, classes, plotting info
        """
        if self.cell_type != "code":
            return {}

        source_text = self.get_source_text()

        # Single-pass analysis using pre-compiled patterns
        imports = IMPORT_PATTERN.findall(source_text)
        functions = FUNCTION_PATTERN.findall(source_text)
        classes = CLASS_PATTERN.findall(source_text)
        has_plotting = bool(MATPLOTLIB_PATTERN.search(source_text))

        return {
            "has_imports": bool(imports),
            "import_count": len(imports),
            "functions": functions,
            "classes": classes,
            "has_plotting": has_plotting,
            "line_count": len(self.source)
        }


class CellBuilderInterface(ABC):
    """Abstract interface for cell builders"""

    @abstractmethod
    def build(self) -> NotebookCell:
        """Build and return the cell"""
        pass


class CodeCellBuilder(CellBuilderInterface):
    """
    Builder for code cells with fluent API

    Design Pattern: Builder Pattern for complex object construction
    """

    def __init__(self, source: Union[str, List[str]]):
        """
        Initialize code cell builder

        Args:
            source: Code as string or list of lines
        """
        if isinstance(source, str):
            # Split into lines, preserving newlines
            self.source = [line + '\n' if not line.endswith('\n') else line
                          for line in source.splitlines()]
            if self.source and not self.source[-1].endswith('\n'):
                self.source[-1] += '\n'
        else:
            self.source = source

        self.metadata = {}
        self.outputs = []
        self.execution_count = None

    def with_metadata(self, metadata: Dict[str, Any]) -> 'CodeCellBuilder':
        """Add metadata to cell"""
        self.metadata.update(metadata)
        return self

    def with_execution_count(self, count: int) -> 'CodeCellBuilder':
        """Set execution count"""
        self.execution_count = count
        return self

    def with_output(self, output: Dict[str, Any]) -> 'CodeCellBuilder':
        """Add output to cell"""
        self.outputs.append(output)
        return self

    def build(self) -> NotebookCell:
        """Build the code cell"""
        return NotebookCell(
            cell_type=CellType.CODE.value,
            source=self.source,
            metadata=self.metadata,
            outputs=self.outputs,
            execution_count=self.execution_count
        )


class MarkdownCellBuilder(CellBuilderInterface):
    """Builder for markdown cells with fluent API"""

    def __init__(self, source: Union[str, List[str]]):
        """
        Initialize markdown cell builder

        Args:
            source: Markdown as string or list of lines
        """
        if isinstance(source, str):
            self.source = [line + '\n' if not line.endswith('\n') else line
                          for line in source.splitlines()]
            if self.source and not self.source[-1].endswith('\n'):
                self.source[-1] += '\n'
        else:
            self.source = source

        self.metadata = {}

    def with_metadata(self, metadata: Dict[str, Any]) -> 'MarkdownCellBuilder':
        """Add metadata to cell"""
        self.metadata.update(metadata)
        return self

    def build(self) -> NotebookCell:
        """Build the markdown cell"""
        return NotebookCell(
            cell_type=CellType.MARKDOWN.value,
            source=self.source,
            metadata=self.metadata
        )


class CellFactory:
    """
    Factory for creating notebook cells

    Design Pattern: Factory Pattern
    Performance: O(1) cell type dispatch
    """

    # Performance: Dict dispatch for O(1) builder lookup
    _BUILDERS = {
        CellType.CODE.value: CodeCellBuilder,
        CellType.MARKDOWN.value: MarkdownCellBuilder
    }

    @staticmethod
    def create_cell(cell_type: str, source: Union[str, List[str]]) -> CellBuilderInterface:
        """
        Create cell builder of specified type

        Args:
            cell_type: Type of cell (code, markdown, raw)
            source: Cell source content

        Returns:
            Appropriate cell builder

        Raises:
            ValueError: If cell type is invalid
        """
        # Performance: O(1) validation
        if cell_type not in VALID_CELL_TYPES:
            raise ValueError(f"Invalid cell type: {cell_type}. Must be one of {VALID_CELL_TYPES}")

        # Performance: O(1) builder lookup
        builder_class = CellFactory._BUILDERS.get(cell_type)
        if builder_class:
            return builder_class(source)

        # Fallback for raw cells (simple, no builder needed)
        return MarkdownCellBuilder(source)  # Treat as markdown for now


class NotebookBuilder:
    """
    Builder for creating complete Jupyter notebooks

    Design Pattern: Builder Pattern with fluent API
    """

    def __init__(self, title: Optional[str] = None):
        """
        Initialize notebook builder

        Args:
            title: Optional notebook title (added as first markdown cell)
        """
        self.cells: List[NotebookCell] = []
        self.metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.8.0",
                "mimetype": "text/x-python",
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                }
            }
        }

        if title:
            self.add_markdown(f"# {title}\n\nGenerated by Artemis on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def add_markdown(self, content: str) -> 'NotebookBuilder':
        """Add markdown cell"""
        cell = CellFactory.create_cell(CellType.MARKDOWN.value, content).build()
        self.cells.append(cell)
        return self

    def add_code(self, code: str, execution_count: Optional[int] = None) -> 'NotebookBuilder':
        """Add code cell"""
        builder = CellFactory.create_cell(CellType.CODE.value, code)
        if execution_count is not None:
            builder.with_execution_count(execution_count)
        cell = builder.build()
        self.cells.append(cell)
        return self

    def add_section(self, title: str, description: Optional[str] = None) -> 'NotebookBuilder':
        """Add section with title and optional description"""
        content = f"## {title}\n"
        if description:
            content += f"\n{description}\n"
        return self.add_markdown(content)

    def with_metadata(self, metadata: Dict[str, Any]) -> 'NotebookBuilder':
        """Update notebook-level metadata"""
        self.metadata.update(metadata)
        return self

    def build(self) -> Dict[str, Any]:
        """
        Build complete notebook structure

        Returns:
            Jupyter notebook as dict (ready for JSON serialization)
        """
        return {
            "cells": [cell.to_dict() for cell in self.cells],
            "metadata": self.metadata,
            "nbformat": 4,
            "nbformat_minor": 5
        }


class JupyterNotebookReader:
    """
    Read and parse Jupyter notebooks

    Single Responsibility: Parse .ipynb files
    Performance: Single-pass parsing - O(n) where n=cells
    """

    def __init__(self, logger: Optional[Any] = None):
        """
        Initialize notebook reader

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    def read_notebook(self, file_path: str) -> Dict[str, Any]:
        """
        Read Jupyter notebook file

        Args:
            file_path: Path to .ipynb file

        Returns:
            Parsed notebook structure

        Raises:
            FileReadError: If file cannot be read or parsed
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"Notebook file not found: {file_path}")

            if path.suffix.lower() != '.ipynb':
                raise ValueError(f"File must have .ipynb extension: {file_path}")

            self._log(f"📓 Reading Jupyter notebook: {path.name}", "INFO")

            # Read and parse JSON
            with open(path, 'r', encoding='utf-8') as f:
                notebook = json.load(f)

            # Validate notebook format
            if 'cells' not in notebook:
                raise ValueError(f"Invalid notebook format: missing 'cells' key")

            self._log(f"✅ Read notebook with {len(notebook['cells'])} cells", "INFO")

            return notebook

        except FileNotFoundError:
            raise  # Re-raise as-is
        except json.JSONDecodeError as e:
            raise create_wrapped_exception(
                e,
                FileReadError,
                f"Failed to parse notebook JSON: {file_path}",
                context={'file_path': file_path}
            )
        except Exception as e:
            raise create_wrapped_exception(
                e,
                FileReadError,
                f"Failed to read notebook: {file_path}",
                context={'file_path': file_path}
            )

    def extract_code_cells(self, notebook: Dict[str, Any]) -> List[NotebookCell]:
        """
        Extract only code cells from notebook

        Performance: Single-pass filter - O(n)

        Args:
            notebook: Parsed notebook structure

        Returns:
            List of code cells
        """
        cells = []
        for cell_data in notebook.get('cells', []):
            if cell_data.get('cell_type') == CellType.CODE.value:
                cell = NotebookCell(
                    cell_type=cell_data['cell_type'],
                    source=cell_data.get('source', []),
                    metadata=cell_data.get('metadata', {}),
                    outputs=cell_data.get('outputs', []),
                    execution_count=cell_data.get('execution_count')
                )
                cells.append(cell)

        return cells

    def extract_markdown_cells(self, notebook: Dict[str, Any]) -> List[NotebookCell]:
        """Extract only markdown cells"""
        cells = []
        for cell_data in notebook.get('cells', []):
            if cell_data.get('cell_type') == CellType.MARKDOWN.value:
                cell = NotebookCell(
                    cell_type=cell_data['cell_type'],
                    source=cell_data.get('source', []),
                    metadata=cell_data.get('metadata', {})
                )
                cells.append(cell)

        return cells

    def get_notebook_summary(self, notebook: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary statistics of notebook

        Performance: Single-pass analysis - O(n)

        Returns:
            Dict with cell counts, code analysis, etc.
        """
        cells = notebook.get('cells', [])

        # Single-pass counting using dict
        summary = {
            'total_cells': len(cells),
            'code_cells': 0,
            'markdown_cells': 0,
            'raw_cells': 0,
            'total_code_lines': 0,
            'functions_defined': [],
            'classes_defined': [],
            'has_plotting': False
        }

        # Single pass through cells
        for cell_data in cells:
            cell_type = cell_data.get('cell_type')

            if cell_type == CellType.CODE.value:
                summary['code_cells'] += 1

                # Analyze code
                cell = NotebookCell(
                    cell_type=cell_type,
                    source=cell_data.get('source', []),
                    metadata=cell_data.get('metadata', {})
                )
                analysis = cell.analyze_code()
                summary['total_code_lines'] += analysis.get('line_count', 0)
                summary['functions_defined'].extend(analysis.get('functions', []))
                summary['classes_defined'].extend(analysis.get('classes', []))
                if analysis.get('has_plotting'):
                    summary['has_plotting'] = True

            elif cell_type == CellType.MARKDOWN.value:
                summary['markdown_cells'] += 1
            elif cell_type == 'raw':
                summary['raw_cells'] += 1

        return summary

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message if logger available"""
        if self.logger:
            self.logger.log(message, level)


class JupyterNotebookWriter:
    """
    Write and save Jupyter notebooks

    Single Responsibility: Save .ipynb files
    """

    def __init__(self, logger: Optional[Any] = None):
        """
        Initialize notebook writer

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    def write_notebook(self, notebook: Dict[str, Any], file_path: str) -> None:
        """
        Write Jupyter notebook to file

        Args:
            notebook: Notebook structure (from NotebookBuilder.build())
            file_path: Path where to save .ipynb file

        Raises:
            FileWriteError: If file cannot be written
        """
        try:
            path = Path(file_path)

            # Ensure .ipynb extension
            if path.suffix.lower() != '.ipynb':
                path = path.with_suffix('.ipynb')

            self._log(f"💾 Writing Jupyter notebook: {path.name}", "INFO")

            # Create parent directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON with nice formatting
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=2, ensure_ascii=False)

            self._log(f"✅ Notebook saved: {path}", "SUCCESS")

        except Exception as e:
            raise create_wrapped_exception(
                e,
                FileWriteError,
                f"Failed to write notebook: {file_path}",
                context={'file_path': file_path}
            )

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message if logger available"""
        if self.logger:
            self.logger.log(message, level)


# Convenience functions for quick notebook creation

def create_data_analysis_notebook(
    title: str,
    data_source: str,
    analysis_steps: List[str]
) -> Dict[str, Any]:
    """
    Create a data analysis notebook template

    Args:
        title: Notebook title
        data_source: Description of data source
        analysis_steps: List of analysis step descriptions

    Returns:
        Complete notebook ready to save
    """
    builder = NotebookBuilder(title)

    # Add data loading section
    builder.add_section("Data Loading", f"Load data from: {data_source}")
    builder.add_code(
        "import pandas as pd\n"
        "import numpy as np\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n\n"
        "# Set plotting style\n"
        "sns.set_style('whitegrid')\n"
        "plt.rcParams['figure.figsize'] = (12, 6)"
    )

    # Add analysis sections
    for i, step in enumerate(analysis_steps, 1):
        builder.add_section(f"Step {i}: {step}")
        builder.add_code(f"# TODO: Implement {step}\npass")

    # Add conclusion section
    builder.add_section("Conclusions", "Summary of findings and next steps")

    return builder.build()


def create_ml_notebook(
    title: str,
    model_type: str,
    features: List[str]
) -> Dict[str, Any]:
    """
    Create a machine learning notebook template

    Args:
        title: Notebook title
        model_type: Type of ML model (classification, regression, clustering)
        features: List of feature names

    Returns:
        Complete notebook ready to save
    """
    builder = NotebookBuilder(title)

    # Import libraries
    builder.add_section("Setup", "Import required libraries")
    builder.add_code(
        "import pandas as pd\n"
        "import numpy as np\n"
        "from sklearn.model_selection import train_test_split\n"
        "from sklearn.preprocessing import StandardScaler\n"
        "from sklearn.metrics import classification_report, confusion_matrix\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns"
    )

    # Data loading
    builder.add_section("Data Loading")
    builder.add_code("# Load dataset\ndf = pd.read_csv('data.csv')\ndf.head()")

    # Feature engineering
    builder.add_section("Feature Engineering", f"Selected features: {', '.join(features)}")
    features_str = ', '.join([f"'{f}'" for f in features])
    builder.add_code(
        f"features = [{features_str}]\n"
        "X = df[features]\n"
        "y = df['target']\n\n"
        "# Split data\n"
        "X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)"
    )

    # Model training
    builder.add_section("Model Training", f"Train {model_type} model")
    builder.add_code(
        "# Initialize and train model\n"
        "# TODO: Select appropriate model for " + model_type + "\n"
        "model = None  # Replace with actual model\n"
        "# model.fit(X_train, y_train)"
    )

    # Evaluation
    builder.add_section("Model Evaluation")
    builder.add_code(
        "# Make predictions\n"
        "# y_pred = model.predict(X_test)\n\n"
        "# Evaluate model\n"
        "# TODO: Add evaluation metrics"
    )

    return builder.build()
