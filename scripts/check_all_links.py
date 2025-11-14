"""
File: check_all_links.py
Purpose: Verify all links in templates match available routes
Main functionality: Extract links from templates and check against registered routes
Dependencies: Flask app, BeautifulSoup
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
import re
from pathlib import Path

def get_all_routes():
    """Get all registered routes in Flask app"""
    routes = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes[rule.rule] = {
                'methods': list(rule.methods),
                'endpoint': rule.endpoint
            }
    return routes

def extract_links_from_templates():
    """Extract all href and onclick links from HTML templates"""
    templates_dir = Path('src/templates')
    links = {}
    
    for template_file in templates_dir.glob('*.html'):
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Extract href links
            href_links = re.findall(r'href=["\']([^"\']+)["\']', content)
            
            # Extract onclick window.location links
            onclick_links = re.findall(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', content)
            
            # Extract fetch URLs
            fetch_urls = re.findall(r'fetch\(["\']([^"\']+)["\']', content)
            
            all_links = href_links + onclick_links + fetch_urls
            
            # Filter out external links, anchors, and javascript
            internal_links = [
                link for link in all_links 
                if link.startswith('/') and not link.startswith('http') 
                and link != '#' and not link.startswith('javascript:')
            ]
            
            if internal_links:
                links[template_file.name] = list(set(internal_links))
    
    return links

def check_link_validity(link, routes):
    """Check if a link matches any registered route"""
    # Remove query parameters and anchors
    clean_link = link.split('?')[0].split('#')[0]
    
    # Direct match
    if clean_link in routes:
        return True, f"Direct match: {clean_link}"
    
    # Check with dynamic segments
    for route_pattern in routes.keys():
        # Convert Flask route pattern to regex
        pattern = route_pattern
        pattern = re.sub(r'<int:([^>]+)>', r'\\d+', pattern)
        pattern = re.sub(r'<([^>]+)>', r'[^/]+', pattern)
        pattern = f'^{pattern}$'
        
        if re.match(pattern, clean_link):
            return True, f"Pattern match: {route_pattern}"
    
    return False, "No matching route"

def main():
    print("=" * 80)
    print("Link Validation Report")
    print("=" * 80)
    print()
    
    # Get all routes
    routes = get_all_routes()
    print(f"Total registered routes: {len(routes)}")
    print()
    
    # Extract links from templates
    template_links = extract_links_from_templates()
    print(f"Templates analyzed: {len(template_links)}")
    print()
    
    # Check each link
    invalid_links = []
    valid_links = []
    
    for template, links in sorted(template_links.items()):
        print(f"\n{template}:")
        print("-" * 80)
        
        for link in sorted(set(links)):
            is_valid, reason = check_link_validity(link, routes)
            
            if is_valid:
                print(f"  [OK] {link}")
                print(f"    -> {reason}")
                valid_links.append((template, link))
            else:
                print(f"  [X] {link}")
                print(f"    -> {reason}")
                invalid_links.append((template, link))
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Valid links: {len(valid_links)}")
    print(f"Invalid links: {len(invalid_links)}")
    print()
    
    if invalid_links:
        print("\n[WARNING] Invalid Links Found:")
        print("-" * 80)
        for template, link in invalid_links:
            print(f"  {template}: {link}")
        print()
        print("These links need to be fixed or routes need to be added.")
    else:
        print("[SUCCESS] All links are valid!")
    
    # Show most common routes being used
    print("\n" + "=" * 80)
    print("Most Common Link Patterns")
    print("=" * 80)
    
    link_counts = {}
    for template, links in template_links.items():
        for link in links:
            # Normalize link (remove IDs)
            normalized = re.sub(r'/\d+', '/{id}', link)
            link_counts[normalized] = link_counts.get(normalized, 0) + 1
    
    for link, count in sorted(link_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {count:2d}x  {link}")

if __name__ == '__main__':
    main()
