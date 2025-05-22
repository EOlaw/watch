# src/tests/test_holographic.py

import unittest
from unittest.mock import Mock, patch
import numpy as np
from ..core.holographic_controller import HolographicProjector

class TestHolographicProjector(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.projector = HolographicProjector()
        
    def test_initialization(self):
        """Test projector initialization."""
        self.assertTrue(self.projector.initialize_system())
        self.assertIsNotNone(self.projector.laser_modules)
        self.assertIsNotNone(self.projector.mems_config)
        self.assertIsNotNone(self.projector.meta_surface_array)
        
    def test_projection_control(self):
        """Test basic projection control functionality."""
        self.projector.initialize_system()
        
        # Test starting projection
        self.projector.start_projection()
        self.assertTrue(self.projector.is_projecting)
        
        # Test stopping projection
        self.projector.stop_projection()
        self.assertFalse(self.projector.is_projecting)
        
    def test_laser_configuration(self):
        """Test laser module configuration."""
        self.projector.initialize_system()
        
        for color in ['red', 'green', 'blue']:
            self.assertIn(color, self.projector.laser_modules)
            laser_config = self.projector.laser_modules[color]
            self.assertTrue(0 < laser_config.power_output <= 5.0)  # reasonable power range
            self.assertTrue(0 <= laser_config.temperature <= 70.0)  # reasonable temp range
            
    def test_meta_surface_array(self):
        """Test meta-surface array manipulation."""
        self.projector.initialize_system()
        
        # Test array dimensions
        self.assertEqual(self.projector.meta_surface_array.shape, (20000, 15000))
        
        # Test array modification
        test_pattern = np.random.randint(0, 256, size=(20000, 15000), dtype=np.uint8)
        self.projector.start_projection(test_pattern)
        np.testing.assert_array_equal(self.projector.meta_surface_array, test_pattern)
        
    def test_diagnostic_system(self):
        """Test diagnostic functionality."""
        self.projector.initialize_system()
        diagnostic = self.projector.run_diagnostic()
        
        # Check diagnostic output structure
        self.assertIn('laser_status', diagnostic)
        self.assertIn('mirror_status', diagnostic)
        self.assertIn('meta_surface_status', diagnostic)
        self.assertIn('temperature', diagnostic)
        self.assertIn('power_consumption', diagnostic)
        
        # Verify status values
        self.assertTrue(all(status == 'operational' 
                          for status in diagnostic['laser_status'].values()))
        self.assertEqual(diagnostic['mirror_status'], 'operational')
        self.assertEqual(diagnostic['meta_surface_status'], 'operational')
        
    def test_error_handling(self):
        """Test error handling in projector operations."""
        # Test initialization failure
        with patch.object(self.projector, '_init_laser_modules', 
                         side_effect=Exception('Laser init failed')):
            self.assertFalse(self.projector.initialize_system())
            
        # Test projection failure
        self.projector.initialize_system()
        with patch.object(self.projector, '_projection_loop', 
                         side_effect=Exception('Projection failed')):
            self.projector.start_projection()
            self.assertFalse(self.projector.is_projecting)
            
    def test_parameter_adjustment(self):
        """Test projection parameter adjustment."""
        self.projector.initialize_system()
        
        # Test parameter ranges
        test_params = {
            'brightness': 75.0,
            'contrast': 60.0,
            'size': 85.0
        }
        
        self.projector.set_projection_parameters(**test_params)
        diagnostic = self.projector.run_diagnostic()
        self.assertTrue(0 <= diagnostic['power_consumption'] <= 5.0)  # reasonable power range
        
    def test_temperature_monitoring(self):
        """Test temperature monitoring and safety features."""
        self.projector.initialize_system()
        
        # Simulate high temperature
        with patch.object(self.projector, '_get_system_temperature', return_value=75.0):
            diagnostic = self.projector.run_diagnostic()
            self.assertGreater(diagnostic['temperature'], 70.0)
            
            # Verify projection is blocked at high temperature
            self.assertFalse(self.projector.start_projection())
            
    def tearDown(self):
        """Clean up after each test."""
        if self.projector.is_projecting:
            self.projector.stop_projection()
