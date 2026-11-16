#!/usr/bin/env python3
"""
AutoQuiz Platform Launcher
Runs server, test suite, UCP calculator, and sample generator.
"""

import sys
import argparse
from app.main import create_app
from tools.ucp_calculator import calculate_ucp
from sample_data.generate_samples import create_samples

def main():
    parser = argparse.ArgumentParser(description="AutoQuiz Platform Runner")
    parser.add_argument("--test", action="store_true", help="Run full automated test suite (TC-01 through TC-77)")
    parser.add_argument("--ucp", action="store_true", help="Run Use Case Point (UCP) Estimation Calculator")
    parser.add_argument("--samples", action="store_true", help="Generate sample course documents")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")

    args = parser.parse_args()

    if args.samples:
        print("[AutoQuiz] Generating sample datasets...")
        create_samples()
        return

    if args.ucp:
        print("[AutoQuiz] Executing UCP Estimation...")
        calculate_ucp()
        return

    if args.test:
        print("[AutoQuiz] Executing automated test suite for TC-01 through TC-77...")
        import pytest
        exit_code = pytest.main(["-v", "tests/test_suite_tc01_tc77.py"])
        sys.exit(exit_code)

    print(f"============================================================")
    print(f"  Starting AutoQuiz Server on http://localhost:{args.port}")
    print(f"  NIT Warangal - Computer Science & Engineering")
    print(f"============================================================")
    app = create_app()
    app.run(host=args.host, port=args.port, debug=False)

if __name__ == "__main__":
    main()

