# Metrics Extraction

This example demonstrates how to extract and analyze metrics from text data.

## Basic Metrics Extraction

```python
from structx import Extractor
import pandas as pd
import matplotlib.pyplot as plt

# Initialize extractor
extractor = Extractor.from_litellm(
    model="gpt-4o-mini",
    api_key="your-api-key"
)

# Sample data
data = [
    {"report": "Server performance test showed 95% CPU utilization, 87% memory usage, and response time of 230ms."},
    {"report": "Database query optimization reduced average query time from 450ms to 120ms and CPU load from 78% to 45%."},
    {"report": "Network throughput measured at 875 Mbps with latency of 15ms and packet loss of 0.02%."},
    {"report": "API performance test showed 99.8% uptime, average response time of 180ms, and error rate of 0.5%."},
    {"report": "Storage system benchmarks: read speed 520 MB/s, write speed 480 MB/s, IOPS 12,000."}
]

df = pd.DataFrame(data)

# Extract metrics
result = extractor.extract(
    data=df,
    query="""
    extract performance metrics including:
    - metric name
    - value
    - unit
    - component
    """,
    return_df=True
)

print(f"Extracted {len(result.data)} metrics")
print(result.data.head())

# Basic visualization
plt.figure(figsize=(10, 6))
for component in result.data['component'].unique():
    component_data = result.data[result.data['component'] == component]
    plt.scatter(component_data['metric_name'], component_data['value'], label=component, s=100)

plt.xlabel('Metric')
plt.ylabel('Value')
plt.title('Performance Metrics by Component')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.show()
```

## Comparative Metrics Analysis

```python
# Sample data with before/after metrics
data = [
    {"report": "Server optimization reduced CPU utilization from 95% to 65%, memory usage from 87% to 60%, and improved response time from 230ms to 120ms."},
    {"report": "Database query optimization reduced average query time from 450ms to 120ms and CPU load from 78% to 45%."},
    {"report": "Network upgrade increased throughput from 875 Mbps to 1.2 Gbps and reduced latency from 15ms to 8ms."},
    {"report": "API optimization improved uptime from 99.8% to 99.95% and reduced error rate from 0.5% to 0.1%."}
]

df = pd.DataFrame(data)

# Extract before/after metrics
result = extractor.extract(
    data=df,
    query="""
    extract comparative metrics including:
    - metric name
    - before value
    - after value
    - unit
    - improvement percentage
    - component
    """,
    return_df=True
)

print(f"Extracted {len(result.data)} comparative metrics")
print(result.data.head())

# Calculate improvement where not provided
if 'improvement_percentage' not in result.data.columns or result.data['improvement_percentage'].isna().any():
    # Convert to numeric, handling percentage signs
    for col in ['before_value', 'after_value']:
        result.data[col] = pd.to_numeric(result.data[col].astype(str).str.replace('%', ''), errors='coerce')

    # Calculate improvement percentage
    def calc_improvement(row):
        if row['before_value'] == 0:
            return 0
        if 'latency' in row['metric_name'].lower() or 'time' in row['metric_name'].lower():
            # For metrics where lower is better
            return ((row['before_value'] - row['after_value']) / row['before_value']) * 100
        else:
            # For metrics where higher is better
            return ((row['after_value'] - row['before_value']) / row['before_value']) * 100

    result.data['improvement_percentage'] = result.data.apply(calc_improvement, axis=1)

# Visualization
plt.figure(figsize=(12, 8))
metrics = result.data['metric_name'].unique()
components = result.data['component'].unique()

x = np.arange(len(metrics))
width = 0.35 / len(components)
offsets = np.linspace(-0.35/2, 0.35/2, len(components))

for i, component in enumerate(components):
    component_data = result.data[result.data['component'] == component]
    improvements = []

    for metric in metrics:
        metric_data = component_data[component_data['metric_name'] == metric]
        if not metric_data.empty:
            improvements.append(metric_data['improvement_percentage'].values[0])
        else:
            improvements.append(0)

    plt.bar(x + offsets[i], improvements, width, label=component)

plt.xlabel('Metric')
plt.ylabel('Improvement (%)')
plt.title('Performance Improvement by Metric and Component')
plt.xticks(x, metrics, rotation=45)
plt.legend()
plt.tight_layout()
plt.show()
```

## Time Series Metrics

```python
# Sample data with timestamps
data = [
    {"log": "2024-01-01 08:00:00 - Server CPU: 45%, Memory: 60%, Response time: 120ms"},
    {"log": "2024-01-01 12:00:00 - Server CPU: 78%, Memory: 75%, Response time: 180ms"},
    {"log": "2024-01-01 16:00:00 - Server CPU: 92%, Memory: 85%, Response time: 250ms"},
    {"log": "2024-01-01 20:00:00 - Server CPU: 65%, Memory: 70%, Response time: 150ms"},
    {"log": "2024-01-02 08:00:00 - Server CPU: 48%, Memory: 62%, Response time: 125ms"}
]

df = pd.DataFrame(data)

# Extract time series metrics
result = extractor.extract(
    data=df,
    query="""
    extract time series metrics including:
    - timestamp
    - cpu_percentage
    - memory_percentage
    - response_time_ms
    """,
    return_df=True
)

print(f"Extracted {len(result.data)} time series data points")
print(result.data.head())

# Convert timestamp to datetime
result.data['timestamp'] = pd.to_datetime(result.data['timestamp'])

# Plot time series
plt.figure(figsize=(12, 8))

# Create subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# CPU and Memory
ax1.plot(result.data['timestamp'], result.data['cpu_percentage'], 'b-', label='CPU')
ax1.plot(result.data['timestamp'], result.data['memory_percentage'], 'g-', label='Memory')
ax1.set_ylabel('Utilization (%)')
ax1.set_title('Server Performance Metrics Over Time')
ax1.legend()
ax1.grid(True)

# Response Time
ax2.plot(result.data['timestamp'], result.data['response_time_ms'], 'r-', label='Response Time')
ax2.set_xlabel('Time')
ax2.set_ylabel('Response Time (ms)')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.show()

# Calculate statistics
stats = result.data.describe()
print("\nStatistics:")
print(stats)

# Calculate correlations
corr = result.data[['cpu_percentage', 'memory_percentage', 'response_time_ms']].corr()
print("\nCorrelations:")
print(corr)
```

## Custom Metrics Model

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class PerformanceMetric(BaseModel):
    name: str = Field(description="Name of the metric")
    value: float = Field(description="Value of the metric")
    unit: str = Field(description="Unit of measurement")
    timestamp: Optional[datetime] = Field(default=None, description="When the metric was recorded")
    component: str = Field(description="System component being measured")
    threshold: Optional[float] = Field(default=None, description="Alert threshold for this metric")
    status: Optional[str] = Field(default=None, description="Status based on threshold (OK, Warning, Critical)")

# Extract with custom model
result = extractor.extract(
    data=df,
    query="""
    extract detailed performance metrics with status based on these thresholds:
    - CPU: Warning > 70%, Critical > 90%
    - Memory: Warning > 80%, Critical > 95%
    - Response time: Warning > 200ms, Critical > 500ms
    """,
    model=PerformanceMetric
)

print(f"Extracted {result.success_count} detailed metrics")
for metric in result.data:
    print(f"{metric.component} {metric.name}: {metric.value}{metric.unit} - {metric.status}")
```

## Metrics Dashboard

```python
import dash
from dash import dcc, html
import plotly.express as px
import plotly.graph_objects as go

# Extract metrics
result = extractor.extract(
    data=df,
    query="""
    extract time series metrics including:
    - timestamp
    - cpu_percentage
    - memory_percentage
    - response_time_ms
    - throughput_mbps
    - error_rate_percentage
    """,
    return_df=True
)

# Convert timestamp to datetime
result.data['timestamp'] = pd.to_datetime(result.data['timestamp'])

# Create a Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("System Performance Dashboard"),

    html.Div([
        html.H3("CPU and Memory Utilization"),
        dcc.Graph(
            figure=px.line(
                result.data,
                x="timestamp",
                y=["cpu_percentage", "memory_percentage"],
                labels={"value": "Percentage", "variable": "Metric"}
            )
        )
    ]),

    html.Div([
        html.H3("Response Time"),
        dcc.Graph(
            figure=px.line(
                result.data,
                x="timestamp",
                y="response_time_ms",
                labels={"response_time_ms": "Response Time (ms)"}
            )
        )
    ]),

    html.Div([
        html.H3("Throughput"),
        dcc.Graph(
            figure=px.line(
                result.data,
                x="timestamp",
                y="throughput_mbps",
                labels={"throughput_mbps": "Throughput (Mbps)"}
            )
        )
    ]),

    html.Div([
        html.H3("Error Rate"),
        dcc.Graph(
            figure=px.line(
                result.data,
                x="timestamp",
                y="error_rate_percentage",
                labels={"error_rate_percentage": "Error Rate (%)"}
            )
        )
    ])
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
```
