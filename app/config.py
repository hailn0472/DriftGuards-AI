"""Application configuration management."""

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DriftGuards"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    api_key: str = Field(..., min_length=32)

    # AWS
    aws_region: str = "us-east-1"
    aws_account_id: str = Field(..., pattern=r"^\d{12}$")
    aws_access_key_id: str = Field(default="", description="Optional if using IAM roles")
    aws_secret_access_key: str = Field(default="", description="Optional if using IAM roles")
    aws_session_token: str = ""

    # AWS Bedrock
    bedrock_model_id: str = "us.anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_region: str = "us-east-1"
    bedrock_max_tokens: int = 4096
    bedrock_temperature: float = Field(default=0.1, ge=0.0, le=1.0)

    # Terraform
    terraform_binary_path: str = "/usr/local/bin/terraform"
    terraform_state_backend: Literal["local", "s3", "terraform-cloud"] = "s3"
    terraform_state_bucket: str = "driftguards-terraform-state"
    terraform_state_key: str = "terraform.tfstate"
    terraform_working_dir: str = "/app/terraform"

    # driftctl
    driftctl_binary_path: str = "/usr/local/bin/driftctl"
    driftctl_cache_dir: str = "/tmp/driftctl-cache"

    # Database
    database_url: str = "sqlite+aiosqlite:///./driftguards.db"

    # DynamoDB (for production)
    dynamodb_table_drifts: str = "DriftGuardsRecords"
    dynamodb_table_remediations: str = "DriftGuardsRemediations"
    dynamodb_table_policies: str = "DriftGuardsPolicies"

    # S3
    s3_bucket_artifacts: str = "driftguards-artifacts"
    s3_bucket_logs: str = "driftguards-logs"
    s3_prefix_reports: str = "drift-reports/"
    s3_prefix_backups: str = "backups/"
    s3_prefix_terraform_states: str = "terraform-states/"

    # CloudWatch
    cloudwatch_metrics_namespace: str = "DriftGuards"
    cloudwatch_log_group: str = "/driftguards/app"
    cloudwatch_lookback_hours: int = 24

    # AWS Config
    config_lookback_days: int = 7

    # Cost Explorer
    cost_explorer_lookback_days: int = 30

    # Alerts
    alert_email_from: str = "alerts@driftguards.io"
    alert_email_to: str = "team@driftguards.io"

    # SMTP (Simple Email)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # OPA
    opa_policy_dir: str = "/app/app/policies/opa"
    opa_enabled: bool = True

    # Scanning
    scan_interval_hours: int = 1
    scan_parallel_workers: int = 5
    scan_timeout_minutes: int = 30
    scan_resource_types: str = "aws_instance,aws_s3_bucket,aws_rds_instance,aws_lambda_function"

    @property
    def scan_resource_types_list(self) -> List[str]:
        """Get scan resource types as a list."""
        return [t.strip() for t in self.scan_resource_types.split(",") if t.strip()]

    # Remediation
    remediation_auto_approve: bool = False
    remediation_backup_enabled: bool = True
    remediation_dry_run: bool = True
    remediation_timeout_minutes: int = 15

    # Policy
    policy_enforcement_level: Literal["ignore", "warn", "block"] = "warn"
    policy_auto_remediate: bool = False

    # Security
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    cache_backend: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/0"

    # Monitoring
    xray_enabled: bool = False
    metrics_enabled: bool = True

    # Frontend
    streamlit_port: int = 8501
    streamlit_server_address: str = "0.0.0.0"

    # GitHub (for GitOps features)
    github_token: str = ""
    github_repo_owner: str = ""
    github_repo_name: str = ""
    github_base_branch: str = "main"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v_upper

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    @property
    def use_dynamodb(self) -> bool:
        """Check if DynamoDB should be used instead of SQLite."""
        return self.is_production and not self.database_url.startswith("sqlite")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
