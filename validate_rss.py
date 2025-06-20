# validate_rss.py
# Simple validator for mindfulnews.xml

import os

rss_file = "mindfulnews.xml"

if not os.path.exists(rss_file):
    print(f"❌ File not found: {rss_file}")
    exit(1)

with open(rss_file, "r", encoding="utf-8") as f:
    content = f.read()

xml_decl_count = content.count('<?xml')
rss_open_count = content.count('<rss')
rss_close_count = content.count('</rss>')

print(f"XML declaration count: {xml_decl_count}")
print(f"<rss> count: {rss_open_count}")
print(f"</rss> count: {rss_close_count}")

if xml_decl_count != 1 or rss_open_count != 1 or rss_close_count != 1:
    print("⚠️ RSS file is INVALID — duplicate XML declaration or RSS blocks.")
    exit(1)
else:
    print("✅ RSS file validated — looks good.")