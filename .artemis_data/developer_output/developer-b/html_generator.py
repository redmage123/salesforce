from typing import List

class ChartJSConfig:
    def __init__(self, type_: str, data: dict, options: dict):
        self.type = type_
        self.data = data
        self.options = options

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'data': self.data,
            'options': self.options
        }

class HTMLGenerator:
    def __init__(self, title: str, chart_config: ChartJSConfig):
        self.title = title
        self.chart_config = chart_config

    def generate_html(self) -> str:
        return f"""
        <html>
        <head>
            <title>{self.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                #chart-container {{ width: 80%; margin: auto; }}
            </style>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>{self.title}</h1>
            <div id="chart-container">
                <canvas id="myChart"></canvas>
            </div>
            <script>
                var ctx = document.getElementById('myChart').getContext('2d');
                new Chart(ctx, {self.chart_config.to_dict()});
            </script>
        </body>
        </html>
        """
