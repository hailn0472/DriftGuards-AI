"""Setup script for development environment."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> None:
    """Run a command and print the result."""
    print(f"\n{'=' * 60}")
    print(f"🔧 {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        print(f"✅ {description} completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stderr)
        sys.exit(1)


def main() -> None:
    """Main setup function."""
    print("\n" + "=" * 60)
    print("🚀 DriftGuards Development Environment Setup")
    print("=" * 60)

    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        sys.exit(1)

    print(f"✅ Python version: {sys.version}")

    # Check if .env exists
    env_path = Path(".env")
    if not env_path.exists():
        print("\n⚠️  .env file not found")
        print("📝 Copying .env.example to .env")
        env_example = Path(".env.example")
        if env_example.exists():
            env_example.rename(".env")
            print("✅ Created .env file")
            print("⚠️  Please edit .env with your AWS credentials")
        else:
            print("❌ .env.example not found")
            sys.exit(1)
    else:
        print("✅ .env file exists")

    # Install dependencies
    print("\n" + "=" * 60)
    print("📦 Installing dependencies...")
    print("=" * 60)

    if os.name == "nt":  # Windows
        venv_python = r".venv\Scripts\python.exe"
        venv_activate = r".venv\Scripts\activate"
    else:  # Unix/Mac
        venv_python = ".venv/bin/python"
        venv_activate = "source .venv/bin/activate"

    # Check if virtual environment exists
    if not Path(venv_python).exists():
        print("Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", ".venv"], "Creating venv")

    # Install dependencies
    run_command(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        "Upgrading pip",
    )

    run_command(
        [venv_python, "-m", "pip", "install", "-r", "requirements.txt"],
        "Installing requirements",
    )

    # Create necessary directories
    print("\n" + "=" * 60)
    print("📁 Creating project directories...")
    print("=" * 60)

    directories = [
        "logs",
        "artifacts",
        "backups",
        "drift-reports",
        "terraform-states",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path}")

    # Final instructions
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print(f"\n1. Activate virtual environment:")
    print(f"   {venv_activate}")
    print("\n2. Edit .env with your AWS credentials")
    print("\n3. Test the setup:")
    print("   python scripts/test_setup.py")
    print("\n4. Run the application:")
    print("   python -m uvicorn app.main:app --reload")
    print("\n5. Visit the API docs:")
    print("   http://localhost:8000/docs")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
