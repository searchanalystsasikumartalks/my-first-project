"""Read-only catalog draft planner. No network, publishing, or in-place writes."""
import argparse
import datetime
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

FILES = ('index.html', 'manifest.json', 'sitemap.xml')
BASE = 'https://sasikumartalks.com/appln/'
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

def digest(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def once(source, old, new):
    require(source.count(old) == 1, 'Ambiguous or changed catalog structure')
    return source.replace(old, new, 1)

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result

def plan(snapshot, metadata, inventory, expected):
    """inventory is fresh Master inspect_application.files, not inferred from voice."""
    require(set(snapshot) == set(FILES), 'Exactly three catalog snapshots required')
    require(all(digest(snapshot[p]) == expected.get(p) for p in FILES), 'Snapshot hash conflict')
    fields = {'slug', 'title', 'category', 'summary', 'version', 'updated'}
    require(set(metadata) == fields, 'Provide exactly slug, title, category, summary, version, updated')
    require(all(isinstance(v, str) and v.strip() == v and v for v in metadata.values()), 'Empty or invalid metadata')
    slug = metadata['slug']
    require(bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug)) and len(slug) <= 80, 'Unsafe slug')
    require(bool(re.fullmatch(r'\d+\.\d+\.\d+', metadata['version'])), 'Version must be x.y.z')
    require(datetime.date.fromisoformat(metadata['updated']).isoformat() == metadata['updated'], 'Invalid date')
    require(all(len(metadata[k]) <= 500 and not any(ord(c) < 32 for c in metadata[k]) for k in fields), 'Metadata too long or control characters')
    path = 'apps/' + slug + '/index.html'
    require(any(f.get('path') == path and f.get('type') == 'file' and f.get('bytes', 0) > 0 and re.fullmatch('[a-f0-9]{64}', f.get('sha256', '')) for f in inventory), 'App entry point missing from verified draft inventory')
    url = BASE + 'apps/' + slug + '/'
    entry = dict(metadata, url=url)
    manifest = json.loads(snapshot['manifest.json'], object_pairs_hook=unique_pairs)
    require(manifest.get('schema_version') == 1 and isinstance(manifest.get('applications'), list), 'Unsupported manifest schema')
    entries = manifest['applications']
    slugs = [e['slug'] for e in entries]
    urls = [e['url'] for e in entries]
    require(len(set(slugs)) == len(slugs) and len(set(urls)) == len(urls), 'Existing manifest duplicates require review')
    index = snapshot['index.html']
    cards = re.findall(r'<article\b[^>]*class="app-card"[^>]*>.*?</article>', index, re.S)
    card_urls = []
    for card in cards:
        links = set(re.findall(r'href="(/appln/apps/[a-z0-9-]+/)"', card))
        require(len(links) == 1, 'Unsupported card structure')
        card_urls.append('https://sasikumartalks.com' + links.pop())
    require(len(set(card_urls)) == len(card_urls), 'Duplicate cards require review')
    sitemap = snapshot['sitemap.xml']
    require('<!DOCTYPE' not in sitemap.upper() and '<!ENTITY' not in sitemap.upper(), 'XML declarations prohibited')
    root = ET.fromstring(sitemap)
    require(root.tag == NS + 'urlset', 'Unsupported sitemap')
    locations = [n.text for n in root.findall(NS + 'url/' + NS + 'loc')]
    require(len(set(locations)) == len(locations), 'Duplicate sitemap URLs require review')
    require(set(card_urls) == set(urls) and set(locations) == set(urls) | {BASE}, 'Catalog membership differs; repair separately')
    counts = re.findall(r'(<p id="count"[^>]*>)(\d+)( applications</p>)', index)
    require(len(counts) == 1, 'Unsupported count element')
    warnings = []
    if int(counts[0][1]) != len(entries):
        warnings.append('Existing static count differs from actual cards; updating count with this addition.')
    if slug in slugs or url in urls:
        require(slug in slugs and entries[slugs.index(slug)] == entry, 'Existing app differs; explicit update required')
        return {'app': 'application-studio', 'status': 'no-op', 'writes': [], 'warnings': warnings}
    escaped = {k: html.escape(v, quote=True) for k, v in metadata.items()}
    card = ('<article class="app-card" data-category="{category}"><span class="pill">Available</span>'
            '<div class="app-icon" aria-hidden="true">⇄</div><span class="eyebrow">{category}</span>'
            '<h2>{title}</h2><p>{summary}</p><a href="/appln/apps/{slug}/">Open application →</a></article>').format(**escaped)
    require(bool(cards), 'Empty catalog requires explicit template review')
    index = once(index, cards[-1] + '</div><p id="empty"', cards[-1] + card + '</div><p id="empty"')
    count = counts[0]
    index = once(index, ''.join(count), count[0] + str(len(entries) + 1) + count[2])
    select = re.findall(r'<select id="category">(.*?)</select>', index, re.S)
    require(len(select) == 1, 'Unsupported category filter')
    options = [html.unescape(v) for v in re.findall(r'<option(?:\s[^>]*)?>(.*?)</option>', select[0], re.S)]
    if metadata['category'] not in options:
        index = once(index, '<select id="category">' + select[0] + '</select>', '<select id="category">' + select[0] + '<option>' + escaped['category'] + '</option></select>')
    # Append to the applications array without reformatting any existing entry.
    match = re.search(r'\]\s*}\s*$', snapshot['manifest.json'])
    require(match is not None, 'Unsupported manifest tail')
    addition = (',' if entries else '') + '\n    ' + json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n  '
    manifest_text = snapshot['manifest.json'][:match.start()].rstrip() + addition + snapshot['manifest.json'][match.start():]
    require(json.loads(manifest_text)['applications'] == entries + [entry], 'Manifest preservation check failed')
    sitemap = once(sitemap, '</urlset>', '<url><loc>' + url + '</loc><lastmod>' + metadata['updated'] + '</lastmod></url></urlset>')
    ET.fromstring(sitemap)
    after = {'index.html': index, 'manifest.json': manifest_text, 'sitemap.xml': sitemap}
    return {'app': 'application-studio', 'status': 'private-draft-plan-only', 'app_entrypoint': path,
            'warnings': warnings, 'requires_owner_portal_approval': True,
            'writes': [{'path': p, 'expected_sha256': expected[p], 'sha256': digest(after[p]), 'content': after[p]} for p in FILES]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--metadata', required=True, type=Path)
    parser.add_argument('--inventory', required=True, type=Path)
    args = parser.parse_args()
    snapshot = {p: (args.snapshot / p).read_bytes().decode('utf-8') for p in FILES}
    result = plan(snapshot, json.loads(args.metadata.read_text()), json.loads(args.inventory.read_text())['files'], json.loads((args.snapshot / 'revisions.json').read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
