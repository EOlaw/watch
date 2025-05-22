# src/tests/test_system.py

import unittest
from unittest.mock import Mock, patch
import time
from ..core.system_interface import HolographicSystemInterface
from ..core.power_management import PowerState

class TestHolographicSystem(unittest.TestCase):
    def setUp(self):
        self.system = HolographicSystemInterface()
        
    def test_system_initialization(self):
        """Test system initialization sequence."""
        self.assertTrue(self.system.initialize_system())
        status = self.system.get_system_status()
        self.assertEqual(status.power_state, PowerState.STANDBY)
        
    def test_hologram_projection(self):
        """Test hologram projection lifecycle."""
        self.system.initialize_system()
        
        # Start projection
        self.assertTrue(self.system.start_hologram())
        status = self.system.get_system_status()
        self.assertTrue(status.projection_active)
        self.assertEqual(status.power_state, PowerState.BURST)
        
        # Stop projection
        self.system.stop_hologram()
        status = self.system.get_system_status()
        self.assertFalse(status.projection_active)
        self.assertEqual(status.power_state, PowerState.STANDBY)
        
    def test_power_management(self):
        """Test power management functionality."""
        self.system.initialize_system()
        
        # Test low battery handling
        with patch.object(self.system.power_system, 'battery_level', 10.0):
            status = self.system.get_system_status()
            self.assertEqual(status.system_health['power_system'], 'low')
            
            # Attempt to start projection
            self.assertFalse(self.system.start_hologram())
            
    def test_temperature_management(self):
        """Test temperature management."""
        self.system.initialize_system()
        
        # Test high temperature handling
        with patch.object(self.system.power_system, 'temperature', 45.0):
            self.system.start_hologram()
            time.sleep(0.2)  # Allow monitoring loop to detect temperature
            
            status = self.system.get_system_status()
            self.assertFalse(status.projection_active)
            self.assertEqual(status.power_state, PowerState.LOW_POWER)
            
    def test_system_shutdown(self):
        """Test system shutdown sequence."""
        self.system.initialize_system()
        self.system.start_hologram()
        
        self.system.shutdown()
        status = self.system.get_system_status()
        self.assertFalse(status.projection_active)
        self.assertEqual(status.power_state, PowerState.STANDBY)

# src/tests/test_power.py

class TestPowerManagement(unittest.TestCase):
    def setUp(self):
        self.power_system = PowerManagementSystem()
        
    def test_power_state_transitions(self):
        """Test power state transition validation."""
        self.power_system.initialize()
        
        # Test valid transitions
        self.assertTrue(self.power_system.request_power_state(PowerState.ACTIVE))
        self.assertEqual(self.power_system.current_state, PowerState.ACTIVE)
        
        # Test invalid transitions
        self.assertFalse(self.power_system.request_power_state(PowerState.BURST))
        
    def test_power_optimization(self):
        """Test power optimization functionality."""
        self.power_system.initialize()
        
        # Test low battery optimization
        self.power_system.battery_level = 15.0
        self.power_system.optimize_power_consumption()
        self.assertEqual(self.power_system.current_state, PowerState.LOW_POWER)

# src/tests/test_holographic.py

class TestHolographicProjector(unittest.TestCase):
    def setUp(self):
        self.projector = HolographicProjector()
        
    def test_projector_initialization(self):
        """Test projector initialization."""
        self.assertTrue(self.projector.initialize_system())
        self.assertFalse(self.projector.is_projecting)
        
    def test_projection_control(self):
        """Test projection control functions."""
        self.projector.initialize_system()
        
        self.projector.start_projection()
        self.assertTrue(self.projector.is_projecting)
        
        self.projector.stop_projection()
        self.assertFalse(self.projector.is_projecting)
        
    def test_diagnostic(self):
        """Test diagnostic functionality."""
        self.projector.initialize_system()
        diagnostic = self.projector.run_diagnostic()
        
        self.assertIn('laser_status', diagnostic)
        self.assertIn('mirror_status', diagnostic)
        self.assertIn('meta_surface_status', diagnostic)

if __name__ == '__main__':
    unittest.main()