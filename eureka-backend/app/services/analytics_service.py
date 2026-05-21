from typing import Dict, List, Any
import logging
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Provides advanced analytics on experiments"""
    
    def __init__(self):
        self.experiments_data: Dict[str, List[Dict]] = {}
    
    async def compare_experiments(
        self,
        exp_ids: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple experiments"""
        comparison = {
            "experiments": exp_ids,
            "metrics": {},
            "statistics": {},
            "insights": []
        }
        
        for exp_id in exp_ids:
            if exp_id in self.experiments_data:
                data = self.experiments_data[exp_id]
                metrics = self._calculate_metrics(data)
                comparison["metrics"][exp_id] = metrics
        
        # Statistical comparison
        valid_datasets = [self.experiments_data.get(exp_id, []) for exp_id in exp_ids if exp_id in self.experiments_data]
        if len(valid_datasets) > 1:
            comparison["statistics"] = self._statistical_comparison(valid_datasets)
        
        # Generate insights
        comparison["insights"] = self._generate_insights(comparison)
        
        return comparison
    
    def _calculate_metrics(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics from experiment data"""
        if not data:
            return {}
        
        values = [d.get("value", 0.0) for d in data]
        if not values:
            return {}
            
        mean_val = float(np.mean(values))
        median_val = float(np.median(values))
        std_val = float(np.std(values))
        min_val = float(np.min(values))
        max_val = float(np.max(values))
        
        metrics = {
            "mean": mean_val,
            "median": median_val,
            "std_dev": std_val,
            "min": min_val,
            "max": max_val,
            "range": float(max_val - min_val),
            "count": len(values)
        }
        
        return metrics
    
    def _statistical_comparison(
        self, 
        datasets: List[List[Dict]]
    ) -> Dict[str, Any]:
        """Perform statistical comparison"""
        # Extract values
        value_lists = [
            [d.get("value", 0.0) for d in dataset]
            for dataset in datasets if dataset
        ]
        
        if len(value_lists) < 2:
            return {}
            
        try:
            # T-test
            if len(value_lists) == 2:
                # Require at least some variation to run t-test safely
                t_stat, p_value = stats.ttest_ind(value_lists[0], value_lists[1])
                
                if np.isnan(t_stat) or np.isnan(p_value):
                    return {
                        "test": "t-test",
                        "t_statistic": 0.0,
                        "p_value": 1.0,
                        "significant": False
                    }
                    
                return {
                    "test": "t-test",
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "significant": bool(p_value < 0.05)
                }
            
            # ANOVA for multiple groups
            elif len(value_lists) > 2:
                f_stat, p_value = stats.f_oneway(*value_lists)
                
                if np.isnan(f_stat) or np.isnan(p_value):
                    return {
                        "test": "ANOVA",
                        "f_statistic": 0.0,
                        "p_value": 1.0,
                        "significant": False
                    }
                    
                return {
                    "test": "ANOVA",
                    "f_statistic": float(f_stat),
                    "p_value": float(p_value),
                    "significant": bool(p_value < 0.05)
                }
        except Exception as e:
            logger.error(f"Statistical comparison error: {e}")
            
        return {}
    
    def _generate_insights(self, comparison: Dict) -> List[str]:
        """Generate insights from comparison"""
        insights = []
        
        metrics = comparison.get("metrics", {})
        if len(metrics) > 1:
            means = [m.get("mean", 0.0) for m in metrics.values() if m]
            if means and max(means) > min(means) * 1.5:
                insights.append("Significant difference in average values detected")
        
        # Check variability
        for exp_id, metric in metrics.items():
            if not metric:
                continue
            mean = metric.get("mean", 1.0)
            if mean == 0.0:
                mean = 1.0
            if metric.get("std_dev", 0.0) > mean * 0.5:
                insights.append(f"High variability in {exp_id}")
        
        return insights
    
    async def detect_anomalies(
        self,
        exp_id: str,
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in experiment data"""
        if exp_id not in self.experiments_data:
            return []
        
        data = self.experiments_data[exp_id]
        if not data:
            return []
            
        values = [d.get("value", 0.0) for d in data]
        
        # Z-score based anomaly detection
        mean = float(np.mean(values))
        std = float(np.std(values))
        
        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std) if std > 0 else 0.0
            
            if z_score > threshold:
                anomalies.append({
                    "index": i,
                    "value": float(value),
                    "z_score": float(z_score),
                    "timestamp": data[i].get("timestamp")
                })
        
        return anomalies
    
    async def trend_analysis(
        self,
        exp_id: str
    ) -> Dict[str, Any]:
        """Analyze trends in experiment data"""
        if exp_id not in self.experiments_data:
            return {}
        
        data = self.experiments_data[exp_id]
        if not data:
            return {}
            
        values = [d.get("value", 0.0) for d in data]
        if len(values) < 2:
            return {
                "slope": 0.0,
                "intercept": 0.0,
                "r_squared": 0.0,
                "p_value": 1.0,
                "trend": "stable",
                "strength": "weak"
            }
            
        # Linear regression
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # Guard against NaN values
        if np.isnan(slope):
            slope = 0.0
        if np.isnan(intercept):
            intercept = 0.0
        if np.isnan(r_value):
            r_value = 0.0
        if np.isnan(p_value):
            p_value = 1.0
            
        trend = {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "trend": "increasing" if slope > 0 else "decreasing",
            "strength": "strong" if abs(r_value) > 0.7 else "moderate" if abs(r_value) > 0.4 else "weak"
        }
        
        return trend
