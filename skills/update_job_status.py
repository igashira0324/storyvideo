import os
import sys
import json
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Update job status JSON after completion")
    parser.add_argument("status_path", help="Path to status JSON")
    parser.add_argument("returncode", type=int, help="Exit code of the job")
    args = parser.parse_args()
    
    if not os.path.exists(args.status_path):
        sys.exit(1)
        
    try:
        with open(args.status_path, 'r') as f:
            data = json.load(f)
            
        data["status"] = "completed" if args.returncode == 0 else "failed"
        data["returncode"] = args.returncode
        data["finished_at"] = datetime.now().isoformat()
        
        with open(args.status_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to update status: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
