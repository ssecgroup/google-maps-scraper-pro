#!/usr/bin/env python3
"""
Checkpoint to Final Converter
Converts checkpoint files to final formats
"""

import argparse
import os
import glob
import json
from datetime import datetime
import pandas as pd

class CheckpointConverter:
    """Convert checkpoint files to final formats"""
    
    def __init__(self):
        self.output_dir = 'output/final'
        os.makedirs(os.path.join(self.output_dir, 'csv'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'excel'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'json'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'html'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'summary'), exist_ok=True)
    
    def convert_checkpoint(self, checkpoint_file: str, output_name: str = None):
        """Convert a checkpoint file to all formats"""
        
        if not os.path.exists(checkpoint_file):
            print(f"Error: {checkpoint_file} not found")
            return
        
        # Read businesses
        businesses = []
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    businesses.append(json.loads(line))
        
        print(f"Loaded {len(businesses)} businesses from checkpoint")
        
        # Generate output name
        if not output_name:
            base = os.path.basename(checkpoint_file).replace('.jsonl', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_name = f"{base}_{timestamp}"
        
        # Convert to all formats
        self.to_csv(businesses, output_name)
        self.to_excel(businesses, output_name)
        self.to_json(businesses, output_name)
        self.to_html(businesses, output_name)
        self.to_summary(businesses, output_name)
        
        print(f"\n✅ Conversion complete! Files saved in {self.output_dir}")
    
    def to_csv(self, businesses, name):
        filename = os.path.join(self.output_dir, 'csv', f'{name}.csv')
        pd.DataFrame(businesses).to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✓ CSV: {filename}")
    
    def to_excel(self, businesses, name):
        filename = os.path.join(self.output_dir, 'excel', f'{name}.xlsx')
        pd.DataFrame(businesses).to_excel(filename, index=False)
        print(f"✓ Excel: {filename}")
    
    def to_json(self, businesses, name):
        filename = os.path.join(self.output_dir, 'json', f'{name}.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(businesses, f, indent=2, ensure_ascii=False, default=str)
        print(f"✓ JSON: {filename}")
    
    def to_html(self, businesses, name):
        filename = os.path.join(self.output_dir, 'html', f'report_{name}.html')
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Business Report</title>
    <style>
        body {{ font-family: Arial; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th {{ background: #4CAF50; color: white; padding: 8px; }}
        td {{ border: 1px solid #ddd; padding: 8px; }}
    </style>
</head>
<body>
    <h1>Business Report</h1>
    <p>Total: {len(businesses)} businesses</p>
    <table>
        <tr>
            <th>#</th>
            <th>Name</th>
            <th>Phone</th>
            <th>Website</th>
        </tr>"""
        
        for i, b in enumerate(businesses[:100]):
            html += f"""
        <tr>
            <td>{i+1}</td>
            <td>{b.get('name', 'N/A')}</td>
            <td>{b.get('phone', 'N/A')}</td>
            <td><a href="{b.get('website', '#')}">Link</a></td>
        </tr>"""
        
        html += """
    </table>
</body>
</html>"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✓ HTML: {filename}")
    
    def to_summary(self, businesses, name):
        filename = os.path.join(self.output_dir, 'summary', f'summary_{name}.txt')
        
        total = len(businesses)
        with_phone = sum(1 for b in businesses if b.get('phone'))
        with_website = sum(1 for b in businesses if b.get('website'))
        
        summary = f"""
{'='*60}
BUSINESS SCRAPING SUMMARY
{'='*60}
Total Businesses: {total}
With Phone: {with_phone} ({with_phone/total*100:.1f}%)
With Website: {with_website} ({with_website/total*100:.1f}%)
{'='*60}
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"✓ Summary: {filename}")

def main():
    parser = argparse.ArgumentParser(description='Convert checkpoint to final formats')
    parser.add_argument('checkpoint', help='Checkpoint file to convert')
    parser.add_argument('--name', '-n', help='Output name (optional)')
    
    args = parser.parse_args()
    
    converter = CheckpointConverter()
    converter.convert_checkpoint(args.checkpoint, args.name)

if __name__ == "__main__":
    main()
