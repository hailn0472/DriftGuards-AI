# ✅ Pulumi E-commerce Infrastructure - Deployment Ready!

## Current Status

All configuration errors have been fixed! The Pulumi preview shows **68 resources** ready to be created.

## What Will Be Created

### Core Infrastructure (24 resources)
- **VPC** with public/private subnets across 2 availability zones
- **Internet Gateway** and **2 NAT Gateways**
- **Route Tables** and associations
- **Elastic IPs** for NAT Gateways

### EKS Cluster (30+ resources)
- **EKS Control Plane** (Kubernetes v1.x)
- **EKS Node Group** with t3.medium instances (2-3 nodes)
- **IAM Roles** and policies for EKS
- **Security Groups** for cluster and nodes
- **VPC CNI** plugin for networking

### ECS Cluster (5 resources)
- **ECS Fargate Cluster** for order processing
- **Task Definition** with Instana agent sidecar
- **IAM Execution Role**
- **CloudWatch Log Groups** (2x)

### Databases
- **Aurora MySQL Cluster** (RDS)
  - 1x db.r5.large instance (~$200-400/month)
- **DynamoDB Table** (session storage, pay-per-request)

### Messaging & Storage
- **S3 Bucket** for static assets
- **SQS Queue** for order processing
- **MSK Kafka Cluster** (3 brokers, kafka.m5.large) (~$300-400/month)

### Monitoring
- **Instana Agent DaemonSet** on EKS
- **Instana Agent Sidecar** on ECS
- **Kubernetes Secret** for Instana key

## Fixed Issues

1. ✅ Renamed `pulumi.py` → `__main__.py` (Pulumi requirement)
2. ✅ Fixed config schema: `default` → `value` for provider configs
3. ✅ Fixed config reading: Using namespaced Config objects
4. ✅ Fixed Output concatenation: Using `Output.all().apply()`
5. ✅ Fixed JSON serialization: Wrapped Output objects properly
6. ✅ Added missing `engine` property to Aurora ClusterInstance

## Deployment Commands

### Preview (Safe - No Charges)
```powershell
cd d:\GitHub\SelfStudy\CloudDrift-AI\data-example
pulumi preview --diff
```

### Deploy Everything
```powershell
pulumi up
# Review the changes and type "yes" to confirm
```

### Deploy Using Quick Script
```powershell
.\run.ps1 -Deploy
```

## Cost Estimates

| Service | Instance Type | Estimated Monthly Cost |
|---------|--------------|------------------------|
| EKS Control Plane | - | $75 |
| EKS Worker Nodes | 2x t3.medium | $60 |
| Aurora MySQL | 1x db.r5.large | $200-400 |
| MSK Kafka | 3x kafka.m5.large | $300-400 |
| NAT Gateways | 2x | $65 |
| ECS Fargate | Variable | $20-50 |
| S3, DynamoDB, SQS | Pay-per-use | $5-20 |
| **Total** | | **$725-1,070/month** ⚠️

## Safety Recommendations

### Before Deploying
1. **Review costs** - This is an expensive infrastructure
2. **Set billing alerts** in AWS Console
3. **Use a test/dev AWS account** - NOT production
4. **Consider cheaper alternatives**:
   - Use t3.small for EKS nodes
   - Use Aurora Serverless v2 (cheaper)
   - Use MSK Serverless (cheaper)
   - Reduce to 1 NAT Gateway

### Cost-Optimized Configuration
Edit `__main__.py` to use cheaper resources:

```python
# EKS - Change from t3.medium to t3.small
instance_type="t3.small",
desired_capacity=1,  # Reduce from 2

# Aurora - Use smaller instance
instance_class="db.t3.medium",  # Instead of db.r5.large

# MSK - Use smaller brokers
"instance_type": "kafka.t3.small",  # Instead of kafka.m5.large
```

## After Deployment

### View Outputs
```powershell
pulumi stack output
```

You'll see:
- VPC ID
- EKS cluster name
- ECS cluster name
- Aurora endpoint
- S3 bucket name
- SQS queue URL
- MSK cluster ARN

### Get EKS Kubeconfig
```powershell
pulumi stack output kubeconfig > kubeconfig.yaml
$env:KUBECONFIG = "kubeconfig.yaml"
kubectl get nodes
kubectl get pods -n instana
```

### Test the Infrastructure
```powershell
# Check ECS task
aws ecs list-clusters
aws ecs list-tasks --cluster (pulumi stack output ecs_cluster_name)

# Check Aurora
aws rds describe-db-clusters

# Check MSK
aws kafka list-clusters
```

## Cleanup / Destroy

### Remove All Resources
```powershell
pulumi destroy
# Type "yes" to confirm
```

This will delete all 68 resources and stop all charges.

### Verify Cleanup
```powershell
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ecom-vpc*"
aws eks list-clusters
aws rds describe-db-clusters
```

## Troubleshooting

### Issue: "Rate exceeded" errors
**Solution**: AWS API rate limits. Wait 1-2 minutes and retry.

### Issue: "Service quota exceeded"
**Solution**: Your AWS account has limits. Request quota increases in AWS Console.

### Issue: EKS node group fails
**Solution**: Check IAM permissions. Ensure your user has EC2, EKS, IAM permissions.

### Issue: MSK cluster fails
**Solution**: MSK requires specific subnet configuration. Ensure VPC has correct subnets.

### Issue: Costs higher than expected
**Solution**: Run `pulumi destroy` immediately. Review the cost optimization section.

## Next Steps After Deployment

1. **Deploy your application** to EKS:
   ```bash
   kubectl apply -f your-app.yaml
   ```

2. **Configure Instana monitoring**:
   - Login to Instana dashboard
   - Verify agents are reporting
   - Set up alerts and dashboards

3. **Test the order processing**:
   - Send test orders to SQS queue
   - Verify ECS tasks process them
   - Check logs in CloudWatch

4. **Set up CI/CD**:
   - GitHub Actions or similar
   - Automated deployments to EKS
   - Automated testing

## Important Notes

- ⚠️ **This is a production-grade architecture** with high costs
- 💰 **Monitor your AWS billing daily** for the first week
- 🔒 **All secrets are stored in Pulumi state** (encrypted)
- 🌍 **Region**: ap-southeast-1 (Singapore)
- 📊 **Instana endpoint**: https://saas-ap-southeast-1.instana.io

## Support

If you encounter issues:
1. Check Pulumi logs: `pulumi logs`
2. Check AWS CloudWatch logs
3. Review Pulumi state: `pulumi stack`
4. Export stack for debugging: `pulumi stack export > stack.json`

---

**Ready to deploy?** Run `pulumi up` to create the infrastructure! 🚀
