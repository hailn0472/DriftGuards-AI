# DriftGuards-AI Documentation

Welcome to the DriftGuards-AI documentation hub. This folder contains comprehensive documentation organized by category.

## 📚 Documentation Structure

### 🏗️ Architecture
High-level system design and architectural decisions.

- **[Architecture Diagram](architecture/ARCHITECTURE_DIAGRAM.md)** - Visual overview of system components
- **[System Design](architecture/DESIGN.md)** - Detailed design document
- **[Hybrid Approach Guide](architecture/HYBRID_APPROACH_GUIDE.md)** - Pulumi + Boto3 hybrid strategy

### 📖 User Guides
Step-by-step guides for using DriftGuards-AI.

- **[Dashboard Guide](guides/DASHBOARD_GUIDE.md)** - How to use the Streamlit dashboard
- **[Dashboard Usage](guides/DASHBOARD_USAGE.md)** - Detailed dashboard features
- **[Resource Inventory Guide](guides/RESOURCE_INVENTORY_GUIDE.md)** - Managing resource inventory
- **[Deployment Guide](guides/DEPLOYMENT_GUIDE.md)** - Deployment instructions

### 🔧 Implementation Details
Technical implementation documentation for developers.

- **[Agents Implementation](implementation/AGENTS_IMPLEMENTATION.md)** - AI agents architecture
- **[Implementation Summary](implementation/IMPLEMENTATION_SUMMARY.md)** - Overall implementation overview
- **[How Drift Detection Works](implementation/HOW_DRIFT_DETECTION_WORKS.md)** - Deep dive into drift detection
- **[Drift Detection Examples](implementation/DRIFT_DETECTION_EXAMPLES.md)** - Real-world examples

### ⚡ Features
Documentation for specific features.

- **[Custom Cron Feature](features/CUSTOM_CRON_FEATURE.md)** - Scheduled drift detection
- **[Selective Revert Example](features/SELECTIVE_REVERT_EXAMPLE.md)** - Field-level revert examples
- **[Selective Revert UI](features/SELECTIVE_REVERT_UI.md)** - UI for selective revert

### 🗄️ Legacy Documentation
Archived documentation for historical reference.

- **[Pulumi Fix](legacy/PULUMI_FIX.md)** - Historical Pulumi issues
- **[Pulumi Terraform Verification](legacy/PULUMI_TERRAFORM_VERIFICATION.md)** - Migration notes
- **[Terraform Replacement Complete](legacy/TERRAFORM_REPLACEMENT_COMPLETE.md)** - Legacy Terraform approach

---

## 🚀 Quick Start

New to DriftGuards-AI? Start here:

1. Read the **[System Design](architecture/DESIGN.md)** to understand the overall architecture
2. Follow the **[Deployment Guide](guides/DEPLOYMENT_GUIDE.md)** to set up the system
3. Learn how to use the **[Dashboard](guides/DASHBOARD_GUIDE.md)**
4. Understand **[How Drift Detection Works](implementation/HOW_DRIFT_DETECTION_WORKS.md)**

---

## 📝 Contributing to Documentation

When adding new documentation:

- Place architecture docs in `architecture/`
- Place user guides in `guides/`
- Place implementation details in `implementation/`
- Place feature docs in `features/`
- Move outdated docs to `legacy/`

Keep documentation up-to-date with code changes!
