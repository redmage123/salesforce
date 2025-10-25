#!/usr/bin/env python3
"""
Notebook Generation Stage - Creates Jupyter Notebooks as Project Artifacts

Generates Jupyter notebooks for:
- Data analysis workflows
- Machine learning experiments
- API demonstrations
- Documentation with executable examples
- Test result visualization

SOLID Principles:
- Single Responsibility: Notebook generation only
- Open/Closed: Extensible via templates
- Liskov Substitution: Implements StageInterface
- Interface Segregation: Minimal, focused interface
- Dependency Inversion: Depends on abstractions

Design Patterns:
- Strategy Pattern: Different notebook generation strategies
- Template Method: Common notebook structure with customizable content
- Builder Pattern: Uses NotebookBuilder for construction
- Factory Pattern: Creates appropriate notebook type based on context
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from artemis_exceptions import (
    PipelineStageError,
    wrap_exception
)
from jupyter_notebook_handler import (
    NotebookBuilder,
    JupyterNotebookWriter,
    create_data_analysis_notebook,
    create_ml_notebook
)
from pipeline_observer import PipelineObservable, PipelineEvent, EventType
from agent_messenger import AgentMessenger


class NotebookGenerationStage:
    """
    Pipeline stage for generating Jupyter notebooks

    SOLID: Single Responsibility - Notebook generation only
    Pattern: Strategy for different notebook types
    Performance: O(1) notebook type dispatch
    """

    # Performance: Dict dispatch for O(1) notebook type lookup
    NOTEBOOK_GENERATORS = {
        'data_analysis': 'data_analysis',
        'machine_learning': 'machine_learning',
        'ml': 'machine_learning',
        'api_demo': 'api_demo',
        'documentation': 'documentation',
        'test_visualization': 'test_visualization',
        'general': 'general'
    }

    def __init__(
        self,
        output_dir: str = ".",
        logger: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        observable: Optional[PipelineObservable] = None,
        messenger: Optional[AgentMessenger] = None
    ):
        """
        Initialize notebook generation stage

        Args:
            output_dir: Directory to save notebooks
            logger: Optional logger instance
            config: Optional configuration dictionary
            observable: Optional PipelineObservable for event broadcasting
            messenger: Optional AgentMessenger for inter-agent communication
        """
        self.output_dir = Path(output_dir)
        self.logger = logger
        self.config = config or {}
        self.observable = observable
        self.messenger = messenger
        self.writer = JupyterNotebookWriter()

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Performance: Dict dispatch for O(1) generator lookup
        self._generator_dispatch = {
            'data_analysis': self._generate_data_analysis_notebook,
            'machine_learning': self._generate_ml_notebook,
            'api_demo': self._generate_api_demo_notebook,
            'test_visualization': self._generate_test_visualization_notebook,
            'documentation': self._generate_documentation_notebook,
            'general': self._generate_general_notebook
        }

    def execute(
        self,
        card: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute notebook generation stage

        Time Complexity: O(n) where n = number of cells

        Args:
            card: Kanban card with task information
            context: Additional context from previous stages

        Returns:
            Stage results with notebook paths

        Raises:
            PipelineStageError: If notebook generation fails
        """
        try:
            # Observer Pattern: Notify stage start
            if self.observable:
                self.observable.notify(PipelineEvent(
                    event_type=EventType.STAGE_START,
                    stage_name='notebook_generation',
                    data={'card_id': card.get('id', 'unknown')}
                ))

            self.log("📓 Starting Notebook Generation Stage", "INFO")

            # Extract notebook requirements from card
            notebook_type = self._determine_notebook_type(card, context)

            self.log(f"Notebook type: {notebook_type}", "INFO")

            # Generate notebook based on type
            notebook_path = self._generate_notebook(
                card=card,
                notebook_type=notebook_type,
                context=context or {}
            )

            result = {
                'stage': 'notebook_generation',
                'status': 'success',
                'notebook_path': str(notebook_path),
                'notebook_type': notebook_type,
                'message': f'Generated {notebook_type} notebook'
            }

            self.log(f"✅ Notebook generated: {notebook_path}", "SUCCESS")

            # Observer Pattern: Notify stage completion
            if self.observable:
                self.observable.notify(PipelineEvent(
                    event_type=EventType.STAGE_COMPLETE,
                    stage_name='notebook_generation',
                    data=result
                ))

            # Agent Messenger: Send data update with notebook path
            # Other stages can use this notebook for documentation, visualization, etc.
            if self.messenger:
                self.messenger.send_data_update(
                    to_agent="integration-agent",
                    card_id=card.get('id', 'unknown'),
                    data={
                        'notebook_path': str(notebook_path),
                        'notebook_type': notebook_type,
                        'stage': 'notebook_generation'
                    },
                    priority='normal'
                )

            return result

        except Exception as e:
            error_msg = f"Notebook generation failed: {str(e)}"
            self.log(error_msg, "ERROR")

            # Observer Pattern: Notify stage failure
            if self.observable:
                self.observable.notify(PipelineEvent(
                    event_type=EventType.STAGE_FAILED,
                    stage_name='notebook_generation',
                    data={
                        'card_id': card.get('id', 'unknown'),
                        'error': str(e)
                    }
                ))

            # Agent Messenger: Send error notification
            if self.messenger:
                self.messenger.send_error(
                    to_agent="supervisor-agent",
                    card_id=card.get('id', 'unknown'),
                    data={
                        'stage': 'notebook_generation',
                        'error': error_msg,
                        'error_type': type(e).__name__
                    }
                )

            raise wrap_exception(
                e,
                PipelineStageError,
                error_msg,
                context={
                    'stage': 'notebook_generation',
                    'card_id': card.get('id', 'unknown')
                }
            )

    def _determine_notebook_type(
        self,
        card: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Determine notebook type from card and context

        Time Complexity: O(1) - dict lookups

        Args:
            card: Kanban card
            context: Stage context

        Returns:
            Notebook type string
        """
        # Check explicit notebook type in card
        metadata = card.get('metadata', {})
        if 'notebook_type' in metadata:
            nb_type = metadata['notebook_type'].lower()
            if nb_type in self.NOTEBOOK_GENERATORS:
                return self.NOTEBOOK_GENERATORS[nb_type]

        # Infer from card content
        title = card.get('title', '').lower()
        description = card.get('description', '').lower()
        combined_text = f"{title} {description}"

        # Performance: Single pass through text with early exit
        if any(keyword in combined_text for keyword in ['ml', 'machine learning', 'model', 'train', 'predict']):
            return 'machine_learning'

        if any(keyword in combined_text for keyword in ['data analysis', 'analyze data', 'visualization', 'pandas']):
            return 'data_analysis'

        if any(keyword in combined_text for keyword in ['api', 'endpoint', 'demo', 'example']):
            return 'api_demo'

        if any(keyword in combined_text for keyword in ['test', 'testing', 'results']):
            return 'test_visualization'

        # Default to general notebook
        return 'general'

    def _generate_notebook(
        self,
        card: Dict[str, Any],
        notebook_type: str,
        context: Dict[str, Any]
    ) -> Path:
        """
        Generate notebook of specified type

        Pattern: Strategy - delegates to type-specific generator
        Time Complexity: O(n) where n = number of cells
        Performance: O(1) dict dispatch instead of O(n) elif chain

        Args:
            card: Kanban card
            notebook_type: Type of notebook to generate
            context: Stage context

        Returns:
            Path to generated notebook
        """
        # Generate filename from card title
        title = card.get('title', 'notebook')
        # Sanitize filename - single pass O(n)
        safe_title = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in title)
        safe_title = safe_title.replace(' ', '_').lower()
        filename = f"{safe_title}.ipynb"
        output_path = self.output_dir / filename

        # Performance: O(1) dict dispatch instead of O(n) elif chain
        generator_func = self._generator_dispatch.get(
            notebook_type,
            self._generate_general_notebook
        )
        notebook = generator_func(card, context)

        # Write notebook to disk
        self.writer.write_notebook(notebook, str(output_path))

        return output_path

    def _generate_data_analysis_notebook(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate data analysis notebook using template"""
        title = card.get('title', 'Data Analysis')
        description = card.get('description', '')

        # Extract data source from description or context
        data_source = context.get('data_source', 'data.csv')

        # Parse analysis steps from description
        analysis_steps = self._extract_analysis_steps(description)

        return create_data_analysis_notebook(
            title=title,
            data_source=data_source,
            analysis_steps=analysis_steps
        )

    def _generate_ml_notebook(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate machine learning notebook using template"""
        title = card.get('title', 'Machine Learning Experiment')

        # Extract model type and features from card
        model_type = context.get('model_type', 'classification')
        features = context.get('features', ['feature_1', 'feature_2', 'feature_3'])

        return create_ml_notebook(
            title=title,
            model_type=model_type,
            features=features
        )

    def _generate_api_demo_notebook(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate API demonstration notebook"""
        title = card.get('title', 'API Demo')
        description = card.get('description', '')

        builder = NotebookBuilder(title)

        # Title
        builder.add_markdown(f"# {title}\n\n{description}")

        # Setup section
        builder.add_section("Setup", "Install required packages and import libraries")
        builder.add_code(
            "# Install requirements\n"
            "# !pip install requests\n\n"
            "import requests\n"
            "import json\n"
            "from typing import Dict, Any"
        )

        # Configuration
        builder.add_section("Configuration", "Set up API endpoints and credentials")
        builder.add_code(
            "# API Configuration\n"
            "BASE_URL = 'https://api.example.com'\n"
            "API_KEY = 'your-api-key-here'\n\n"
            "headers = {\n"
            "    'Authorization': f'Bearer {API_KEY}',\n"
            "    'Content-Type': 'application/json'\n"
            "}"
        )

        # Example requests
        builder.add_section("Example Requests", "Demonstrate API functionality")
        builder.add_code(
            "# GET request example\n"
            "response = requests.get(f'{BASE_URL}/endpoint', headers=headers)\n"
            "print(f'Status: {response.status_code}')\n"
            "print(json.dumps(response.json(), indent=2))"
        )

        builder.add_code(
            "# POST request example\n"
            "data = {'key': 'value'}\n"
            "response = requests.post(f'{BASE_URL}/endpoint', headers=headers, json=data)\n"
            "print(f'Status: {response.status_code}')\n"
            "print(json.dumps(response.json(), indent=2))"
        )

        return builder.build()

    def _generate_test_visualization_notebook(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate test results visualization notebook"""
        title = card.get('title', 'Test Results Visualization')

        builder = NotebookBuilder(title)

        builder.add_markdown(f"# {title}\n\nVisualize test execution results and coverage metrics")

        # Setup
        builder.add_section("Setup", "Import visualization libraries")
        builder.add_code(
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n"
            "import seaborn as sns\n"
            "import json\n\n"
            "sns.set_style('whitegrid')\n"
            "%matplotlib inline"
        )

        # Load test results
        builder.add_section("Load Test Results", "Read test execution data")
        builder.add_code(
            "# Load test results from JSON\n"
            "with open('test_results.json', 'r') as f:\n"
            "    test_data = json.load(f)\n\n"
            "# Convert to DataFrame\n"
            "df = pd.DataFrame(test_data)\n"
            "df.head()"
        )

        # Visualizations
        builder.add_section("Test Pass/Fail Distribution", "Overall test results")
        builder.add_code(
            "# Pass/Fail pie chart\n"
            "status_counts = df['status'].value_counts()\n"
            "plt.figure(figsize=(8, 6))\n"
            "plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%')\n"
            "plt.title('Test Results Distribution')\n"
            "plt.show()"
        )

        builder.add_section("Test Duration Analysis", "Execution time analysis")
        builder.add_code(
            "# Test duration histogram\n"
            "plt.figure(figsize=(10, 6))\n"
            "plt.hist(df['duration'], bins=30, edgecolor='black')\n"
            "plt.xlabel('Duration (seconds)')\n"
            "plt.ylabel('Number of Tests')\n"
            "plt.title('Test Execution Duration Distribution')\n"
            "plt.show()"
        )

        return builder.build()

    def _generate_documentation_notebook(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate documentation notebook with executable examples"""
        title = card.get('title', 'Documentation')
        description = card.get('description', '')

        builder = NotebookBuilder(title)

        builder.add_markdown(f"# {title}\n\n{description}")

        # Overview section
        builder.add_section("Overview", "Project documentation with executable examples")

        # Installation
        builder.add_section("Installation", "Setup instructions")
        builder.add_code(
            "# Install the package\n"
            "# !pip install package-name\n\n"
            "# Verify installation\n"
            "import package_name\n"
            "print(f'Version: {package_name.__version__}')"
        )

        # Usage examples
        builder.add_section("Basic Usage", "Common use cases")
        builder.add_code(
            "# Import the library\n"
            "from package_name import MainClass\n\n"
            "# Create instance\n"
            "obj = MainClass()\n\n"
            "# Use basic functionality\n"
            "result = obj.method()\n"
            "print(result)"
        )

        # Advanced examples
        builder.add_section("Advanced Features", "Advanced functionality")
        builder.add_code(
            "# Advanced usage example\n"
            "# TODO: Add advanced examples\n"
            "pass"
        )

        return builder.build()

    def _generate_general_notebook(
        self,
        card: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate general purpose notebook"""
        title = card.get('title', 'Notebook')
        description = card.get('description', '')

        builder = NotebookBuilder(title)

        # Title and description
        builder.add_markdown(f"# {title}\n\n{description}")

        # Setup section
        builder.add_section("Setup", "Import required libraries")
        builder.add_code(
            "# Import standard libraries\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n\n"
            "print('Setup complete')"
        )

        # Main content
        builder.add_section("Main Content", "Primary notebook content")
        builder.add_code(
            "# TODO: Add implementation\n"
            "pass"
        )

        # Results
        builder.add_section("Results", "Output and conclusions")
        builder.add_markdown("TODO: Add results and analysis")

        return builder.build()

    def _extract_analysis_steps(self, description: str) -> List[str]:
        """
        Extract analysis steps from description

        Time Complexity: O(n) where n = description length

        Args:
            description: Task description

        Returns:
            List of analysis steps
        """
        # Default steps if none specified
        default_steps = [
            "Load and explore data",
            "Clean and preprocess data",
            "Perform statistical analysis",
            "Create visualizations",
            "Draw conclusions"
        ]

        # Try to extract numbered steps from description
        steps = []
        lines = description.split('\n')

        # Single pass through lines O(n)
        for line in lines:
            line = line.strip()
            # Look for numbered items or bullet points
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove numbering/bullets
                clean_step = line.lstrip('0123456789.-* ')
                if clean_step:
                    steps.append(clean_step)

        return steps if steps else default_steps

    def log(self, message: str, level: str = "INFO"):
        """Log a message"""
        if self.logger:
            self.logger.log(message, level)
        else:
            print(f"[{level}] {message}")


# Convenience function for standalone use
def generate_notebook(
    card: Dict[str, Any],
    output_dir: str = ".",
    notebook_type: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a Jupyter notebook from a card

    Args:
        card: Kanban card with task information
        output_dir: Directory to save notebook
        notebook_type: Optional explicit notebook type
        context: Optional additional context

    Returns:
        Path to generated notebook
    """
    stage = NotebookGenerationStage(output_dir=output_dir)

    # Override notebook type if specified
    if notebook_type:
        if 'metadata' not in card:
            card['metadata'] = {}
        card['metadata']['notebook_type'] = notebook_type

    result = stage.execute(card=card, context=context)
    return result['notebook_path']
