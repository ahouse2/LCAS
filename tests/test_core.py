#!/usr/bin/env python3
"""
Tests for LCAS Core functionality
"""

import pytest
import asyncio
import tempfile
from pathlib import Path

from lcas.core import LCASCore, LCASConfig, PluginManager

class TestLCASConfig:
    """Test LCASConfig class"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = LCASConfig()
        assert config.case_name == ""
        assert config.source_directory == ""
        assert config.target_directory == ""
        assert config.debug_mode == False
        assert config.log_level == "INFO"
        assert len(config.enabled_plugins) > 0
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = LCASConfig(
            case_name="Test Case",
            source_directory="/test/source",
            target_directory="/test/target",
            debug_mode=True
        )
        assert config.case_name == "Test Case"
        assert config.source_directory == "/test/source"
        assert config.target_directory == "/test/target"
        assert config.debug_mode == True

class TestPluginManager:
    """Test PluginManager class"""
    
    def test_plugin_manager_init(self):
        """Test plugin manager initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = PluginManager(temp_dir)
            assert manager.plugins_directory == Path(temp_dir)
            assert len(manager.loaded_plugins) == 0
    
    def test_discover_plugins_empty(self):
        """Test plugin discovery with empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = PluginManager(temp_dir)
            plugins = manager.discover_plugins()
            assert plugins == []
    
    def test_discover_plugins_with_files(self):
        """Test plugin discovery with plugin files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock plugin files
            (Path(temp_dir) / "test_plugin.py").touch()
            (Path(temp_dir) / "another_plugin.py").touch()
            (Path(temp_dir) / "not_a_plugin.txt").touch()
            
            manager = PluginManager(temp_dir)
            plugins = manager.discover_plugins()
            assert "test_plugin" in plugins
            assert "another_plugin" in plugins
            assert len(plugins) == 2

class TestLCASCore:
    """Test LCASCore class"""
    
    def test_core_init(self):
        """Test core initialization"""
        config = LCASConfig(case_name="Test Case")
        core = LCASCore(config)
        assert core.config.case_name == "Test Case"
        assert core.running == False
        assert len(core.analysis_results) == 0
    
    @pytest.mark.asyncio
    async def test_core_initialize(self):
        """Test core initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LCASConfig(
                target_directory=temp_dir,
                plugins_directory=temp_dir
            )
            core = LCASCore(config)
            
            result = await core.initialize()
            assert result == True
            assert core.running == True
            
            await core.shutdown()
            assert core.running == False
    
    def test_case_data_management(self):
        """Test case data management"""
        core = LCASCore()
        
        # Test setting and getting data
        core.set_case_data("test_key", "test_value")
        assert core.get_case_data("test_key") == "test_value"
        
        # Test default value
        assert core.get_case_data("nonexistent", "default") == "default"
    
    def test_analysis_results_management(self):
        """Test analysis results management"""
        core = LCASCore()
        
        # Test setting and getting results
        test_result = {"status": "completed", "files": 5}
        core.set_analysis_result("test_plugin", test_result)
        
        stored_result = core.get_analysis_result("test_plugin")
        assert stored_result == test_result
        
        # Test nonexistent plugin
        assert core.get_analysis_result("nonexistent") is None
    
    def test_config_save_load(self):
        """Test configuration save and load"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.json"
            
            # Create and save config
            original_config = LCASConfig(
                case_name="Test Case",
                source_directory="/test/source"
            )
            core = LCASCore(original_config)
            
            result = core.save_config(str(config_file))
            assert result == True
            assert config_file.exists()
            
            # Load config
            loaded_core = LCASCore.load_config(str(config_file))
            assert loaded_core.config.case_name == "Test Case"
            assert loaded_core.config.source_directory == "/test/source"

if __name__ == "__main__":
    pytest.main([__file__])