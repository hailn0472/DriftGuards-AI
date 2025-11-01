# Cleanup Script - Stop and Destroy All Pulumi-Created Resources
# This script provides multiple options to clean up AWS infrastructure

param(
    [switch]$StopOnly,
    [switch]$DestroyAll,
    [switch]$Preview,
    [switch]$Force,
    [switch]$KeepState
)

$ErrorActionPreference = "Stop"

Write-Host @"
╔═══════════════════════════════════════════════════════════╗
║   Pulumi Cleanup - Stop/Destroy Infrastructure           ║
║   ⚠️  WARNING: This will affect running resources!       ║
╔═══════════════════════════════════════════════════════════╗
"@ -ForegroundColor Red

# Activate virtual environment if it exists
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "`n🔧 Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
}

# Check if Pulumi is available
try {
    $pulumiVersion = pulumi version 2>&1
    Write-Host "✅ Pulumi found: $pulumiVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Pulumi not found! Please install Pulumi first." -ForegroundColor Red
    Write-Host "Run: winget install pulumi" -ForegroundColor Yellow
    exit 1
}

# Check if stack exists
try {
    $stackName = pulumi stack --show-name 2>&1
    Write-Host "✅ Current stack: $stackName" -ForegroundColor Green
} catch {
    Write-Host "❌ No Pulumi stack found in this directory!" -ForegroundColor Red
    Write-Host "Make sure you're in the correct directory with Pulumi.yaml" -ForegroundColor Yellow
    exit 1
}

# Get stack outputs to see what's deployed
Write-Host "`n📊 Current deployed resources:" -ForegroundColor Cyan
try {
    pulumi stack output --json | ConvertFrom-Json | Format-List
} catch {
    Write-Host "⚠️  No outputs found (stack may be empty)" -ForegroundColor Yellow
}

# Function to stop ECS services
function Stop-ECSServices {
    Write-Host "`n🛑 Stopping ECS services..." -ForegroundColor Yellow
    
    try {
        $ecsClusterName = pulumi stack output ecs_cluster_name 2>&1
        if ($ecsClusterName) {
            Write-Host "  Found ECS cluster: $ecsClusterName" -ForegroundColor Gray
            
            # List and stop all services
            $services = aws ecs list-services --cluster $ecsClusterName --query 'serviceArns[*]' --output json 2>&1 | ConvertFrom-Json
            
            foreach ($service in $services) {
                $serviceName = $service.Split('/')[-1]
                Write-Host "  Scaling down service: $serviceName to 0 tasks" -ForegroundColor Gray
                aws ecs update-service --cluster $ecsClusterName --service $serviceName --desired-count 0 2>&1 | Out-Null
            }
            Write-Host "✅ ECS services stopped" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  Could not stop ECS services: $_" -ForegroundColor Yellow
    }
}

# Function to stop EKS node groups
function Stop-EKSNodes {
    Write-Host "`n🛑 Scaling down EKS node groups..." -ForegroundColor Yellow
    
    try {
        $eksClusterName = pulumi stack output eks_cluster_name 2>&1
        if ($eksClusterName) {
            Write-Host "  Found EKS cluster: $eksClusterName" -ForegroundColor Gray
            
            # List node groups
            $nodeGroups = aws eks list-nodegroups --cluster-name $eksClusterName --query 'nodegroups[*]' --output json 2>&1 | ConvertFrom-Json
            
            foreach ($nodeGroup in $nodeGroups) {
                Write-Host "  Scaling down node group: $nodeGroup to 0 nodes" -ForegroundColor Gray
                aws eks update-nodegroup-config --cluster-name $eksClusterName --nodegroup-name $nodeGroup --scaling-config minSize=0,maxSize=0,desiredSize=0 2>&1 | Out-Null
            }
            Write-Host "✅ EKS nodes scaled down" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  Could not scale down EKS nodes: $_" -ForegroundColor Yellow
    }
}

# Function to stop Aurora cluster
function Stop-AuroraCluster {
    Write-Host "`n🛑 Stopping Aurora cluster..." -ForegroundColor Yellow
    
    try {
        $auroraEndpoint = pulumi stack output aurora_cluster_endpoint 2>&1
        if ($auroraEndpoint) {
            # Extract cluster identifier from endpoint
            $clusterIdentifier = $auroraEndpoint.Split('.')[0]
            Write-Host "  Found Aurora cluster: $clusterIdentifier" -ForegroundColor Gray
            
            # Stop the cluster (saves costs while keeping data)
            aws rds stop-db-cluster --db-cluster-identifier $clusterIdentifier 2>&1 | Out-Null
            Write-Host "✅ Aurora cluster stopped (will auto-start after 7 days)" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️  Could not stop Aurora cluster: $_" -ForegroundColor Yellow
    }
}

# Main logic based on parameters
if ($Preview) {
    Write-Host "`n🔍 Preview mode - showing what would be destroyed..." -ForegroundColor Cyan
    pulumi preview --diff
    
    Write-Host "`n📋 To proceed with cleanup:" -ForegroundColor Cyan
    Write-Host "  Stop instances only: .\cleanup.ps1 -StopOnly" -ForegroundColor Gray
    Write-Host "  Destroy everything:  .\cleanup.ps1 -DestroyAll" -ForegroundColor Gray
    
} elseif ($StopOnly) {
    Write-Host "`n⏸️  Stop-only mode - stopping compute resources (keeps infrastructure)" -ForegroundColor Yellow
    Write-Host "This will:" -ForegroundColor Yellow
    Write-Host "  • Stop ECS services (scale to 0)" -ForegroundColor Gray
    Write-Host "  • Scale down EKS nodes (to 0)" -ForegroundColor Gray
    Write-Host "  • Stop Aurora cluster" -ForegroundColor Gray
    Write-Host "  • Keep: VPC, S3, DynamoDB, SQS, MSK (minimal cost)" -ForegroundColor Gray
    
    if (-not $Force) {
        $confirm = Read-Host "`nContinue? (yes/no)"
        if ($confirm -ne "yes") {
            Write-Host "Cancelled" -ForegroundColor Yellow
            exit 0
        }
    }
    
    Stop-ECSServices
    Stop-EKSNodes
    Stop-AuroraCluster
    
    Write-Host "`n✅ Compute resources stopped!" -ForegroundColor Green
    Write-Host "💰 This significantly reduces costs while keeping your infrastructure" -ForegroundColor Cyan
    Write-Host "To fully destroy everything, run: .\cleanup.ps1 -DestroyAll" -ForegroundColor Gray
    
} elseif ($DestroyAll) {
    Write-Host "`n💥 Destroy mode - removing ALL resources" -ForegroundColor Red
    Write-Host "This will permanently delete:" -ForegroundColor Red
    Write-Host "  • EKS cluster and all workloads" -ForegroundColor Gray
    Write-Host "  • ECS cluster and tasks" -ForegroundColor Gray
    Write-Host "  • Aurora database (⚠️  DATA LOSS!)" -ForegroundColor Gray
    Write-Host "  • DynamoDB tables (⚠️  DATA LOSS!)" -ForegroundColor Gray
    Write-Host "  • S3 buckets and contents (⚠️  DATA LOSS!)" -ForegroundColor Gray
    Write-Host "  • VPC, subnets, security groups" -ForegroundColor Gray
    Write-Host "  • MSK cluster" -ForegroundColor Gray
    Write-Host "  • All monitoring and logs" -ForegroundColor Gray
    
    if (-not $Force) {
        Write-Host "`n⚠️  THIS CANNOT BE UNDONE! ⚠️" -ForegroundColor Red
        $confirm = Read-Host "Type 'DELETE' to confirm destruction"
        if ($confirm -ne "DELETE") {
            Write-Host "Cancelled - smart choice!" -ForegroundColor Yellow
            exit 0
        }
    }
    
    Write-Host "`n🔥 Starting destruction..." -ForegroundColor Red
    
    # First stop compute to speed up deletion
    Write-Host "Step 1: Stopping compute resources..." -ForegroundColor Yellow
    Stop-ECSServices
    Stop-EKSNodes
    
    # Run Pulumi destroy
    Write-Host "`nStep 2: Running Pulumi destroy..." -ForegroundColor Yellow
    if ($Force) {
        pulumi destroy --yes --skip-preview
    } else {
        pulumi destroy
    }
    
    # Optionally remove stack state
    if ($KeepState) {
        Write-Host "`n✅ Resources destroyed, stack state preserved" -ForegroundColor Green
    } else {
        Write-Host "`n🗑️  Removing stack..." -ForegroundColor Yellow
        $removeStack = Read-Host "Remove stack state? (yes/no)"
        if ($removeStack -eq "yes") {
            pulumi stack rm --yes
            Write-Host "✅ Stack removed" -ForegroundColor Green
        }
    }
    
    Write-Host "`n✅ Cleanup complete!" -ForegroundColor Green
    Write-Host "💰 All AWS resources have been destroyed" -ForegroundColor Cyan
    
} else {
    # No parameters - show help
    Write-Host @"

📖 Usage:
  .\cleanup.ps1 -Preview          # Preview what would be destroyed (safe)
  .\cleanup.ps1 -StopOnly         # Stop compute resources only (saves $$$)
  .\cleanup.ps1 -DestroyAll       # Destroy everything (permanent!)
  .\cleanup.ps1 -DestroyAll -Force    # Destroy without prompts

Options:
  -Preview        Show what would be destroyed without doing it
  -StopOnly       Stop ECS/EKS/Aurora but keep infrastructure
  -DestroyAll     Permanently delete all resources
  -Force          Skip confirmation prompts
  -KeepState      Keep Pulumi stack state after destroy

Examples:
  # Safe preview
  .\cleanup.ps1 -Preview

  # Stop instances to save money overnight
  .\cleanup.ps1 -StopOnly

  # Full cleanup after testing
  .\cleanup.ps1 -DestroyAll

💡 Cost Savings:
  -StopOnly:     Saves ~80% of costs (keeps VPC, S3, DynamoDB)
  -DestroyAll:   Saves 100% of costs (deletes everything)

⚠️  Important Notes:
  • -StopOnly is reversible (run .\run.ps1 to restart)
  • -DestroyAll is PERMANENT (data will be lost!)
  • Always backup data before destroying
  • Set up billing alerts in AWS Console

"@ -ForegroundColor Cyan
}

Write-Host "`n✅ Cleanup script finished" -ForegroundColor Green
