"""
Pulumi Cleanup Program - Safe Resource Destruction

This script provides different cleanup strategies:
1. Stop-only mode: Stops compute resources to save costs (reversible)
2. Destroy mode: Removes all resources permanently

Usage:
    python cleanup_pulumi.py --preview          # Show what would be destroyed
    python cleanup_pulumi.py --stop-only        # Stop compute only
    python cleanup_pulumi.py --destroy          # Destroy everything
    python cleanup_pulumi.py --destroy --force  # No confirmations

This script can be run independently or called from cleanup.ps1
"""

import argparse
import json
import sys
import subprocess
from typing import Dict, List, Optional

try:
    import pulumi
    from pulumi import automation as auto
    PULUMI_AVAILABLE = True
except ImportError:
    PULUMI_AVAILABLE = False
    print("⚠️  Pulumi Python SDK not available. Install with: pip install pulumi")


class PulumiCleanup:
    """Manages cleanup operations for Pulumi-deployed infrastructure"""
    
    def __init__(self, project_name: str = "ecommerce-infra", stack_name: str = "dev"):
        self.project_name = project_name
        self.stack_name = stack_name
        self.workspace = None
        
    def initialize(self) -> bool:
        """Initialize Pulumi workspace"""
        try:
            self.workspace = auto.LocalWorkspace(
                project_settings=auto.ProjectSettings(
                    name=self.project_name,
                    runtime="python"
                ),
                work_dir="."
            )
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Pulumi workspace: {e}")
            return False
    
    def get_stack_outputs(self) -> Dict:
        """Get current stack outputs"""
        try:
            result = subprocess.run(
                ["pulumi", "stack", "output", "--json"],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError:
            return {}
        except json.JSONDecodeError:
            return {}
    
    def preview_destroy(self) -> None:
        """Show what would be destroyed"""
        print("\n🔍 Previewing resources that would be destroyed...\n")
        subprocess.run(["pulumi", "preview", "--diff"])
    
    def stop_compute_resources(self) -> None:
        """Stop compute resources without destroying infrastructure"""
        print("\n⏸️  Stopping compute resources...\n")
        
        outputs = self.get_stack_outputs()
        
        # Stop ECS services
        if "ecs_cluster_name" in outputs:
            self._stop_ecs_services(outputs["ecs_cluster_name"])
        
        # Scale down EKS nodes
        if "eks_cluster_name" in outputs:
            self._scale_down_eks(outputs["eks_cluster_name"])
        
        # Stop Aurora cluster
        if "aurora_cluster_endpoint" in outputs:
            self._stop_aurora(outputs["aurora_cluster_endpoint"])
        
        print("\n✅ Compute resources stopped!")
        print("💰 Estimated cost savings: 70-80%")
        print("📝 Resources are still present and can be restarted")
    
    def _stop_ecs_services(self, cluster_name: str) -> None:
        """Stop all ECS services in a cluster"""
        try:
            print(f"  🛑 Stopping ECS services in cluster: {cluster_name}")
            
            # List services
            result = subprocess.run(
                ["aws", "ecs", "list-services", "--cluster", cluster_name, "--query", "serviceArns[*]", "--output", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            services = json.loads(result.stdout)
            
            for service_arn in services:
                service_name = service_arn.split('/')[-1]
                print(f"    Scaling down: {service_name}")
                subprocess.run(
                    ["aws", "ecs", "update-service", "--cluster", cluster_name, 
                     "--service", service_name, "--desired-count", "0"],
                    capture_output=True,
                    check=True
                )
            
            print(f"  ✅ Stopped {len(services)} ECS service(s)")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Could not stop ECS services: {e}")
        except json.JSONDecodeError:
            print("  ⚠️  No ECS services found")
    
    def _scale_down_eks(self, cluster_name: str) -> None:
        """Scale down EKS node groups"""
        try:
            print(f"  🛑 Scaling down EKS cluster: {cluster_name}")
            
            # List node groups
            result = subprocess.run(
                ["aws", "eks", "list-nodegroups", "--cluster-name", cluster_name, "--query", "nodegroups[*]", "--output", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            node_groups = json.loads(result.stdout)
            
            for node_group in node_groups:
                print(f"    Scaling down node group: {node_group}")
                subprocess.run(
                    ["aws", "eks", "update-nodegroup-config", "--cluster-name", cluster_name,
                     "--nodegroup-name", node_group, "--scaling-config", "minSize=0,maxSize=0,desiredSize=0"],
                    capture_output=True,
                    check=True
                )
            
            print(f"  ✅ Scaled down {len(node_groups)} node group(s)")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Could not scale down EKS: {e}")
        except json.JSONDecodeError:
            print("  ⚠️  No EKS node groups found")
    
    def _stop_aurora(self, endpoint: str) -> None:
        """Stop Aurora cluster"""
        try:
            cluster_id = endpoint.split('.')[0]
            print(f"  🛑 Stopping Aurora cluster: {cluster_id}")
            
            subprocess.run(
                ["aws", "rds", "stop-db-cluster", "--db-cluster-identifier", cluster_id],
                capture_output=True,
                check=True
            )
            
            print(f"  ✅ Aurora cluster stopped (will auto-start in 7 days)")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Could not stop Aurora: {e}")
    
    def destroy_all(self, force: bool = False) -> None:
        """Destroy all Pulumi resources"""
        print("\n💥 Destroying all resources...\n")
        
        # Show what will be destroyed
        if not force:
            self.preview_destroy()
            print("\n⚠️  WARNING: This will permanently delete all resources! ⚠️")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm != "DELETE":
                print("❌ Cancelled")
                return
        
        # Stop compute first for faster deletion
        print("\n📋 Step 1: Stopping compute resources...")
        self.stop_compute_resources()
        
        # Run destroy
        print("\n📋 Step 2: Destroying infrastructure...")
        cmd = ["pulumi", "destroy"]
        if force:
            cmd.extend(["--yes", "--skip-preview"])
        
        try:
            subprocess.run(cmd, check=True)
            print("\n✅ All resources destroyed successfully!")
            
            # Optionally remove stack
            if not force:
                remove = input("\n🗑️  Remove stack state? (yes/no): ")
                if remove.lower() == "yes":
                    subprocess.run(["pulumi", "stack", "rm", "--yes"], check=True)
                    print("✅ Stack removed")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Destroy failed: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup Pulumi-deployed AWS infrastructure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_pulumi.py --preview         # Preview what would be destroyed
  python cleanup_pulumi.py --stop-only       # Stop compute resources only
  python cleanup_pulumi.py --destroy         # Destroy everything (with confirmation)
  python cleanup_pulumi.py --destroy --force # Destroy without confirmation

Cost Savings:
  --stop-only:  ~70-80% cost reduction (keeps infrastructure)
  --destroy:    100% cost reduction (removes everything)
        """
    )
    
    parser.add_argument("--preview", action="store_true", help="Preview what would be destroyed")
    parser.add_argument("--stop-only", action="store_true", help="Stop compute resources only (reversible)")
    parser.add_argument("--destroy", action="store_true", help="Destroy all resources (permanent)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--project", default="ecommerce-infra", help="Pulumi project name")
    parser.add_argument("--stack", default="dev", help="Pulumi stack name")
    
    args = parser.parse_args()
    
    # Show help if no action specified
    if not any([args.preview, args.stop_only, args.destroy]):
        parser.print_help()
        sys.exit(0)
    
    # Create cleanup manager
    cleanup = PulumiCleanup(args.project, args.stack)
    
    # Execute requested action
    if args.preview:
        cleanup.preview_destroy()
    elif args.stop_only:
        cleanup.stop_compute_resources()
    elif args.destroy:
        cleanup.destroy_all(args.force)


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║   Pulumi Cleanup - Infrastructure Management             ║
║   ⚠️  Handle with care - manages production resources!   ║
╔═══════════════════════════════════════════════════════════╗
    """)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
