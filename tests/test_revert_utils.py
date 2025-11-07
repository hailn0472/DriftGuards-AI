"""Tests for revert utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.revert.boto3_revert import boto3_revert_to_baseline, _revert_ec2


class TestBoto3Revert:
    """Tests for boto3 revert functions."""
    
    def test_unsupported_resource_type(self):
        """Test revert with unsupported resource type."""
        result = boto3_revert_to_baseline(
            resource_type="unsupported_type",
            resource_id="test-123",
            account_id="123456789012",
            region="us-east-1",
            baseline_config={},
        )
        
        assert result["status"] == "error"
        assert "Unsupported resource type" in result["message"]
    
    @patch("app.revert.boto3_revert.boto3.client")
    def test_revert_ec2_instance_not_found(self, mock_boto3_client):
        """Test reverting EC2 instance that doesn't exist."""
        from botocore.exceptions import ClientError
        
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        
        # Simulate InvalidInstanceID.NotFound error
        error_response = {
            "Error": {
                "Code": "InvalidInstanceID.NotFound",
                "Message": "The instance ID 'i-invalid' does not exist"
            }
        }
        mock_ec2.describe_instances.side_effect = ClientError(error_response, "DescribeInstances")
        
        result = _revert_ec2(
            instance_id="i-invalid",
            baseline={"state": "running"},
            region="us-east-1",
        )
        
        assert result["status"] == "error"
        assert "does not exist" in result["message"]
    
    @patch("app.revert.boto3_revert.boto3.client")
    def test_revert_ec2_terminated_instance(self, mock_boto3_client):
        """Test reverting terminated EC2 instance."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        
        # Mock describe_instances response with terminated instance
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-12345",
                            "State": {"Name": "terminated"},
                            "InstanceType": "t2.micro",
                        }
                    ]
                }
            ]
        }
        
        result = _revert_ec2(
            instance_id="i-12345",
            baseline={"state": "running"},
            region="us-east-1",
        )
        
        assert result["status"] == "error"
        assert "terminated" in result["message"].lower()
    
    @patch("app.revert.boto3_revert.boto3.client")
    def test_revert_ec2_already_in_baseline_state(self, mock_boto3_client):
        """Test reverting EC2 instance that's already in baseline state."""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        
        # Mock describe_instances response
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-12345",
                            "State": {"Name": "running"},
                            "InstanceType": "t2.micro",
                        }
                    ]
                }
            ]
        }
        
        result = _revert_ec2(
            instance_id="i-12345",
            baseline={"state": "running", "type": "t2.micro"},
            region="us-east-1",
        )
        
        assert result["status"] == "success"
        assert "already in baseline state" in result["actions"][0]


class TestSelectiveRevert:
    """Tests for selective revert functionality."""
    
    @patch("app.revert.selective_revert.boto3.client")
    def test_selective_revert_tags(self, mock_boto3_client):
        """Test selective revert of instance tags."""
        from app.revert.selective_revert import selective_revert
        
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_boto3_client.return_value = mock_ec2
        
        # Mock current state
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-12345",
                            "State": {"Name": "running"},
                            "Tags": [{"Key": "Name", "Value": "wrong-name"}],
                        }
                    ]
                }
            ]
        }
        
        result = selective_revert(
            resource_type="ec2_instances",
            resource_id="i-12345",
            region="us-east-1",
            diff={
                "tags": {
                    "baseline": [{"Key": "Name", "Value": "correct-name"}],
                    "current": [{"Key": "Name", "Value": "wrong-name"}],
                }
            },
            selected_fields=["tags"],
        )
        
        # Should attempt to update tags
        assert result["status"] == "success"
        assert "tags" in result.get("reverted_fields", [])
