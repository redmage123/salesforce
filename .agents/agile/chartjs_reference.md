# Chart.js Reference for Interactive Visualizations

## What is Chart.js?

Chart.js is a simple yet flexible JavaScript charting library for designers and developers. It provides 8 chart types with animations, responsive design, and interactivity.

**Official Website**: https://www.chartjs.org/
**CDN**: `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>`

## Why Use Chart.js?

- **Simple API**: Easy to learn and use
- **Responsive**: Adapts to all screen sizes
- **Animated**: Built-in smooth animations
- **Interactive**: Hover tooltips, click events
- **Customizable**: Extensive configuration options
- **Lightweight**: Small file size (~200KB)

## Chart Types

1. **Line Chart**: Trends over time
2. **Bar Chart**: Comparisons between categories
3. **Pie/Doughnut Chart**: Proportions and percentages
4. **Radar Chart**: Multivariate data
5. **Polar Area Chart**: Like pie but uses angles
6. **Bubble Chart**: 3-dimensional data
7. **Scatter Chart**: Correlation between variables
8. **Mixed Charts**: Combine multiple types

## Basic Usage Pattern

### 1. Include Chart.js
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### 2. Create Canvas Element
```html
<canvas id="myChart" width="400" height="400"></canvas>
```

### 3. Initialize Chart
```javascript
const ctx = document.getElementById('myChart').getContext('2d');
const myChart = new Chart(ctx, {
    type: 'bar',  // Chart type
    data: {       // Data configuration
        labels: ['Red', 'Blue', 'Yellow'],
        datasets: [{
            label: 'My Dataset',
            data: [12, 19, 3],
            backgroundColor: ['red', 'blue', 'yellow']
        }]
    },
    options: {    // Chart options
        responsive: true,
        maintainAspectRatio: false
    }
});
```

## Common Chart Examples

### Line Chart (Time Series)
```javascript
new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
        datasets: [{
            label: 'Revenue',
            data: [12000, 19000, 15000, 25000, 22000],
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.4  // Smooth curves
        }]
    },
    options: {
        responsive: true,
        plugins: {
            title: {
                display: true,
                text: 'Monthly Revenue'
            }
        }
    }
});
```

### Bar Chart (Comparisons)
```javascript
new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['Q1', 'Q2', 'Q3', 'Q4'],
        datasets: [{
            label: 'Sales',
            data: [65, 59, 80, 81],
            backgroundColor: [
                'rgba(255, 99, 132, 0.8)',
                'rgba(54, 162, 235, 0.8)',
                'rgba(255, 206, 86, 0.8)',
                'rgba(75, 192, 192, 0.8)'
            ]
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});
```

### Doughnut Chart (Proportions)
```javascript
new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['Direct', 'Referral', 'Social', 'Organic'],
        datasets: [{
            data: [300, 50, 100, 80],
            backgroundColor: [
                '#FF6384',
                '#36A2EB',
                '#FFCE56',
                '#4BC0C0'
            ]
        }]
    },
    options: {
        plugins: {
            legend: {
                position: 'bottom'
            }
        }
    }
});
```

### Multi-Dataset Chart
```javascript
new Chart(ctx, {
    type: 'line',
    data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
        datasets: [
            {
                label: 'Revenue',
                data: [12, 19, 15, 25, 22],
                borderColor: 'rgb(75, 192, 192)',
                yAxisID: 'y'
            },
            {
                label: 'Costs',
                data: [8, 12, 10, 15, 14],
                borderColor: 'rgb(255, 99, 132)',
                yAxisID: 'y'
            }
        ]
    },
    options: {
        scales: {
            y: {
                type: 'linear',
                position: 'left'
            }
        }
    }
});
```

## Best Practices for Artemis Demos

### 1. Professional Color Schemes
```javascript
// Use consistent, professional colors
const colors = {
    primary: '#2563eb',    // Blue
    success: '#10b981',    // Green
    warning: '#f59e0b',    // Orange
    danger: '#ef4444',     // Red
    info: '#06b6d4'        // Cyan
};
```

### 2. Responsive Configuration
```javascript
options: {
    responsive: true,
    maintainAspectRatio: false,  // Allow custom aspect ratio
    aspectRatio: 2  // Width:Height ratio
}
```

### 3. Interactive Tooltips
```javascript
options: {
    plugins: {
        tooltip: {
            callbacks: {
                label: function(context) {
                    return context.dataset.label + ': $' +
                           context.parsed.y.toLocaleString();
                }
            }
        }
    }
}
```

### 4. Animations
```javascript
options: {
    animation: {
        duration: 1000,
        easing: 'easeInOutQuart'
    }
}
```

### 5. Legend Configuration
```javascript
options: {
    plugins: {
        legend: {
            display: true,
            position: 'bottom',
            labels: {
                boxWidth: 12,
                padding: 10,
                font: {
                    size: 12
                }
            }
        }
    }
}
```

## Common Patterns for Business Dashboards

### 1. Performance Metrics Dashboard
```javascript
// Multiple KPI cards with mini charts
// Use sparkline-style charts (no axes, minimal styling)
```

### 2. Trend Analysis
```javascript
// Line charts with annotations
// Multiple time series on same axes
```

### 3. Comparison Charts
```javascript
// Grouped or stacked bar charts
// Side-by-side comparisons
```

### 4. Distribution Analysis
```javascript
// Pie/Doughnut for proportions
// Histogram for distributions
```

## Integration with HTML Demos

### Full Example Structure
```html
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Demo</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .chart-container {
            position: relative;
            height: 400px;
            margin: 20px;
        }
    </style>
</head>
<body>
    <div class="chart-container">
        <canvas id="myChart"></canvas>
    </div>

    <script>
        const ctx = document.getElementById('myChart').getContext('2d');
        new Chart(ctx, {
            // Configuration here
        });
    </script>
</body>
</html>
```

## Chart.js + Plotly Comparison

| Feature | Chart.js | Plotly |
|---------|----------|--------|
| **Use Case** | HTML slides, web demos | Jupyter notebooks, Python |
| **Interactivity** | Basic (hover, click) | Advanced (zoom, pan, select) |
| **File Size** | ~200KB | ~3MB |
| **Setup** | Single CDN link | Python package |
| **Best For** | Presentation slides | Data analysis notebooks |

## When to Use Each

**Use Chart.js when**:
- Creating HTML presentation slides
- Need lightweight, fast-loading charts
- Simple interactivity is sufficient
- Web-only deployment

**Use Plotly when**:
- Working in Jupyter notebooks
- Need advanced interactivity
- Complex multi-dimensional data
- Python-based workflows

## Resources

- Documentation: https://www.chartjs.org/docs/
- Examples: https://www.chartjs.org/samples/
- GitHub: https://github.com/chartjs/Chart.js
- CDN: https://cdn.jsdelivr.net/npm/chart.js
