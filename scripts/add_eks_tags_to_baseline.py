"""Add tags field to EKS clusters in baseline."""
import json
import boto3
from pathlib import Path

# Initialize EKS client
eks_client = boto3.client("eks", region_name="ap-southeast-1")

# Load baseline
baseline_file = Path("data/baseline/baseline_state.json")
with open(baseline_file) as f:
    baseline = json.load(f)

# Find EKS clusters
eks_clusters = None
if "resources" in baseline and "eks_clusters" in baseline["resources"]:
    eks_clusters = baseline["resources"]["eks_clusters"]
elif "eks_clusters" in baseline:
    eks_clusters = baseline["eks_clusters"]

if eks_clusters:
    for cluster in eks_clusters:
        cluster_name = cluster.get("name")
        if cluster_name:
            try:
                # Get cluster info from AWS
                response = eks_client.describe_cluster(name=cluster_name)
                tags = response["cluster"].get("tags", {})
                
                # Add tags to baseline
                cluster["tags"] = tags
                print(f"✅ Added tags to cluster: {cluster_name}")
                print(f"   Tags: {tags}")
            except Exception as e:
                print(f"❌ Failed to get tags for {cluster_name}: {e}")

    # Save baseline
    with open(baseline_file, "w") as f:
        json.dump(baseline, f, indent=2)
    
    print(f"\n✅ Baseline updated: {baseline_file}")
else:
    print("❌ No EKS clusters found in baseline")
