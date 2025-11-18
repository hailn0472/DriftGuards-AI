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
    unzip \
    ca-certificates \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install Pulumi CLI
RUN curl -fsSL https://get.pulumi.com | sh
ENV PATH="/root/.pulumi/bin:${PATH}"

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

# Copy shared requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY ./pulumi-sqs-deployment .

# Convert line endings and make plugin scripts executable
RUN dos2unix pulumi-plugins/pulumi-sqs && \
    dos2unix pulumi-plugins/pulumi-sqs.py && \
    dos2unix pulumi-plugins/pulumi-sqs-down && \
    dos2unix pulumi-plugins/pulumi-sqs-down.py && \
    chmod +x pulumi-plugins/pulumi-sqs && \
    chmod +x pulumi-plugins/pulumi-sqs.py && \
    chmod +x pulumi-plugins/pulumi-sqs-down && \
    chmod +x pulumi-plugins/pulumi-sqs-down.py && \
    cp pulumi-plugins/pulumi-sqs /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-sqs.py /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-sqs-down /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-sqs-down.py /usr/local/bin/

# Verify installations
RUN pulumi version && aws --version

# Configure Pulumi to use local backend
RUN pulumi login --local

# Default command - run pulumi-sqs with auto-approve
CMD ["pulumi-sqs", "--yes"]