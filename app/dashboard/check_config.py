"""Configuration checker for auto-scheduler."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytz


def check_config():
    """Check auto-scheduler configuration."""
    print("\n" + "=" * 80)
    print("🔍 AUTO-SCHEDULER CONFIGURATION CHECKER")
    print("=" * 80 + "\n")

    # File paths
    config_file = Path(__file__).parent / "drift_config.json"
    status_file = Path(__file__).parent / "auto_scan_status.json"
    results_file = Path(__file__).parent / "latest_auto_scan.json"

    # Timezone
    utc_plus_7 = pytz.timezone("Asia/Bangkok")
    now = datetime.now(utc_plus_7)

    print(f"📅 Current Time (UTC+7): {now.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Check config file
    print("1️⃣  CONFIG FILE")
    print("-" * 80)
    if config_file.exists():
        print(f"✅ File exists: {config_file}")
        try:
            with open(config_file) as f:
                config = json.load(f)
            print("✅ Valid JSON format")
            print("\n📋 Configuration:")
            print(f"   Auto-scan enabled: {config.get('auto_scan_enabled', False)}")
            print(f"   Schedule: {config.get('scan_schedule', 'not set')}")
            print(f"   Accounts: {config.get('auto_scan_accounts', [])}")
            print(f"   Regions: {config.get('auto_scan_regions', [])}")
            print(f"   Resource types: {len(config.get('auto_scan_resource_types', []))} types")

            # Validate schedule
            schedule = config.get("scan_schedule", "hourly")
            valid_schedules = [
                "1min",
                "15min",
                "30min",
                "hourly",
                "6hours",
                "12hours",
                "daily",
                "weekly",
            ]
            if schedule in valid_schedules:
                print(f"   ✅ Valid schedule: {schedule}")
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
                interval = intervals[schedule]
                print(f"   📅 Interval: {interval}")
            else:
                print(f"   ❌ Invalid schedule: {schedule}")

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading config: {e}")
    else:
        print(f"❌ File not found: {config_file}")

    # Check status file
    print("\n2️⃣  STATUS FILE")
    print("-" * 80)
    if status_file.exists():
        print(f"✅ File exists: {status_file}")
        try:
            with open(status_file) as f:
                status = json.load(f)
            print("✅ Valid JSON format")
            print("\n📋 Status:")
            last_scan = status.get("last_scan")
            if last_scan:
                last_scan_dt = datetime.fromisoformat(last_scan)
                print(f"   Last scan: {last_scan_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Status: {status.get('last_scan_status', 'unknown')}")
                print(f"   Drift count: {status.get('drift_count', 0)}")

                # Calculate next scan
                if config_file.exists():
                    with open(config_file) as f:
                        config = json.load(f)
                    schedule = config.get("scan_schedule", "hourly")
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
                    interval = intervals.get(schedule, timedelta(hours=1))
                    next_scan = last_scan_dt + interval
                    time_until = (next_scan - now).total_seconds()
                    print(f"   Next scan: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")
                    if time_until > 0:
                        print(f"   ⏳ Time until next scan: {int(time_until)}s")
                    else:
                        print(f"   ⚠️  Next scan is overdue by {int(abs(time_until))}s")
            else:
                print("   📝 No previous scan recorded")

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading status: {e}")
    else:
        print(f"📝 File not found: {status_file}")
        print("   (This is normal if no scan has run yet)")

    # Check results file
    print("\n3️⃣  RESULTS FILE")
    print("-" * 80)
    if results_file.exists():
        print(f"✅ File exists: {results_file}")
        try:
            with open(results_file) as f:
                results = json.load(f)
            print("✅ Valid JSON format")
            print("\n📋 Latest Results:")
            print(f"   Scan time: {results.get('scan_time', 'unknown')}")
            print(f"   Status: {results.get('status', 'unknown')}")
            print(f"   Drift count: {results.get('drift_count', 0)}")
            if results.get("error"):
                print(f"   ❌ Error: {results.get('error')}")

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading results: {e}")
    else:
        print(f"📝 File not found: {results_file}")
        print("   (This is normal if no scan has completed yet)")

    # Summary
    print("\n" + "=" * 80)
    print("✅ CONFIGURATION CHECK COMPLETE")
    print("=" * 80)

    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        if config.get("auto_scan_enabled"):
            print("\n✅ Auto-scan is ENABLED and configured")
            print(f"   Schedule: {config.get('scan_schedule', 'not set')}")
            print("\n🚀 To start the scheduler, run:")
            print("   python app/dashboard/auto_scheduler.py")
        else:
            print("\n⚠️  Auto-scan is DISABLED")
            print("   Enable it in the Streamlit dashboard to activate scheduling")
    else:
        print("\n⚠️  No configuration found")
        print("   Configure auto-scan in the Streamlit dashboard first")

    print()


if __name__ == "__main__":
    check_config()
