"""
Friday Analytics - Data analysis and visualization.
Analytics, metrics, reporting, data visualization.
"""
from __future__ import annotations

import os
import sys
import json
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import csv
import io


# ─── Data Analysis ────────────────────────────#

class DataAnalyzer:
    """Analyze data sets."""
    
    def __init__(self):
        self.pandas_available = self._check_pandas()
        
    def _check_pandas(self) -> bool:
        try:
            import pandas as pd
            self.pd = pd
            return True
        except ImportError:
            return False
    
    def analyze_csv(self, file_path: str) -> Dict[str, Any]:
        """Analyze CSV file."""
        if not self.pandas_available:
            return {"success": False, "error": "pandas not available. Install: pip install pandas"}
        
        try:
            df = self.pd.read_csv(file_path)
            
            return {
                "success": True,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "summary": df.describe().to_dict() if len(df) > 0 else {},
                "missing_values": df.isnull().sum().to_dict(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def analyze_json(self, data: Any) -> Dict[str, Any]:
        """Analyze JSON data."""
        if not self.pandas_available:
            # Simple analysis without pandas
            if isinstance(data, list):
                return {
                    "success": True,
                    "type": "list",
                    "count": len(data),
                    "sample": data[:3] if len(data) > 0 else [],
                }
            elif isinstance(data, dict):

                return {
                    "success": True,
                    "type": "dict",
                    "keys": list(data.keys())[:10],
                    "count": len(data),
                }
            else:
                return {"success": True, "type": type(data).__name__, "value": str(data)[:100]}
        
        try:
            df = self.pd.json_normalize(data if isinstance(data, list) else [data])
            
            return {
                "success": True,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_statistics(self, numbers: List[float]) -> Dict[str, Any]:
        """Calculate statistics for a list of numbers."""
        if not numbers:
            return {"success": False, "error": "No data provided."}
        
        try:
            return {
                "success": True,
                "count": len(numbers),
                "mean": statistics.mean(numbers),
                "median": statistics.median(numbers),
                "mode": statistics.mode(numbers) if len(set(numbers)) < len(numbers) else None,
                "stdev": statistics.stdev(numbers) if len(numbers) > 1 else 0,
                "min": min(numbers),
                "max": max(numbers),
                "sum": sum(numbers),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Metrics ────────────────────────────#

class MetricsCollector:
    """Collect and analyze metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.timestamps: Dict[str, List[datetime]] = {}
        
    def add_metric(self, name: str, value: float):
        """Add a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
            self.timestamps[name] = []
        
        self.metrics[name].append(value)
        self.timestamps[name].append(datetime.now())
        
        # Keep only last 1000 values
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
            self.timestamps[name] = self.timestamps[name][-1000:]
    
    def get_metric_summary(self, name: str) -> Dict[str, Any]:
        """Get summary of a metric."""
        if name not in self.metrics or not self.metrics[name]:
            return {"success": False, "error": "Metric not found or empty."}
        
        values = self.metrics[name]
        
        return {
            "success": True,
            "name": name,
            "count": len(values),
            "current": values[-1],
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "last_updated": self.timestamps[name][-1].isoformat() if self.timestamps[name] else None,
        }
    
    def get_all_summaries(self) -> Dict[str, Any]:
        """Get summaries of all metrics."""
        summaries = {}
        for name in self.metrics.keys():
            summary = self.get_metric_summary(name)
            if summary["success"]:
                summaries[name] = {k: v for k, v in summary.items() if k != "success"}
        
        return {
            "success": True,
            "metrics": summaries,
            "metric_count": len(summaries),
        }
    
    def clear_metrics(self, name: str = None):
        """Clear metrics."""
        if name:
            if name in self.metrics:
                del self.metrics[name]
                del self.timestamps[name]
        else:
            self.metrics.clear()
            self.timestamps.clear()


# ─── Report Generation ────────────────────────────#

class ReportGenerator:
    """Generate reports from data."""
    
    def __init__(self):
        self.templates: Dict[str, str] = {}
        
    def add_template(self, name: str, template: str):
        """Add a report template."""
        self.templates[name] = template
        
    def generate_text_report(self, data: Dict[str, Any], title: str = "Report") -> str:
        """Generate a text report."""
        lines = [
            "=" * 60,
            title.center(60),
            "=" * 60,
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            elif isinstance(value, list):
                lines.append(f"{key} ({len(value)} items):")
                for i, item in enumerate(value[:10]):  # Limit to 10 items
                    lines.append(f"  {i+1}. {item}")
                if len(value) > 10:
                    lines.append(f"  ... and {len(value) - 10} more")
            else:
                lines.append(f"{key}: {value}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_csv_report(self, data: List[Dict], output_path: str = None) -> Dict[str, Any]:
        """Generate a CSV report."""
        if not data:
            return {"success": False, "error": "No data provided."}
        
        try:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
            csv_content = output.getvalue()
            
            if output_path:
                with open(output_path, "w", newline="") as f:
                    f.write(csv_content)
                return {"success": True, "path": output_path}
            
            return {"success": True, "content": csv_content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_json_report(self, data: Any, output_path: str = None) -> Dict[str, Any]:
        """Generate a JSON report."""
        try:
            json_content = json.dumps(data, indent=2)
            
            if output_path:
                with open(output_path, "w") as f:
                    f.write(json_content)
                return {"success": True, "path": output_path}
            
            return {"success": True, "content": json_content}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Visualization (Simplified) ────────────────────────────#

class Visualizer:
    """Data visualization (simplified)."""
    
    def __init__(self):
        self.matplotlib_available = self._check_matplotlib()
        
    def _check_matplotlib(self) -> bool:
        try:
            import matplotlib
            self.matplotlib = matplotlib
            return True
        except ImportError:
            return False
    
    def create_line_chart(self, x_data: List[Any], y_data: List[float], title: str = "Line Chart", output: str = "chart.png") -> Dict[str, Any]:
        """Create a line chart."""
        if not self.matplotlib_available:
            return {"success": False, "error": "matplotlib not available. Install: pip install matplotlib"}
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            plt.plot(x_data, y_data, marker='o')
            plt.title(title)
            plt.xlabel("X")
            plt.ylabel("Y")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output)
            plt.close()
            
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_bar_chart(self, categories: List[str], values: List[float], title: str = "Bar Chart", output: str = "bar_chart.png") -> Dict[str, Any]:
        """Create a bar chart."""
        if not self.matplotlib_available:
            return {"success": False, "error": "matplotlib not available."}
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            plt.bar(categories, values, color='skyblue')
            plt.title(title)
            plt.xlabel("Category")
            plt.ylabel("Value")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(output)
            plt.close()
            
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_pie_chart(self, labels: List[str], values: List[float], title: str = "Pie Chart", output: str = "pie_chart.png") -> Dict[str, Any]:
        """Create a pie chart."""
        if not self.matplotlib_available:
            return {"success": False, "error": "matplotlib not available."}
        
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(8, 8))
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
            plt.title(title)
            plt.axis('equal')
            plt.tight_layout()
            plt.savefig(output)
            plt.close()
            
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Analytics Tool for Friday ────────────────────────────#

def analytics_tool(
    action: str = "status",
    data: Any = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for analytics operations.
    Actions: status, analyze_csv, analyze_json, statistics,
            metrics_add, metrics_summary, report_text, report_csv,
            viz_line, viz_bar, viz_pie
    """
    params = params or {}
    
    if action == "status":
        analyzer = DataAnalyzer()
        visualizer = Visualizer()
        lines = ["### ANALYTICS STATUS", ""]
        lines.append(f"**pandas Available**: {'✅' if analyzer.pandas_available else '❌'}")
        lines.append(f"**matplotlib Available**: {'✅' if visualizer.matplotlib_available else '❌'}")
        lines.append("")
        lines.append("**Available Features**:")
        lines.append("  - CSV/JSON analysis")
        lines.append("  - Statistical calculations")
        lines.append("  - Metrics collection")
        lines.append("  - Report generation (text, CSV, JSON)")
        lines.append("  - Visualization (line, bar, pie charts)")
        return "\n".join(lines)
    
    if action == "analyze_csv":
        if not data:
            return "❌ File path required."
        analyzer = DataAnalyzer()
        result = analyzer.analyze_csv(data)
        if result["success"]:
            lines = [f"### CSV ANALYSIS: {data}", ""]
            lines.append(f"**Rows**: {result['rows']}")
            lines.append(f"**Columns**: {', '.join(result['columns'])}")
            lines.append("")
            lines.append("**Summary**:")
            for col, stats in result.get("summary", {}).items():
                lines.append(f"  {col}: mean={stats.get('mean', 0):.2f}, min={stats.get('min', 0)}, max={stats.get('max', 0)}")
            return "\n".join(lines)
        else:
            return f"❌ Analysis error: {result.get('error', 'Unknown')}"
    
    if action == "analyze_json":
        if not data:
            return "❌ Data required."
        analyzer = DataAnalyzer()
        try:
            json_data = json.loads(data) if isinstance(data, str) else data
        except:
            return "❌ Invalid JSON data."
        
        result = analyzer.analyze_json(json_data)
        if result["success"]:
            return f"### JSON ANALYSIS\n\n{json.dumps(result, indent=2)}"
        else:
            return f"❌ Analysis error: {result.get('error', 'Unknown')}"
    
    if action == "statistics":
        if not data:
            return "❌ Numbers required (as JSON list)."
        try:
            numbers = json.loads(data) if isinstance(data, str) else data
        except:
            return "❌ Invalid data format. Provide a JSON list of numbers."
        
        analyzer = DataAnalyzer()
        result = analyzer.calculate_statistics(numbers)
        if result["success"]:
            lines = ["### STATISTICS", ""]
            for key, value in result.items():
                if key != "success":
                    lines.append(f"**{key.capitalize()}**: {value}")
            return "\n".join(lines)
        else:
            return f"❌ Statistics error: {result.get('error', 'Unknown')}"
    
    if action == "metrics_add":
        if not data or "value" not in params:
            return "❌ Metric name and value required."
        collector = MetricsCollector()
        collector.add_metric(data, float(params["value"]))
        return f"✅ Added metric: {data} = {params['value']}"
    
    if action == "metrics_summary":
        collector = MetricsCollector()
        if data:
            result = collector.get_metric_summary(data)
        else:
            result = collector.get_all_summaries()
        
        if result.get("success"):
            return f"### METRICS SUMMARY\n\n{json.dumps(result, indent=2)}"
        else:
            return f"❌ Metrics error: {result.get('error', 'Unknown')}"
    
    if action == "report_text":
        if not data:
            return "❌ Data required."
        try:
            report_data = json.loads(data) if isinstance(data, str) else data
        except:
            return "❌ Invalid JSON data."
        
        generator = ReportGenerator()
        title = params.get("title", "Friday Report")
        report = generator.generate_text_report(report_data, title)
        return f"### TEXT REPORT\n\n```\n{report}\n```"
    
    if action == "report_csv":
        if not data:
            return "❌ Data required (JSON list of dicts)."
        try:
            report_data = json.loads(data) if isinstance(data, str) else data
        except:
            return "❌ Invalid JSON data."
        
        generator = ReportGenerator()
        output_path = params.get("output")
        result = generator.generate_csv_report(report_data, output_path)
        if result["success"]:
            return f"### CSV REPORT\n\n✅ Generated: {result.get('path', 'output')}"
        else:
            return f"❌ Report error: {result.get('error', 'Unknown')}"
    
    if action == "viz_line":
        if not data or "x" not in params or "y" not in params:
            return "❌ Data and x/y values required."
        visualizer = Visualizer()
        title = params.get("title", "Line Chart")
        output = params.get("output", "line_chart.png")
        result = visualizer.create_line_chart(params["x"], params["y"], title, output)
        if result["success"]:
            return f"### LINE CHART\n\n✅ Saved to {result['output']}"
        else:
            return f"❌ Visualization error: {result.get('error', 'Unknown')}"
    
    if action == "viz_bar":
        if not data or "values" not in params:
            return "❌ Data and values required."
        visualizer = Visualizer()
        categories = params.get("categories", [str(i) for i in range(len(params["values"]))])
        title = params.get("title", "Bar Chart")
        output = params.get("output", "bar_chart.png")
        result = visualizer.create_bar_chart(categories, params["values"], title, output)
        if result["success"]:
            return f"### BAR CHART\n\n✅ Saved to {result['output']}"
        else:
            return f"❌ Visualization error: {result.get('error', 'Unknown')}"
    
    if action == "viz_pie":
        if not data or "values" not in params:
            return "❌ Data and values required."
        visualizer = Visualizer()
        labels = params.get("labels", [str(i) for i in range(len(params["values"]))])
        title = params.get("title", "Pie Chart")
        output = params.get("output", "pie_chart.png")
        result = visualizer.create_pie_chart(labels, params["values"], title, output)
        if result["success"]:
            return f"### PIE CHART\n\n✅ Saved to {result['output']}"
        else:
            return f"❌ Visualization error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Analytics...\n")
    
    # Test status
    print("--- Analytics Status ---")
    print(analytics_tool("status"))
    
    # Test statistics
    print("\n--- Statistics ---")
    print(analytics_tool("statistics", data=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
