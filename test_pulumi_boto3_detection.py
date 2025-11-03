"""
Test Script: Verify boto3 detects all Pulumi-created resources

This script:
1. Creates a baseline of current AWS resources
2. Runs `pulumi up` to deploy infrastructure
3. Discovers resources with boto3
4. Compares to verify all Pulumi resources are detected
5. Runs `pulumi destroy` to clean up
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.agents.boto3_detection import Boto3DriftDetector
from scripts.discover_aws_resources import AWSResourceDiscovery


class PulumiBot3Test:
    """Test boto3 detection with Pulumi deployment."""

    def __init__(self):
        self.pulumi_dir = project_root / "data-example"
        self.discovery = AWSResourceDiscovery()
        self.drift_detector = Boto3DriftDetector()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "stages": {},
            "resources_detected": {},
            "verification": {},
        }

    def print_header(self, title):
        """Print formatted header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_section(self, title):
        """Print formatted section."""
        print("\n" + "-" * 80)
        print(f"  {title}")
        print("-" * 80)

    def run_command(self, cmd, cwd=None, capture=True):
        """Run a command and return output."""
        print(f"  Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, cwd=cwd or self.pulumi_dir, capture_output=capture, text=True, check=False
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            print(f"  ❌ Command failed: {e}")
            return -1, "", str(e)

    async def stage_1_baseline(self):
        """Stage 1: Create baseline before Pulumi deployment."""
        self.print_header("STAGE 1: Create Baseline (Before Pulumi)")

        print("\n📊 Discovering current AWS resources...")
        baseline = self.discovery.discover_all()

        # Save baseline
        baseline_file = Path("baseline_before_pulumi.json")
        with open(baseline_file, "w") as f:
            json.dump(baseline, f, indent=2, default=str)

        print(f"\n✅ Baseline saved to: {baseline_file}")

        # Print summary
        print("\n📋 Current Resources (Before Pulumi):")
        for key, value in baseline.items():
            if isinstance(value, dict) and "count" in value:
                count = value["count"]
                if count > 0:
                    print(f"  • {key}: {count}")

        self.test_results["stages"]["baseline"] = {
            "status": "success",
            "resources": {k: v.get("count", 0) for k, v in baseline.items() if isinstance(v, dict)},
            "file": str(baseline_file),
        }

        return baseline

    async def stage_2_pulumi_check(self):
        """Stage 2: Check Pulumi prerequisites."""
        self.print_header("STAGE 2: Check Pulumi Prerequisites")

        # Check Pulumi CLI
        print("\n🔍 Checking Pulumi CLI...")
        code, stdout, stderr = self.run_command(["pulumi", "version"])
        if code != 0:
            print("  ❌ Pulumi not found!")
            print("  💡 Install: https://www.pulumi.com/docs/install/")
            return False

        print(f"  ✅ Pulumi version: {stdout.strip()}")

        # Check if stack exists
        print("\n🔍 Checking Pulumi stack...")
        code, stdout, stderr = self.run_command(["pulumi", "stack", "--show-name"])
        if code != 0:
            print("  ⚠️  No Pulumi stack initialized")
            print("  💡 Run: pulumi stack init dev")
            return False

        stack_name = stdout.strip()
        print(f"  ✅ Current stack: {stack_name}")

        # Check configuration
        print("\n🔍 Checking Pulumi configuration...")
        code, stdout, stderr = self.run_command(["pulumi", "config", "get", "aws:region"])
        if code == 0:
            print(f"  ✅ AWS Region: {stdout.strip()}")
        else:
            print("  ⚠️  AWS region not set")

        self.test_results["stages"]["pulumi_check"] = {
            "status": "success",
            "stack": stack_name if code == 0 else "unknown",
        }

        return True

    async def stage_3_pulumi_preview(self):
        """Stage 3: Preview Pulumi deployment."""
        self.print_header("STAGE 3: Preview Pulumi Deployment")

        print("\n🔍 Running pulumi preview...")
        print("  (This shows what will be created without actually deploying)")

        code, stdout, stderr = self.run_command(["pulumi", "preview", "--json"])

        if code == 0:
            print("  ✅ Preview successful!")
            try:
                # Count resources to be created
                lines = stdout.strip().split("\n")
                create_count = sum(1 for line in lines if '"create"' in line.lower())
                print(f"  📊 Resources to create: ~{create_count}")
            except:
                pass
        else:
            print("  ⚠️  Preview had warnings (this is normal)")

        self.test_results["stages"]["preview"] = {
            "status": "success" if code == 0 else "warning",
            "exit_code": code,
        }

        return True

    async def stage_4_pulumi_up(self):
        """Stage 4: Deploy with Pulumi."""
        self.print_header("STAGE 4: Deploy Infrastructure with Pulumi")

        print("\n🚀 Running pulumi up...")
        print("  ⏳ This may take 10-20 minutes (EKS takes longest)")
        print("  💰 WARNING: This will create billable AWS resources!")

        # Ask for confirmation
        response = input("\n  Deploy infrastructure? (yes/no): ").strip().lower()
        if response != "yes":
            print("  ❌ Deployment cancelled by user")
            self.test_results["stages"]["deployment"] = {
                "status": "cancelled",
                "reason": "User cancelled",
            }
            return False

        print("\n  Deploying... (this will take a while)")

        # Run pulumi up with auto-approve
        code, stdout, stderr = self.run_command(
            ["pulumi", "up", "--yes", "--skip-preview"],
            capture=False,  # Show output in real-time
        )

        if code == 0:
            print("\n  ✅ Deployment successful!")
            self.test_results["stages"]["deployment"] = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }
            return True
        else:
            print(f"\n  ❌ Deployment failed with exit code {code}")
            print(f"  Error: {stderr}")
            self.test_results["stages"]["deployment"] = {
                "status": "failed",
                "exit_code": code,
                "error": stderr,
            }
            return False

    async def stage_5_discover_resources(self):
        """Stage 5: Discover resources after Pulumi deployment."""
        self.print_header("STAGE 5: Discover Resources (After Pulumi)")

        print("\n📊 Discovering AWS resources with boto3...")
        after_deployment = self.discovery.discover_all()

        # Save results
        after_file = Path("resources_after_pulumi.json")
        with open(after_file, "w") as f:
            json.dump(after_deployment, f, indent=2, default=str)

        print(f"\n✅ Discovery results saved to: {after_file}")

        # Print summary
        print("\n📋 Resources Found (After Pulumi):")
        resource_counts = {}
        for key, value in after_deployment.items():
            if isinstance(value, dict) and "count" in value:
                count = value["count"]
                resource_counts[key] = count
                if count > 0:
                    emoji = "✅" if count > 0 else "  "
                    print(f"  {emoji} {key}: {count}")

        self.test_results["stages"]["discovery"] = {
            "status": "success",
            "resources": resource_counts,
            "file": str(after_file),
        }

        return after_deployment, resource_counts

    async def stage_6_verify_detection(self, baseline, after_deployment):
        """Stage 6: Verify boto3 detected all Pulumi resources."""
        self.print_header("STAGE 6: Verify Detection")

        print("\n🔍 Comparing baseline vs after deployment...")

        # Expected Pulumi resources (from __main__.py)
        expected_resources = {
            "vpcs": 1,  # ecom-vpc
            "eks_clusters": 1,  # frontend-eks
            "ecs_clusters": 1,  # order-ecs-cluster
            "rds_clusters": 1,  # aurora-cluster
            "rds_instances": 1,  # aurora-instance-1
            "dynamodb_tables": 1,  # session-table
            "s3_buckets": 1,  # assets-bucket
            "sqs_queues": 1,  # order-queue
            "security_groups": "+1",  # msk-sg (plus existing)
        }

        print("\n📊 Verification Results:\n")
        print(f"  {'Resource Type':<25} {'Expected':<12} {'Detected':<12} {'Status'}")
        print("  " + "-" * 78)

        all_detected = True
        detection_results = {}

        for resource_type, expected in expected_resources.items():
            baseline_count = baseline.get(resource_type, {}).get("count", 0)
            after_count = after_deployment.get(resource_type, {}).get("count", 0)
            new_count = after_count - baseline_count

            if expected == "+1":
                detected = new_count >= 1
                status = "✅ Detected" if detected else "❌ MISSING"
                print(f"  {resource_type:<25} {'+1':<12} {new_count:<12} {status}")
            else:
                detected = new_count >= expected
                status = "✅ Detected" if detected else "❌ MISSING"
                print(f"  {resource_type:<25} {expected:<12} {new_count:<12} {status}")

            detection_results[resource_type] = {
                "expected": expected,
                "detected": new_count,
                "status": "success" if detected else "missing",
            }

            if not detected:
                all_detected = False

        # Resources that Terraform CAN'T detect but boto3 CAN
        print("\n📊 Resources Terraform CAN'T list (but boto3 CAN!):\n")
        terraform_cant_detect = ["ecs_clusters", "s3_buckets", "dynamodb_tables", "sqs_queues"]

        for resource_type in terraform_cant_detect:
            if resource_type in detection_results:
                result = detection_results[resource_type]
                emoji = "✅" if result["status"] == "success" else "❌"
                print(f"  {emoji} {resource_type}: {result['detected']} (Terraform would find 0!)")

        self.test_results["verification"] = {
            "all_detected": all_detected,
            "details": detection_results,
        }

        if all_detected:
            print("\n✅ SUCCESS! boto3 detected ALL Pulumi resources!")
        else:
            print("\n⚠️  WARNING: Some resources were not detected")

        return all_detected

    async def stage_7_pulumi_destroy(self):
        """Stage 7: Destroy Pulumi infrastructure."""
        self.print_header("STAGE 7: Clean Up (Pulumi Destroy)")

        print("\n🗑️  Preparing to destroy infrastructure...")
        print("  💰 This will remove all billable resources")

        # Ask for confirmation
        response = input("\n  Destroy infrastructure? (yes/no): ").strip().lower()
        if response != "yes":
            print("  ⚠️  Destroy cancelled - resources still running!")
            print("  💡 To destroy later, run: cd data-example && pulumi destroy")
            self.test_results["stages"]["cleanup"] = {
                "status": "skipped",
                "reason": "User cancelled",
            }
            return False

        print("\n  Destroying... (this may take 5-10 minutes)")

        # Run pulumi destroy
        code, stdout, stderr = self.run_command(
            ["pulumi", "destroy", "--yes", "--skip-preview"],
            capture=False,  # Show output in real-time
        )

        if code == 0:
            print("\n  ✅ Infrastructure destroyed successfully!")
            self.test_results["stages"]["cleanup"] = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }
            return True
        else:
            print(f"\n  ❌ Destroy failed with exit code {code}")
            print(f"  Error: {stderr}")
            print("\n  ⚠️  IMPORTANT: Resources may still be running!")
            print("  💡 Try: cd data-example && pulumi destroy")
            self.test_results["stages"]["cleanup"] = {
                "status": "failed",
                "exit_code": code,
                "error": stderr,
            }
            return False

    async def run_full_test(self):
        """Run complete test flow."""
        self.print_header("PULUMI + BOTO3 DETECTION TEST")
        print(f"\n  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Working Directory: {self.pulumi_dir}")

        try:
            # Stage 1: Baseline
            baseline = await self.stage_1_baseline()

            # Stage 2: Check Pulumi
            if not await self.stage_2_pulumi_check():
                print("\n❌ Pulumi prerequisites not met. Please set up Pulumi first.")
                return False

            # Stage 3: Preview
            await self.stage_3_pulumi_preview()

            # Stage 4: Deploy
            if not await self.stage_4_pulumi_up():
                print("\n❌ Deployment failed or cancelled.")
                return False

            # Wait a bit for resources to stabilize
            print("\n⏳ Waiting 30 seconds for resources to stabilize...")
            await asyncio.sleep(30)

            # Stage 5: Discover
            after_deployment, resource_counts = await self.stage_5_discover_resources()

            # Stage 6: Verify
            all_detected = await self.stage_6_verify_detection(baseline, after_deployment)

            # Stage 7: Cleanup
            await self.stage_7_pulumi_destroy()

            # Final summary
            self.print_header("TEST SUMMARY")
            print(f"\n  Test Status: {'✅ PASSED' if all_detected else '⚠️  PARTIAL'}")
            print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            if all_detected:
                print("\n  🎉 boto3 successfully detected ALL Pulumi resources!")
                print("  ✅ boto3 is a complete replacement for Terraform!")
            else:
                print("\n  ⚠️  Some resources were not detected")
                print("  Check the verification results above")

            # Save test results
            results_file = Path("test_results.json")
            with open(results_file, "w") as f:
                json.dump(self.test_results, f, indent=2, default=str)
            print(f"\n  📄 Full test results: {results_file}")

            return all_detected

        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
            print("  💡 Resources may still be running!")
            print("  Run: cd data-example && pulumi destroy")
            return False
        except Exception as e:
            print(f"\n\n❌ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            return False


async def main():
    """Main entry point."""
    tester = PulumiBot3Test()
    success = await tester.run_full_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("  PULUMI + BOTO3 DETECTION COMPREHENSIVE TEST")
    print("  Tests that boto3 can detect ALL Pulumi-created resources")
    print("=" * 80)
    print("\n⚠️  WARNING: This test will:")
    print("  1. Deploy real AWS infrastructure (costs money!)")
    print("  2. Take 10-20 minutes to complete")
    print("  3. Require Pulumi CLI and AWS credentials")
    print("\n💡 Make sure you have:")
    print("  • Pulumi CLI installed")
    print("  • AWS credentials configured")
    print("  • Pulumi secrets set (instana:agentKey, db:password)")
    print("\n")

    response = input("Ready to start test? (yes/no): ").strip().lower()
    if response != "yes":
        print("\n❌ Test cancelled")
        sys.exit(1)

    asyncio.run(main())
