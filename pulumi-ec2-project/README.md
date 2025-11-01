## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.7+**: [Download Python](https://www.python.org/downloads/)
- **Pulumi CLI**: [Install Pulumi](https://www.pulumi.com/docs/get-started/install/)
- **AWS CLI**: [Install AWS CLI](https://aws.amazon.com/cli/) (optional, for credential configuration)
- **AWS Account**: With appropriate permissions to create EC2, VPC, and related resources

## Installation

### 1. Clone the Repository

```bash
cd pulumi-ec2-project
```

### 2. Set Up Python Virtual Environment

Create and activate a virtual environment:

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure AWS Credentials

Ensure your AWS credentials are configured. You can do this in several ways:

**Option 1: Using AWS CLI**
```bash
aws configure
```

**Option 2: Using Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
```

### 5. Configure Pulumi

Initialize your Pulumi stack (if not already done):

```bash
pulumi login  # Login to Pulumi Cloud or use local backend
pulumi stack select dev  # Select the 'dev' stack or create a new one
```

### 6. Install Custom Plugins

The project includes custom CLI tools for easier management:

**On Linux/macOS:**
```bash
chmod +x install.sh
./install.sh
```

This will install:
- `pulumi-ec2`: Deploy infrastructure and SSH into the instance
- `pulumi-ec2-down`: Destroy the infrastructure