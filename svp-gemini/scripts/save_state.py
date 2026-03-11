from pathlib import Path
import json
import sys
import os

# Add current script directory to sys.path to find ported scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline_state import load_state, save_state

def run_save(project_root: Path):
    state_path = project_root / "ledgers" / "pipeline_state.json"
    if not state_path.exists():
        # Initialize if not exists
        state = {"stage": "Stage 0", "current_unit": None, "history": []}
        os.makedirs(state_path.parent, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=4)
        print(f"Initialized new state at {state_path}")
    
    try:
        # Load and save to trigger timestamp updates if implemented
        # In this port, we'll just ensure it's valid JSON
        with open(state_path, "r") as f:
            state = json.load(f)
        
        with open(state_path, "w") as f:
            json.dump(state, f, indent=4)
            
        print("Save complete. State file verified.")
    except Exception as e:
        print(f"Error saving state: {e}")
        sys.exit(1)

if __name__ == "__main__":
    project_root = Path(os.getcwd())
    run_save(project_root)
