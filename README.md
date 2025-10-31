# DriftGuards - AWS IaC Drift Analyzer

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

**DriftGuards** is an intelligent AWS Infrastructure-as-Code (IaC) drift detection and remediation system that combines multi-agent AI workflows with comprehensive AWS resource monitoring.

## 🎯 Key Features

- **Continuous Drift Detection**: Automated hourly scans using Terraform and driftctl
- **AI-Powered Analysis**: Context-aware explanations using AWS Bedrock (Claude 3)
- **Multi-Agent Architecture**: Specialized LangGraph agents for detection, analysis, and remediation
- **Comprehensive Metrics**: CloudWatch performance, Config compliance, and Cost Explorer data
- **Policy-as-Code**: Proactive drift prevention using OPA and AWS Config Rules
- **Automated Remediation**: Safe, audited, and reversible fixes with rollback capabilities
- **Interactive Dashboard**: Streamlit-based UI for visualization and management

## 📋 Prerequisites

- Python 3.11+
- AWS Account with appropriate permissions
- Terraform installed
- driftctl installed
- AWS Bedrock access (Claude 3 model)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/driftguards.git
cd driftguards
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials and configuration
# On Windows PowerShell:
Copy-Item .env.example .env
```

### 3. Install Dependencies

Using `uv` (recommended):
```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

Or using `pip`:
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the Application

Start the API server:
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start the Streamlit dashboard (in another terminal):
```powershell
streamlit run frontend/app.py
```

### 5. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **Health Check**: http://localhost:8000/health

## 📦 Project Structure

```
driftguards/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration management
│   ├── agents/                    # LangGraph agents
│   │   ├── detection.py           # Drift detection agent
│   │   ├── metrics_collector.py   # Metrics collection agent
│   │   ├── ai_analyzer.py         # AI analysis agent
│   │   ├── policy_validator.py    # Policy validation agent
│   │   ├── alert_engine.py        # Alert engine agent
│   │   └── remediation.py         # Remediation agent
│   ├── workflows/                 # LangGraph workflows
│   │   └── drift_workflow.py      # Main drift workflow
│   ├── models/                    # Data models
│   │   ├── drift.py               # Drift models
│   │   ├── metrics.py             # Metrics models
│   │   └── analysis.py            # Analysis models
│   ├── services/                  # AWS service clients
│   │   ├── terraform.py           # Terraform operations
│   │   ├── driftctl.py            # driftctl integration
│   │   ├── aws_client.py          # AWS SDK wrappers
│   │   └── bedrock.py             # Bedrock LLM client
│   ├── storage/                   # Data storage
│   │   ├── sqlite.py              # SQLite for dev
│   │   └── dynamodb.py            # DynamoDB for prod
│   ├── api/                       # API routes
│   │   └── v1/                    # API v1
│   └── utils/                     # Utilities
├── frontend/                      # Streamlit dashboard
│   ├── app.py                     # Main app
│   └── pages/                     # Dashboard pages
├── tests/                         # Tests
├── deployment/                    # Deployment configs
├── docs/                          # Documentation
├── pyproject.toml                 # Project configuration
├── requirements.txt               # Dependencies
├── .env.example                   # Environment template
├── Dockerfile                     # Docker configuration
├── DESIGN.md                      # Design document
└── README.md                      # This file
```

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_TEMPERATURE=0.1

# Scanning Configuration
SCAN_INTERVAL_HOURS=1
SCAN_RESOURCE_TYPES=aws_instance,aws_s3_bucket,aws_rds_instance

# Remediation Configuration
REMEDIATION_AUTO_APPROVE=false
REMEDIATION_BACKUP_ENABLED=true
REMEDIATION_DRY_RUN=true
```

See `.env.example` for all available configuration options.

## 📚 API Documentation

### Scan for Drift

```bash
POST /api/v1/scan
{
  "accounts": ["123456789012"],
  "regions": ["us-east-1"],
  "resource_types": ["aws_instance", "aws_s3_bucket"]
}
```

### List Drifts

```bash
GET /api/v1/drifts?severity=high&status=open&limit=50
```

### Get Drift Analysis

```bash
GET /api/v1/drifts/{drift_id}/analysis
```

### Remediate Drift

```bash
POST /api/v1/drifts/{drift_id}/remediate
{
  "action": "update_terraform",
  "confirm": true,
  "dry_run": false
}
```

## 🧪 Testing

Run tests:
```powershell
pytest
```

Run tests with coverage:
```powershell
pytest --cov=app --cov-report=html
```

## 🐳 Docker Deployment

Build and run with Docker:

```powershell
docker build -t driftguards:latest .
docker run -p 8000:8000 --env-file .env driftguards:latest
```

Using Docker Compose:

```powershell
docker-compose up -d
```

## 📊 Monitoring

The application exposes metrics via:

- **Health Check**: `/health`
- **CloudWatch Metrics**: Custom namespace `DriftGuards`
- **Structured Logs**: JSON format for production
- **AWS X-Ray**: Distributed tracing (when enabled)

## 🔒 Security

- **Authentication**: API key authentication (OAuth2/JWT support)
- **IAM Roles**: Uses AWS IAM roles for service access
- **Secrets Management**: AWS Secrets Manager integration
- **Audit Logging**: All actions logged to DynamoDB/S3

## 🛠️ Development

Install development dependencies:

```powershell
pip install -e ".[dev]"
```

Run linters:

```powershell
black .
ruff check .
mypy app/
```

## 📖 Documentation

- [Design Document](DESIGN.md) - Comprehensive architecture and design
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

## 🗺️ Roadmap

### Phase 1: MVP (Weeks 1-4) - IN PROGRESS
- [x] Project structure and configuration
- [x] Core data models
- [x] AWS service clients
- [ ] Detection agent
- [ ] Metrics collector agent
- [ ] Basic AI analyzer
- [ ] FastAPI endpoints
- [ ] Streamlit dashboard
- [ ] Docker configuration

### Phase 2: Enhanced Intelligence (Weeks 5-6)
- [ ] driftctl integration
- [ ] AWS Config enrichment
- [ ] Cost Explorer integration
- [ ] Policy validator agent
- [ ] Multi-channel alerts

### Phase 3: Automated Remediation (Weeks 7-8)
- [ ] Full remediation agent
- [ ] Terraform patch generation
- [ ] Backup and rollback
- [ ] Pre-flight safety checks

### Phase 4: Production Readiness (Weeks 9-10)
- [ ] ECS Fargate deployment
- [ ] EventBridge scheduling
- [ ] Security hardening
- [ ] Load testing

### Phase 5: Advanced Features (Weeks 11-12)
- [ ] Cross-account support
- [ ] Multi-region scanning
- [ ] Advanced analytics
- [ ] Webhook integrations

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 📧 Contact

- **Repository**: [CloudDrift-AI](https://github.com/hailn0472/CloudDrift-AI)
- **Issues**: [GitHub Issues](https://github.com/hailn0472/CloudDrift-AI/issues)

## 🙏 Acknowledgments

- [Terraform](https://www.terraform.io/) - Infrastructure as Code
- [driftctl](https://github.com/snyk/driftctl) - Drift detection
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [AWS Bedrock](https://aws.amazon.com/bedrock/) - AI/ML services
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Streamlit](https://streamlit.io/) - Data apps framework

---

**Built with ❤️ for AWS Infrastructure Management**