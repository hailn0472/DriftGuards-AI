"""Tests for baseline management."""

import json
from pathlib import Path

import pytest


class TestBaselineData:
    """Tests for baseline data files."""
    
    def test_baseline_file_exists(self):
        """Test that baseline state file exists."""
        baseline_file = Path(__file__).parent.parent / "data" / "baseline" / "baseline_state.json"
        assert baseline_file.exists(), "baseline_state.json should exist"
    
    def test_baseline_file_valid_json(self):
        """Test that baseline file contains valid JSON."""
        baseline_file = Path(__file__).parent.parent / "data" / "baseline" / "baseline_state.json"
        
        with open(baseline_file) as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert "account_id" in data
        assert "region" in data
        assert "resources" in data
    
    def test_baseline_has_required_fields(self):
        """Test that baseline has all required resource types."""
        baseline_file = Path(__file__).parent.parent / "data" / "baseline" / "baseline_state.json"
        
        with open(baseline_file) as f:
            data = json.load(f)
        
        resources = data.get("resources", {})
        
        # Check for expected resource types
        expected_types = [
            "vpcs",
            "ec2_instances",
            "security_groups",
            "s3_buckets",
        ]
        
        for resource_type in expected_types:
            assert resource_type in resources, f"{resource_type} should be in baseline"
    
    def test_baseline_ec2_instances_structure(self):
        """Test that EC2 instances in baseline have correct structure."""
        baseline_file = Path(__file__).parent.parent / "data" / "baseline" / "baseline_state.json"
        
        with open(baseline_file) as f:
            data = json.load(f)
        
        instances = data.get("resources", {}).get("ec2_instances", [])
        
        if instances:  # If there are instances
            instance = instances[0]
            required_fields = ["id", "type", "state"]
            
            for field in required_fields:
                assert field in instance, f"Instance should have {field} field"


class TestInventoryData:
    """Tests for inventory data files."""
    
    def test_inventory_directory_exists(self):
        """Test that inventory directory exists."""
        inventory_dir = Path(__file__).parent.parent / "data" / "inventory"
        assert inventory_dir.exists(), "data/inventory directory should exist"
