#!/usr/bin/env python3
"""
Minimal test to isolate the hanging issue
"""

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', default='~/Programming')
    parser.add_argument('--analyze-only', action='store_true')
    args = parser.parse_args()
    
    print(f"🔍 Testing scan of {args.scan}")
    print(f"analyze-only: {args.analyze_only}")
    
    base_path = Path(args.scan).expanduser()
    print(f"Expanded path: {base_path}")
    
    if base_path.exists():
        print("✅ Path exists")
        print(f"Is directory: {base_path.is_dir()}")
        
        if (base_path / '.git').exists():
            print("✅ Base directory is a git repo")
        else:
            print("❌ Base directory is not a git repo")
            
        # List subdirectories without analyzing them
        subdirs = [item for item in base_path.iterdir() if item.is_dir() and not item.name.startswith('.')]
        print(f"Found {len(subdirs)} subdirectories")
        for subdir in subdirs[:5]:  # Just first 5
            print(f"  📁 {subdir.name}")
            
    else:
        print("❌ Path does not exist")
    
    print("✅ Test completed successfully")
    return 0

if __name__ == '__main__':
    main()
