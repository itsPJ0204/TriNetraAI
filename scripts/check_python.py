"""Small Phase 1 check that reports the Python interpreter in use."""

import sys


def main() -> None:
    print(f"Python is available: {sys.executable}")
    print(f"Version: {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
