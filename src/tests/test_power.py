# src/tests/test_power.py

import unittest
from unittest.mock import Mock, patch
from ..core.power_management import PowerManagementSystem, PowerState, PowerProfile

class TestPowerManagement(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.power_system = PowerManagementSystem()
        
    def test_initialization(self):
        """Test power system initialization."""
        self.assertTrue(self.power_system.initialize())
        self.assertEqual(self.power_system.current_state, PowerState.STANDBY)
        self.assertEqual(self.power_system.battery_level, 100.0)
        
    def test_power_state_transitions(self):
        """Test power state transition logic."""
        self.power_system.initialize()
        
        # Test valid transitions
        self.assertTrue(self.power_system.request_power_state(PowerState.ACTIVE))
        self.assertEqual(self.power_system.current_state, PowerState.ACTIVE)
        
        self.assertTrue(self.power_system.request_power_state(PowerState.LOW_POWER))
        self.assertEqual(self.power_system.current_state, PowerState.LOW_POWER)
        
        # Test invalid transitions
        self.assertFalse(self.power_system.request_power_state(PowerState.BURST))
        
    def test_power_profiles(self):
        """Test power profile configuration and application."""
        self.power_system.initialize()
        
        for state in PowerState:
            self.assertIn(state, self.power_system.power_profiles)
            profile = self.power_system.power_profiles[state]
            self.assertIsInstance(profile, PowerProfile)
            self.assertTrue(profile.min_power <= profile.max_power)
            
    def test_power_monitoring(self):
        """Test power consumption monitoring."""
        self.power_system.initialize()
        consumption_data = self.power_system.monitor_power_consumption()
        
        # Verify monitoring data structure
        self.assertIn('state', consumption_data)
        self.assertIn('battery_level', consumption_data)
        self.assertIn('temperature', consumption_data)
        self.assertIn('primary_power', consumption_data)
        self.assertIn('supercap_power', consumption_data)
        
    def test_power_optimization(self):
        """Test power optimization functionality."""
        self.power_system.initialize()
        
        # Test low battery optimization
        with patch.object(self.power_system, 'battery_level', 15.0):
            self.power_system.optimize_power_consumption()
            self.assertEqual(self.power_system.current_state, PowerState.LOW_POWER)
            
        # Test thermal optimization
        with patch.object(self.power_system, 'temperature', 45.0):
            self.power_system.optimize_power_consumption()
            self.assertEqual(self.power_system.current_state, PowerState.LOW_POWER)
            
    def test_charging_system(self):
        """Test charging system functionality."""
        self.power_system.initialize()
        initial_level = self.power_system.battery_level
        
        # Test charging state transition
        self.assertTrue(self.power_system.request_power_state(PowerState.CHARGING))
        self.assertEqual(self.power_system.current_state, PowerState.CHARGING)
        
        # Simulate charging cycle
        with patch.object(self.power_system.primary_battery, 'charge', return_value=True):
            self.power_system._update_battery_level()
            self.assertGreater(self.power_system.battery_level, initial_level)
            
    def test_supercapacitor_management(self):
        """Test supercapacitor management functionality."""
        self.power_system.initialize()
        
        # Test supercapacitor charging
        initial_power = self.power_system.supercapacitor.get_available_power()
        self.power_system.charge_supercapacitor()
        self.assertGreater(
            self.power_system.supercapacitor.get_available_power(),
            initial_power
        )
        
        # Test burst mode with supercapacitor
        self.power_system.request_power_state(PowerState.BURST)
        self.assertTrue(self.power_system.supercapacitor.in_burst_mode)
        
    def test_thermal_management(self):
        """Test thermal management system."""
        self.power_system.initialize()
        
        # Test thermal threshold monitoring
        with patch.object(self.power_system, 'temperature', 45.0):
            self.power_system._activate_thermal_management()
            self.assertEqual(self.power_system.current_state, PowerState.LOW_POWER)
            
        # Test thermal generator
        thermal_power = self.power_system.thermal_generator.get_current_power()
        self.assertGreaterEqual(thermal_power, 0.0)
        self.assertLessEqual(thermal_power, 1.0)  # Reasonable range for thermal generation
        
    def test_motion_generator(self):
        """Test motion-based power generation."""
        self.power_system.initialize()
        
        # Test motion power generation
        motion_power = self.power_system.motion_generator.get_current_power()
        self.assertGreaterEqual(motion_power, 0.0)
        self.assertLessEqual(motion_power, 0.5)  # Reasonable range for motion generation
        
    def test_power_history(self):
        """Test power consumption history tracking."""
        self.power_system.initialize()
        
        # Record several power states
        test_states = [
            PowerState.ACTIVE,
            PowerState.LOW_POWER,
            PowerState.STANDBY
        ]
        
        for state in test_states:
            self.power_system.request_power_state(state)
            self.power_system.monitor_power_consumption()
            
        # Verify history maintenance
        consumption_data = self.power_system.monitor_power_consumption()
        self.assertIn('timestamp', consumption_data)
        self.assertIn('primary_power', consumption_data)
        self.assertIn('state', consumption_data)
        
    def test_emergency_shutdown(self):
        """Test emergency shutdown procedures."""
        self.power_system.initialize()
        
        # Simulate critical battery level
        with patch.object(self.power_system, 'battery_level', 5.0):
            self.power_system.optimize_power_consumption()
            self.assertEqual(self.power_system.current_state, PowerState.LOW_POWER)
            
        # Simulate critical temperature
        with patch.object(self.power_system, 'temperature', 80.0):
            self.power_system.optimize_power_consumption()
            self.assertEqual(self.power_system.current_state, PowerState.STANDBY)
            
    def test_power_efficiency(self):
        """Test power efficiency calculations."""
        self.power_system.initialize()
        
        # Test power efficiency in different states
        test_states = {
            PowerState.STANDBY: 0.1,    # Expected max power in standby
            PowerState.ACTIVE: 1.65,    # Expected max power in active
            PowerState.LOW_POWER: 0.33  # Expected max power in low power
        }
        
        for state, expected_max in test_states.items():
            self.power_system.request_power_state(state)
            consumption = self.power_system.monitor_power_consumption()
            self.assertLessEqual(consumption['primary_power'], expected_max)
            
    def tearDown(self):
        """Clean up after each test."""
        if self.power_system.current_state != PowerState.STANDBY:
            self.power_system.request_power_state(PowerState.STANDBY)

if __name__ == '__main__':
    unittest.main()