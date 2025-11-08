"""
Create baseline with CloudWatch metrics.
This captures both configuration AND performance baselines.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.boto3_detection import Boto3DriftDetector
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def main():
    """Create baseline with metrics."""
    print("=" * 60)
    print("🔍 Creating Baseline with CloudWatch Metrics")
    print("=" * 60)

    detector = Boto3DriftDetector()

    try:
        # Create baseline with metrics
        print(
            f"\n📊 Collecting infrastructure state for {settings.aws_account_id}/{settings.aws_region}..."
        )
        print("⏳ This may take a few minutes to collect CloudWatch metrics...\n")

        baseline = await detector.create_baseline(settings.aws_account_id, settings.aws_region)

        # Summary
        print("\n" + "=" * 60)
        print("✅ Baseline Created Successfully!")
        print("=" * 60)

        resources = baseline.get("resources", {})
        print(f"\n📦 Resources Captured:")
        for resource_type, items in resources.items():
            count = len(items) if isinstance(items, list) else 0
            print(f"  • {resource_type}: {count}")

            # Check if metrics were collected
            if items and isinstance(items, list):
                with_metrics = sum(1 for item in items if "metrics_baseline" in item)
                if with_metrics > 0:
                    print(f"    └─ {with_metrics} with CloudWatch metrics ✨")

        print(f"\n💾 Baseline saved to: {detector.baseline_file}")
        print("\n🎯 You can now run drift detection to compare against this baseline!")
        print("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"Failed to create baseline: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
