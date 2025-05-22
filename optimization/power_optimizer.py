# optimization/power_optimizer.py

from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass
import time
import json
from ..src.core.power_management import PowerState, PowerManagementSystem

@dataclass
class PowerUsagePattern:
    timestamp: float
    duration: float
    power_consumption: float
    power_state: PowerState

class PowerOptimizer:
    def __init__(self, power_system: PowerManagementSystem):
        self.power_system = power_system
        self.usage_history: List[PowerUsagePattern] = []
        self.learning_rate = 0.01
        self.prediction_window = 3600  # 1 hour
        
    def record_usage(self, pattern: PowerUsagePattern):
        """Record power usage pattern for analysis."""
        self.usage_history.append(pattern)
        if len(self.usage_history) > 1000:  # Limit history size
            self.usage_history = self.usage_history[-1000:]
            
    def analyze_usage_patterns(self) -> Dict:
        """Analyze usage patterns to identify optimization opportunities."""
        if not self.usage_history:
            return {}
            
        patterns = {
            'peak_usage_times': self._identify_peak_usage(),
            'average_duration': self._calculate_average_duration(),
            'state_distribution': self._analyze_state_distribution(),
            'power_efficiency': self._calculate_power_efficiency()
        }
        
        return patterns
        
    def _identify_peak_usage(self) -> List[float]:
        """Identify times of peak power usage."""
        if not self.usage_history:
            return []
            
        # Convert usage history to time series
        times = [p.timestamp for p in self.usage_history]
        power = [p.power_consumption for p in self.usage_history]
        
        # Find peaks using rolling window
        window_size = 10
        peaks = []
        
        for i in range(len(power) - window_size):
            window = power[i:i + window_size]
            if i > 0 and i < len(power) - window_size:
                if power[i] == max(window):
                    peaks.append(times[i])
                    
        return peaks
        
    def _calculate_average_duration(self) -> Dict[PowerState, float]:
        """Calculate average duration for each power state."""
        durations = {}
        counts = {}
        
        for pattern in self.usage_history:
            state = pattern.power_state
            if state not in durations:
                durations[state] = 0
                counts[state] = 0
                
            durations[state] += pattern.duration
            counts[state] += 1
            
        return {
            state: durations[state] / counts[state]
            for state in durations
        }
        
    def _analyze_state_distribution(self) -> Dict[PowerState, float]:
        """Analyze distribution of power states."""
        total = len(self.usage_history)
        if total == 0:
            return {}
            
        distribution = {}
        for pattern in self.usage_history:
            state = pattern.power_state
            if state not in distribution:
                distribution[state] = 0
            distribution[state] += 1
            
        return {
            state: count / total
            for state, count in distribution.items()
        }
        
    def _calculate_power_efficiency(self) -> float:
        """Calculate overall power efficiency metric."""
        if not self.usage_history:
            return 0.0
            
        total_power = sum(p.power_consumption * p.duration 
                         for p in self.usage_history)
        total_time = sum(p.duration for p in self.usage_history)
        
        return total_power / total_time if total_time > 0 else 0.0
        
    def predict_next_usage(self) -> Optional[PowerState]:
        """Predict next likely power state based on patterns."""
        if len(self.usage_history) < 2:
            return None
            
        recent_patterns = self.usage_history[-5:]  # Look at last 5 patterns
        
        # Calculate weighted average of recent states
        state_weights = {}
        total_weight = 0
        
        for i, pattern in enumerate(recent_patterns):
            weight = np.exp(i * 0.5)  # Exponential weighting
            total_weight += weight
            
            if pattern.power_state not in state_weights:
                state_weights[pattern.power_state] = 0
            state_weights[pattern.power_state] += weight
            
        # Normalize weights
        for state in state_weights:
            state_weights[state] /= total_weight
            
        # Return most likely next state
        return max(state_weights.items(), key=lambda x: x[1])[0]
        
    def optimize_power_allocation(self) -> Dict[str, float]:
        """Optimize power allocation based on usage patterns."""
        if not self.usage_history:
            return {}
            
        # Calculate basic statistics
        avg_consumption = np.mean([p.power_consumption for p in self.usage_history])
        std_consumption = np.std([p.power_consumption for p in self.usage_history])
        
        # Define power allocation strategy
        allocations = {
            'base_power': max(0.5 * avg_consumption, 0.1),  # Minimum 10% allocation
            'reserve_power': min(1.5 * std_consumption, 0.3),  # Maximum 30% reserve
            'burst_power': min(2.0 * avg_consumption, 0.6),  # Maximum 60% for burst
        }
        
        return allocations
        
    def suggest_optimizations(self) -> List[Dict]:
        """Generate power optimization suggestions."""
        patterns = self.analyze_usage_patterns()
        allocations = self.optimize_power_allocation()
        
        suggestions = []
        
        # Check for excessive burst mode usage
        if patterns.get('state_distribution', {}).get(PowerState.BURST, 0) > 0.3:
            suggestions.append({
                'type': 'state_optimization',
                'description': 'Reduce burst mode usage',
                'expected_saving': 0.15  # 15% power saving
            })
            
        # Check for power efficiency
        if self._calculate_power_efficiency() > 0.8:
            suggestions.append({
                'type': 'efficiency_alert',
                'description': 'High power consumption detected',
                'recommendation': 'Consider reducing projection brightness'
            })
            
        # Analyze idle periods
        avg_durations = patterns.get('average_duration', {})
        if avg_durations.get(PowerState.STANDBY, 0) < 60:  # Less than 1 minute
            suggestions.append({
                'type': 'idle_optimization',
                'description': 'Increase standby duration',
                'expected_saving': 0.1  # 10% power saving
            })
            
        return suggestions
        
    def apply_optimizations(self) -> bool:
        """Apply suggested optimizations automatically."""
        try:
            suggestions = self.suggest_optimizations()
            if not suggestions:
                return True
                
            for suggestion in suggestions:
                if suggestion['type'] == 'state_optimization':
                    # Adjust power state transition thresholds
                    self.power_system.power_profiles[PowerState.BURST].min_power *= 1.2
                    
                elif suggestion['type'] == 'efficiency_alert':
                    # Reduce maximum power allocation
                    self.power_system.power_profiles[PowerState.ACTIVE].max_power *= 0.9
                    
                elif suggestion['type'] == 'idle_optimization':
                    # Increase standby transition delay
                    self.power_system.request_power_state(PowerState.STANDBY)
                    
            return True
            
        except Exception as e:
            print(f"Error applying optimizations: {str(e)}")
            return False
            
    def generate_optimization_report(self) -> Dict:
        """Generate a comprehensive optimization report."""
        patterns = self.analyze_usage_patterns()
        allocations = self.optimize_power_allocation()
        suggestions = self.suggest_optimizations()
        
        return {
            'usage_patterns': patterns,
            'power_allocations': allocations,
            'optimization_suggestions': suggestions,
            'efficiency_metrics': {
                'overall_efficiency': self._calculate_power_efficiency(),
                'state_distribution': self._analyze_state_distribution(),
                'peak_usage_count': len(self._identify_peak_usage())
            },
            'projected_savings': sum(
                suggestion.get('expected_saving', 0)
                for suggestion in suggestions
            )
        }

def main():
    # Example usage of the PowerOptimizer
    power_system = PowerManagementSystem()
    optimizer = PowerOptimizer(power_system)
    
    # Record some sample usage patterns
    current_time = time.time()
    sample_patterns = [
        PowerUsagePattern(current_time - 3600, 300, 1.5, PowerState.ACTIVE),
        PowerUsagePattern(current_time - 2700, 200, 2.5, PowerState.BURST),
        PowerUsagePattern(current_time - 1800, 400, 0.5, PowerState.STANDBY)
    ]
    
    for pattern in sample_patterns:
        optimizer.record_usage(pattern)
    
    # Generate and print optimization report
    report = optimizer.generate_optimization_report()
    print("\nOptimization Report:")
    print(json.dumps(report, indent=2, default=str))
    
    # Apply optimizations
    if optimizer.apply_optimizations():
        print("\nOptimizations applied successfully!")
    else:
        print("\nFailed to apply optimizations")

if __name__ == "__main__":
    main()