"""Unified launcher for DriftGuards AI - Runs both Streamlit dashboard and auto-scheduler."""

import asyncio
import multiprocessing
import subprocess
import sys
import time
from pathlib import Path


def run_streamlit():
    """Run Streamlit dashboard in a separate process."""
    print("\n🌐 Starting Streamlit Dashboard...")
    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


def run_scheduler():
    """Run auto-scheduler in a separate process."""
    print("\n🤖 Starting Auto-Scheduler...")
    scheduler_path = Path(__file__).parent / "auto_scheduler.py"
    subprocess.run([sys.executable, str(scheduler_path)])


def main():
    """Launch both processes."""
    print("\n" + "=" * 80)
    print("🚀 DriftGuards AI - Unified Launcher")
    print("=" * 80)
    print("\nStarting both Streamlit Dashboard and Auto-Scheduler...")
    print("\nPress Ctrl+C to stop both processes\n")
    print("=" * 80 + "\n")

    # Create processes
    streamlit_process = multiprocessing.Process(target=run_streamlit, name="Streamlit")
    scheduler_process = multiprocessing.Process(target=run_scheduler, name="AutoScheduler")

    try:
        # Start both processes
        streamlit_process.start()
        time.sleep(2)  # Give Streamlit time to start
        scheduler_process.start()

        print("\n✅ Both services started successfully!")
        print("\n📊 Streamlit Dashboard: http://localhost:8501")
        print("🤖 Auto-Scheduler: Running in background")
        print("\nPress Ctrl+C to stop both services...\n")

        # Wait for both processes
        streamlit_process.join()
        scheduler_process.join()

    except KeyboardInterrupt:
        print("\n\n⚠️  Stopping services...")

        # Terminate both processes
        if streamlit_process.is_alive():
            print("  🛑 Stopping Streamlit...")
            streamlit_process.terminate()
            streamlit_process.join(timeout=5)

        if scheduler_process.is_alive():
            print("  🛑 Stopping Auto-Scheduler...")
            scheduler_process.terminate()
            scheduler_process.join(timeout=5)

        print("\n✅ All services stopped")
        print("👋 Goodbye!\n")


if __name__ == "__main__":
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
