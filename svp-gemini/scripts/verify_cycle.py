import subprocess
import sys
import os

def run_verification(unit_name, stage):
    test_path = f"tests/test_{unit_name}.py"
    if stage == "red":
        # Ensure test exists
        if not os.path.exists(test_path):
            print(f"ERROR: Test file {test_path} not found.")
            sys.exit(1)
        
        # Ensure implementation is empty/stubbed or doesn't exist
        # result = subprocess.run(["pytest", test_path])
        # For SVP-G, we expect failure here
        try:
            result = subprocess.run(["pytest", test_path], capture_output=True, text=True)
            if result.returncode != 0:
                print("RED VERIFIED: Tests failed as expected.")
                print(result.stdout)
                print(result.stderr)
            else:
                print("ERROR: Tests passed on an empty stub. Refine tests.")
                sys.exit(1)
        except Exception as e:
            print(f"Exception during pytest: {e}")
            sys.exit(1)
    
    if stage == "green":
        # Run tests against implementation
        try:
            result = subprocess.run(["pytest", test_path], capture_output=True, text=True)
            if result.returncode == 0:
                print("GREEN VERIFIED: Unit complete.")
                print(result.stdout)
            else:
                print("ERROR: Tests failed. Implementation incomplete.")
                print(result.stdout)
                print(result.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Exception during pytest: {e}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python verify_cycle.py <unit_name> <stage>")
        sys.exit(1)
    run_verification(sys.argv[1], sys.argv[2])
