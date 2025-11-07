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
    && rm -rf /var/lib/apt/lists/*

# Install Pulumi CLI
RUN curl -fsSL https://get.pulumi.com | sh
ENV PATH="/root/.pulumi/bin:${PATH}"

# Install dos2unix for line ending conversion
RUN apt-get update && apt-get install -y dos2unix && rm -rf /var/lib/apt/lists/*

# Copy project files first to get requirements
COPY . .

# Install Python dependencies from parent directory requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pulumi>=3.0.0 pulumi-aws>=6.0.0 pulumi-tls>=5.0.0

# Convert line endings and make plugin scripts executable
RUN dos2unix pulumi-plugins/pulumi-lambda && \
    dos2unix pulumi-plugins/pulumi-lambda.py && \
    dos2unix pulumi-plugins/pulumi-lambda-down && \
    dos2unix pulumi-plugins/pulumi-lambda-down.py && \
    chmod +x pulumi-plugins/pulumi-lambda && \
    chmod +x pulumi-plugins/pulumi-lambda.py && \
    chmod +x pulumi-plugins/pulumi-lambda-down && \
    chmod +x pulumi-plugins/pulumi-lambda-down.py && \
    cp pulumi-plugins/pulumi-lambda /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-lambda.py /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-lambda-down /usr/local/bin/ && \
    cp pulumi-plugins/pulumi-lambda-down.py /usr/local/bin/


# Verify Pulumi installation
RUN pulumi version

# Configure Pulumi to use local backend
RUN pulumi login --local

# Default command - run pulumi-lambda with auto-approve
CMD ["pulumi-lambda", "--yes"]
