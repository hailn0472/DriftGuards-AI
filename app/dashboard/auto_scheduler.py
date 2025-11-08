"""Background Auto-Scan Scheduler for DriftGuards AI.

This script runs independently of the Streamlit dashboard and executes
scheduled scans based on the configuration file.
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytz

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()  # Load AWS credentials from .env

from app.models.drift import ScanRequest
from app.workflows import DriftGuardsWorkflow


class AutoScheduler:
    """Background scheduler for automatic drift scans."""

    def __init__(self):
        """Initialize the scheduler."""
        self.config_file = Path(__file__).parent / "drift_config.json"
        self.status_file = Path(__file__).parent / "auto_scan_status.json"
        self.utc_plus_7 = pytz.timezone("Asia/Bangkok")
        self.running = False

    def load_config(self) -> dict:
        """Load configuration from file."""
        print(f"🔍 Checking config file: {self.config_file}")
        if self.config_file.exists():
            print(f"✅ Config file found")
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                print(f"✅ Config loaded successfully")
                print(f"   Auto-scan enabled: {config.get('auto_scan_enabled', False)}")
                print(f"   Schedule: {config.get('scan_schedule', 'not set')}")
                print(f"   Accounts: {config.get('auto_scan_accounts', [])}")
                print(f"   Regions: {config.get('auto_scan_regions', [])}")
                print(f"   Resource types: {len(config.get('auto_scan_resource_types', []))} types")
                return config
            except Exception as e:
                print(f"❌ Error loading config: {e}")
                return {}
        else:
            print(f"❌ Config file not found!")
            return {}

    def load_status(self) -> dict:
        """Load scan status from file."""
        print(f"🔍 Checking status file: {self.status_file}")
        if self.status_file.exists():
            try:
                with open(self.status_file) as f:
                    data = json.load(f)
                    # Convert ISO timestamp back to datetime
                    if data.get("last_scan"):
                        data["last_scan"] = datetime.fromisoformat(data["last_scan"])
                    print(f"✅ Status loaded: Last scan at {data.get('last_scan', 'N/A')}")
                    return data
            except Exception as e:
                print(f"❌ Error loading status: {e}")
                return {}
        else:
            print("📝 No status file found - this will be the first scan")
            return {}

    def save_status(self, status: dict):
        """Save scan status to file."""
        try:
            # Convert datetime to ISO format for JSON
            status_copy = status.copy()
            if status_copy.get("last_scan"):
                if isinstance(status_copy["last_scan"], datetime):
                    status_copy["last_scan"] = status_copy["last_scan"].isoformat()

            with open(self.status_file, "w") as f:
                json.dump(status_copy, f, indent=2)
            print(f"✅ Status saved to: {self.status_file}")
        except Exception as e:
            print(f"❌ Error saving status: {e}")

    def get_schedule_interval(self, schedule: str) -> timedelta:
        """Get timedelta for schedule."""
        intervals = {
            "1min": timedelta(minutes=1),
            "15min": timedelta(minutes=15),
            "30min": timedelta(minutes=30),
            "hourly": timedelta(hours=1),
            "6hours": timedelta(hours=6),
            "12hours": timedelta(hours=12),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }
        return intervals.get(schedule, timedelta(hours=1))

    async def run_scan(self, accounts: list, regions: list, resource_types: list) -> dict:
        """Execute a drift scan."""
        print(f"\n{'=' * 80}")
        print(
            f"🔍 Starting Auto-Scan at {datetime.now(self.utc_plus_7).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"{'=' * 80}")
        print(f"📋 Scan Configuration:")
        print(f"   Accounts: {accounts}")
        print(f"   Regions: {regions}")
        print(f"   Resource Types: {resource_types}")
        print(f"{'=' * 80}\n")

        try:
            # Create workflow
            workflow = DriftGuardsWorkflow()

            # Create scan request
            scan_request = ScanRequest(
                accounts=accounts,
                regions=regions,
                resource_types=resource_types,
                force_refresh=False,
            )

            print("⚙️  Running drift detection workflow...")
            # Run workflow
            final_state = await workflow.run(scan_request)

            # Prepare results
            drifts = final_state.get("drift_records", [])
            analyses = final_state.get("ai_analysis", [])
            violations = final_state.get("policy_violations", [])

            # Convert Pydantic models to dicts for JSON serialization
            drifts_dict = [d.dict() if hasattr(d, "dict") else d for d in drifts]
            analyses_dict = [a.dict() if hasattr(a, "dict") else a for a in analyses]
            violations_dict = [v.dict() if hasattr(v, "dict") else v for v in violations]

            result = {
                "scan_time": datetime.now(self.utc_plus_7).isoformat(),
                "drift_count": len(drifts),
                "drifts": drifts_dict,
                "analyses": analyses_dict,
                "violations": violations_dict,
                "status": "success",
            }

            print("\n✅ Scan completed successfully!")
            print(f"   Drifts found: {len(drifts)}")
            print(f"   Analyses: {len(analyses)}")
            print(f"   Violations: {len(violations)}\n")

            return result

        except KeyboardInterrupt:
            print("\n⚠️  Scan cancelled by user")
            raise
        except Exception as e:
            print(f"\n❌ Scan failed: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback

            print(f"   Traceback:\n{traceback.format_exc()}")
            return {
                "scan_time": datetime.now(self.utc_plus_7).isoformat(),
                "drift_count": 0,
                "drifts": [],
                "analyses": [],
                "violations": [],
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def save_scan_results(self, results: dict):
        """Save scan results to a file that Streamlit can load."""
        results_file = Path(__file__).parent / "latest_auto_scan.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Results saved to: {results_file}")

    async def run_scheduler(self):
        """Main scheduler loop."""
        self.running = True
        print("\n" + "=" * 80)
        print("🤖 DriftGuards Auto-Scan Scheduler Started")
        print("=" * 80)
        print(f"📁 Config file: {self.config_file}")
        print(f"📁 Status file: {self.status_file}")
        print(f"⏰ Timezone: UTC+7 (Asia/Bangkok)")
        print("=" * 80 + "\n")

        while self.running:
            try:
                # Load current config
                config = self.load_config()

                # Check if auto-scan is enabled
                if not config.get("auto_scan_enabled", False):
                    print("⏸️  Auto-scan is disabled. Waiting...")
                    await asyncio.sleep(30)  # Check every 30 seconds
                    continue

                # Load status
                status = self.load_status()

                # Get schedule
                schedule = config.get("scan_schedule", "hourly")
                interval = self.get_schedule_interval(schedule)

                # Get scan parameters
                accounts = config.get("auto_scan_accounts", ["961639320333"])
                regions = config.get("auto_scan_regions", ["ap-southeast-1"])
                resource_types = config.get(
                    "auto_scan_resource_types",
                    [
                        "ec2_instances",
                        "rds_instances",
                        "rds_clusters",
                        "s3_buckets",
                        "dynamodb_tables",
                        "sqs_queues",
                        "lambda_functions",
                        "ecs_clusters",
                        "eks_clusters",
                    ],
                )

                # Check if it's time to scan
                now = datetime.now(self.utc_plus_7)
                last_scan = status.get("last_scan")

                if last_scan:
                    # Make timezone-aware if needed
                    if isinstance(last_scan, str):
                        last_scan = datetime.fromisoformat(last_scan)
                    if last_scan.tzinfo is None:
                        last_scan = self.utc_plus_7.localize(last_scan)

                    next_scan = last_scan + interval
                    time_until_scan = (next_scan - now).total_seconds()

                    print(f"⏰ Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"📅 Schedule: {schedule} (every {interval})")
                    print(f"🕐 Last scan: {last_scan.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"🕑 Next scan: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")

                    if time_until_scan > 0:
                        # Format time remaining
                        if time_until_scan < 60:
                            time_str = f"{int(time_until_scan)}s"
                        elif time_until_scan < 3600:
                            mins = int(time_until_scan // 60)
                            secs = int(time_until_scan % 60)
                            time_str = f"{mins}m {secs}s"
                        else:
                            hours = int(time_until_scan // 3600)
                            mins = int((time_until_scan % 3600) // 60)
                            time_str = f"{hours}h {mins}m"

                        print(f"⏳ Time until next scan: {time_str}")
                        print(f"💤 Sleeping...\n")

                        # Sleep until next scan (or check every minute)
                        sleep_time = min(time_until_scan, 60)
                        await asyncio.sleep(sleep_time)
                        continue
                else:
                    print("🆕 No previous scan found. Running first scan...")

                # Time to scan!
                print(f"\n{'=' * 80}")
                print(f"🚀 TRIGGERING AUTO-SCAN")
                print(f"{'=' * 80}")

                # Run the scan
                results = await self.run_scan(accounts, regions, resource_types)

                # Save results for Streamlit to load
                self.save_scan_results(results)

                # Update status
                status["last_scan"] = now
                status["last_scan_status"] = results["status"]
                status["drift_count"] = results["drift_count"]
                self.save_status(status)

                print(f"{'=' * 80}\n")

            except Exception as e:
                print(f"\n❌ Scheduler error: {e}\n")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        print("\n🛑 Scheduler stopped\n")


async def main():
    """Main entry point."""
    scheduler = AutoScheduler()

    try:
        await scheduler.run_scheduler()
    except KeyboardInterrupt:
        print("\n\n⚠️  Received interrupt signal...")
        scheduler.stop()
        print("👋 Goodbye!\n")


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                                                            ║")
    print("║       DriftGuards AI - Auto-Scan Background Scheduler      ║")
    print("║                                                            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("\n")

    asyncio.run(main())
