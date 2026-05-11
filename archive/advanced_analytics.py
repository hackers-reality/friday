"""
Friday Advanced Analytics - Predictive analytics and insights.
Time series analysis, trend detection, anomaly detection.
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


# ─── Time Series Point ────────────────────────────────────#

class TimeSeriesPoint:
    """A single point in a time series."""
    
    def __init__(self, timestamp: datetime, value: float, metadata: Dict[str, Any] = None):
        self.timestamp = timestamp
        self.value = value
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeSeriesPoint':
        return cls(
            datetime.fromisoformat(data["timestamp"]),
            data["value"],
            data.get("metadata")
        )


# ─── Time Series ────────────────────────────────────#

class TimeSeries:
    """Time series data with analysis capabilities."""
    
    def __init__(self, name: str, metric: str = "value"):
        self.name = name
        self.metric = metric
        self.points: List[TimeSeriesPoint] = []
        self._sort_points()
    
    def add_point(self, point: TimeSeriesPoint):
        """Add a data point."""
        self.points.append(point)
        self._sort_points()
    
    def add_value(self, timestamp: datetime, value: float, metadata: Dict[str, Any] = None):
        """Add a value directly."""
        self.add_point(TimeSeriesPoint(timestamp, value, metadata))
    
    def _sort_points(self):
        """Sort points by timestamp."""
        self.points.sort(key=lambda p: p.timestamp)
    
    def get_values(self) -> List[float]:
        """Get just the values."""
        return [p.value for p in self.points]
    
    def get_timestamps(self) -> List[datetime]:
        """Get just the timestamps."""
        return [p.timestamp for p in self.points]
    
    def moving_average(self, window: int = 5) -> List[float]:
        """Calculate moving average."""
        values = self.get_values()
        if len(values) < window:
            return values
        
        result = []
        for i in range(len(values) - window + 1):
            window_values = values[i:i + window]
            result.append(sum(window_values) / window)
        
        return result
    
    def detect_trend(self) -> str:
        """Detect trend in the time series."""
        if len(self.points) < 3:
            return "insufficient_data"
        
        values = self.get_values()
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        mean_x = sum(x) / n
        mean_y = sum(values) / n
        
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def detect_anomalies(self, threshold: float = 2.0) -> List[Tuple[datetime, float, str]]:
        """
        Detect anomalies using Z-score.
        Returns list of (timestamp, value, reason)
        """
        values = self.get_values()
        if len(values) < 3:
            return []
        
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        
        if stdev == 0:
            return []
        
        anomalies = []
        for point in self.points:
            z_score = abs(point.value - mean) / stdev
            if z_score > threshold:
                reason = "high" if point.value > mean else "low"
                anomalies.append((point.timestamp, point.value, reason))
        
        return anomalies
    
    def forecast(self, steps: int = 5) -> List[float]:
        """Simple linear forecast."""
        if len(self.points) < 2:
            return []
        
        trend = self.detect_trend()
        values = self.get_values()
        
        last_value = values[-1]
        
        if trend == "increasing":
            avg_increase = (values[-1] - values[0]) / len(values)
            return [last_value + avg_increase * (i + 1) for i in range(steps)]
        elif trend == "decreasing":
            avg_decrease = (values[0] - values[-1]) / len(values)
            return [last_value - avg_decrease * (i + 1) for i in range(steps)]
        else:
            return [last_value] * steps
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical summary."""
        values = self.get_values()
        if not values:
            return {"count": 0}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "trend": self.detect_trend(),
        }


# ─── Analytics Engine ────────────────────────────────────#

class AnalyticsEngine:
    """Main analytics engine for Friday."""
    
    def __init__(self, storage_path: str = "friday_memory/analytics"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.series: Dict[str, TimeSeries] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all time series from storage."""
        if not self.storage_path.exists():
            return
        
        for series_file in self.storage_path.glob("*.json"):
            try:
                with open(series_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                series = TimeSeries(data["name"], data.get("metric", "value"))
                for point_data in data.get("points", []):
                    series.add_point(TimeSeriesPoint.from_dict(point_data))
                
                self.series[series.name] = series
            except Exception as e:
                print(f"[Analytics] Error loading {series_file}: {e}")
    
    def save_series(self, name: str):
        """Save a time series to storage."""
        if name not in self.series:
            return
        
        series = self.series[name]
        data = {
            "name": series.name,
            "metric": series.metric,
            "points": [p.to_dict() for p in series.points],
        }
        
        series_path = self.storage_path / f"{name}.json"
        with open(series_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def create_series(self, name: str, metric: str = "value") -> TimeSeries:
        """Create a new time series."""
        if name in self.series:
            return self.series[name]
        
        series = TimeSeries(name, metric)
        self.series[name] = series
        self.save_series(name)
        return series
    
    def add_data_point(self, series_name: str, value: float, timestamp: datetime = None, metadata: Dict[str, Any] = None):
        """Add a data point to a series."""
        if series_name not in self.series:
            self.create_series(series_name)
        
        series = self.series[series_name]
        series.add_value(timestamp or datetime.now(), value, metadata)
        self.save_series(series_name)
    
    def analyze_series(self, name: str) -> Dict[str, Any]:
        """Full analysis of a time series."""
        if name not in self.series:
            return {"error": f"Series not found: {name}"}
        
        series = self.series[name]
        stats = series.get_statistics()
        anomalies = series.detect_anomalies()
        forecast = series.forecast(5)
        
        return {
            "name": name,
            "statistics": stats,
            "trend": series.detect_trend(),
            "anomalies": [
                {"timestamp": a[0].isoformat(), "value": a[1], "reason": a[2]}
                for a in anomalies
            ],
            "forecast": forecast,
            "data_points": len(series.points),
        }
    
    def correlate_series(self, name1: str, name2: str) -> Dict[str, Any]:
        """Calculate correlation between two time series."""
        if name1 not in self.series or name2 not in self.series:
            return {"error": "One or both series not found"}
        
        series1 = self.series[name1]
        series2 = self.series[name2]
        
        # Simple correlation (align by min length)
        values1 = series1.get_values()
        values2 = series2.get_values()
        
        min_len = min(len(values1), len(values2))
        if min_len < 2:
            return {"error": "Insufficient data for correlation"}
        
        values1 = values1[:min_len]
        values2 = values2[:min_len]
        
        # Pearson correlation
        mean1 = statistics.mean(values1)
        mean2 = statistics.mean(values2)
        
        numerator = sum((values1[i] - mean1) * (values2[i] - mean2) for i in range(min_len))
        denom1 = sum((values1[i] - mean1) ** 2 for i in range(min_len)) ** 0.5
        denom2 = sum((values2[i] - mean2) ** 2 for i in range(min_len)) ** 0.5
        
        if denom1 == 0 or denom2 == 0:
            correlation = 0
        else:
            correlation = numerator / (denom1 * denom2)
        
        return {
            "series1": name1,
            "series2": name2,
            "correlation": correlation,
            "strength": "strong" if abs(correlation) > 0.7 else "moderate" if abs(correlation) > 0.3 else "weak",
            "direction": "positive" if correlation > 0 else "negative" if correlation < 0 else "none",
        }


# ─── Singleton Engine ────────────────────────────────────#

_engine: Optional[AnalyticsEngine] = None

def get_analytics_engine() -> AnalyticsEngine:
    """Get or create the global analytics engine."""
    global _engine
    if _engine is None:
        _engine = AnalyticsEngine()
    return _engine


# ─── Tool Function for Friday ────────────────────────────────────#

def analytics_tool(
    action: str = "list",
    series_name: str = None,
    value: float = None,
    metric: str = None,
) -> str:
    """
    Friday tool for advanced analytics.
    Actions: list, create, add, analyze, forecast, correlate, stats
    """
    engine = get_analytics_engine()
    
    if action == "list":
        if not engine.series:
            return "No time series created."
        lines = ["### TIME SERIES", ""]
        for name, series in engine.series.items():
            lines.append(f"**{name}** ({series.metric}) - {len(series.points)} points")
        return "\n".join(lines)
    
    if action == "create":
        if not series_name:
            return "[FAIL] Series name required."
        engine.create_series(series_name, metric or "value")
        return f"[OK] Created series: {series_name}"
    
    if action == "add":
        if not series_name or value is None:
            return "[FAIL] Series name and value required."
        engine.add_data_point(series_name, value)
        return f"[OK] Added value {value} to {series_name}"
    
    if action == "analyze":
        if not series_name:
            return "[FAIL] Series name required."
        
        result = engine.analyze_series(series_name)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        lines = [f"### ANALYSIS: {series_name}", ""]
        lines.append(f"**Data Points**: {result['data_points']}")
        lines.append("")
        lines.append("**Statistics**:")
        for key, val in result["statistics"].items():
            lines.append(f"  - {key}: {val}")
        lines.append("")
        lines.append(f"**Trend**: {result['trend'].upper()}")
        lines.append("")
        lines.append(f"**Anomalies**: {len(result['anomalies'])}")
        if result["anomalies"]:
            for anomaly in result["anomalies"][:5]:
                lines.append(f"  - {anomaly['timestamp']}: {anomaly['value']} ({anomaly['reason']})")
        lines.append("")
        lines.append(f"**Forecast (next 5)**: {result['forecast']}")
        
        return "\n".join(lines)
    
    if action == "forecast":
        if not series_name:
            return "[FAIL] Series name required."
        
        result = engine.analyze_series(series_name)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        return f"### FORECAST: {series_name}\n\nNext 5 values: {result['forecast']}"
    
    if action == "correlate":
        if not series_name or not metric:
            return "[FAIL] Provide two series names: series_name and metric (as second series)."
        
        result = engine.correlate_series(series_name, metric)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        return f"""### CORRELATION ANALYSIS
**Series 1**: {result['series1']}
**Series 2**: {result['series2']}
**Correlation**: {result['correlation']:.3f}
**Strength**: {result['strength'].upper()}
**Direction**: {result['direction'].upper()}"""
    
    if action == "stats":
        if not series_name:
            return "[FAIL] Series name required."
        
        result = engine.analyze_series(series_name)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        
        stats = result["statistics"]
        lines = [f"### STATISTICS: {series_name}", ""]
        for key, val in stats.items():
            lines.append(f"**{key.title()}**: {val}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Advanced Analytics...\n")
    
    engine = get_analytics_engine()
    
    # Create a test series
    print("--- Creating Series ---")
    print(analytics_tool("create", series_name="cpu_usage", metric="percent"))
    
    # Add some data points
    print("\n--- Adding Data ---")
    import random
    base_time = datetime.now()
    for i in range(10):
        value = 50 + random.uniform(-10, 20)
        engine.add_data_point("cpu_usage", value, base_time + timedelta(minutes=i))
    
    # Analyze
    print("\n--- Analysis ---")
    print(analytics_tool("analyze", series_name="cpu_usage"))
