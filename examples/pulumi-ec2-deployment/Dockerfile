# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /pulumi-project

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PULUMI_SKIP_UPDATE_CHECK=true \
    PULUMI_CONFIG_PASSPHRASE="" \
    PULUMI_HOME=/pulumi-project/.pulumi

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    dos2unix \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Pulumi CLI
RUN curl -fsSL https://get.pulumi.com | sh
ENV PATH="/root/.pulumi/bin:${PATH}"

# Copy shared requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY ./pulumi-ec2-deployment .

# Convert line endings and make plugin scripts executable
RUN dos2unix pulumi-plugins/pulumi-ec2 && \
    dos2unix pulumi-plugins/pulumi-ec2.py && \
    dos2unix pulumi-plugins/pulumi-ec2-down && \
    dos2unix pulumi-plugins/pulumi-ec2-down.py && \
    chmod +x pulumi-plugins/pulumi-ec2 && \
    chmod +x pulumi-plugins/pulumi-ec2.py && \
    chmod +x pulumi-plugins/pulumi-ec2-down && \
    chmod +x pulumi-plugins/pulumi-ec2-down.py && \
    cp pulumi-plugins/pulumi-ec2 /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-ec2.py /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-ec2-down /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-ec2-down.py /usr/local/bin/

# Verify Pulumi installation
RUN pulumi version

# Configure Pulumi to use local backend
RUN pulumi login --local

# Default command - run pulumi-ec2 with auto-approve
CMD ["pulumi-ec2", "--yes"]
