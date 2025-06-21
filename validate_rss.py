# validate_rss.py v1.2
# Simple validator for mindfulnews.xml or any RSS file passed as argument

import os
import sys
import re

# Accept filename as argument, or default to "mindfulnews.xml"
rss_file = sys.argv[1] if len(sys.argv) > 1 else "mindfulnews.xml"

if not os.path.exists(rss_file):
    print(f"❌ File not found: {rss_file}")
    exit(1)

with open(rss_file, "r", encoding="utf-8") as f:
    content = f.read()

# Count only true XML declarations (<?xml version=…), not stylesheet PIs
xml_decl_count = len(re.findall(r'<\?xml\s+version=', content))
rss_open_count = content.count('<rss')
rss_close_count = content.count('</rss>')

print(f"\n📄 Validating file: {rss_file}")
print(f"XML declaration count: {xml_decl_count}")
print(f"<rss> count: {rss_open_count}")
print(f"</rss> count: {rss_close_count}")

if xml_decl_count != 1 or rss_open_count != 1 or rss_close_count != 1:
    print("⚠️ RSS file is INVALID — duplicate XML declaration or RSS blocks.")
    exit(1)
else:
    print("✅ RSS file validated — looks good.")