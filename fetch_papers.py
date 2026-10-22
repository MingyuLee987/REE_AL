"""Retrieve publisher HTML for a transparent source audit; no access bypass."""
import concurrent.futures
import hashlib
import json
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'tr', 'h1', 'h2', 'h3', 'h4', 'section', 'caption', 'div'):
            self.parts.append('\n')
        elif tag in ('td', 'th'):
            self.parts.append(' | ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag in ('p', 'tr', 'caption'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def publisher_url(doi, fallback):
    if doi.startswith('10.3390/'):
        m = re.fullmatch(r'10.3390/(met|ma|coatings)(\d{2})(\d{2})(\d+)', doi)
        if m:
            journal, volume, issue, article = m.groups()
            issn = {'met': '2075-4701', 'ma': '1996-1944', 'coatings': '2079-6412'}[journal]
            return f'https://www.mdpi.com/{issn}/{int(volume)}/{int(issue)}/{int(article)}'
    if doi.startswith('10.1038/'):
        return 'https://www.nature.com/articles/' + doi.split('/')[1]
    if doi.startswith('10.1007/'):
        return 'https://link.springer.com/article/' + doi
    return 'https://doi.org/' + doi if doi.startswith('10.') else fallback


def main():
    d = pd.read_excel('rare_earth_steel_single_sheet_sources.xlsx')
    out = Path('outputs/paper_sources')
    out.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        doi, group = item
        key = hashlib.sha256(doi.encode()).hexdigest()[:12]
        fallback = str(group.phase_source_url.iloc[0])
        url = publisher_url(doi, fallback)
        row = dict(source_paper_id=doi, n_records=len(group), requested_url=url, cache_key=key)
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research data verification)'})
            with urllib.request.urlopen(request, timeout=25) as r:
                raw = r.read()
                row.update(final_url=r.url, http_status=r.status)
            (out / f'{key}.html').write_bytes(raw)
            parser = TextParser()
            parser.feed(raw.decode('utf-8', errors='replace'))
            text = '\n'.join(re.sub(r'[ \t\r\f\v]+', ' ', s).strip() for s in ''.join(parser.parts).splitlines())
            text = re.sub(r'\n{3,}', '\n\n', text)
            (out / f'{key}.txt').write_text(text, encoding='utf-8')
            row.update(fetch_status='retrieved_not_yet_verified' if len(text) > 5000 else 'landing_or_challenge_only', text_chars=len(text))
        except Exception as e:
            row.update(fetch_status='unavailable', error=str(e))
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(fetch, d.groupby('source_paper_id', sort=False)))
    pd.DataFrame(rows).to_csv(out / 'retrieval_inventory.csv', index=False, encoding='utf-8-sig')
    print(pd.DataFrame(rows)[['source_paper_id', 'fetch_status', 'text_chars']].to_string(index=False))


def fetch_tables():
    out = Path('outputs/paper_sources')
    inventory = pd.read_csv(out / 'retrieval_inventory.csv')
    jobs = []
    for row in inventory.itertuples():
        if not pd.notna(row.text_chars) or row.text_chars < 5000:
            continue
        html = (out / f'{row.cache_key}.html').read_text(encoding='utf-8', errors='replace')
        links = sorted(set(re.findall(r'href=["\']([^"\']*/tables/\d+)["\']', html)))
        for link in links:
            jobs.append((row.cache_key, urllib.parse.urljoin(row.final_url, link)))

    def fetch(job):
        key, url = job
        path = out / f'{key}_table{url.rsplit("/", 1)[1]}.txt'
        try:
            raw = urllib.request.urlopen(url, timeout=25).read().decode('utf-8')
            parser = TextParser()
            parser.feed(raw)
            text = re.sub(r'\n{3,}', '\n\n', ''.join(parser.parts))
            path.write_text(text, encoding='utf-8')
            return (url, len(text))
        except Exception as e:
            return (url, str(e))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for result in pool.map(fetch, jobs):
            print(result)


def fetch_pmc():
    import xml.etree.ElementTree as ET
    out = Path('outputs/paper_sources')
    d = pd.read_csv(out / 'retrieval_inventory.csv')
    dois = d.loc[d.source_paper_id.str.startswith('10.'), 'source_paper_id']
    query = ' OR '.join('DOI:' + doi for doi in dois)
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?format=json&pageSize=100&query=' + urllib.parse.quote(query)
    result = json.load(urllib.request.urlopen(url, timeout=30))['resultList']['result']
    rows = []
    for item in result:
        pmc = item.get('pmcid')
        if not pmc:
            continue
        doi = item['doi'].lower()
        url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML'
        try:
            raw = urllib.request.urlopen(url, timeout=25).read()
            root = ET.fromstring(raw)
            (out / f'{pmc}.xml').write_bytes(raw)
            # Keep paragraphs and tables separated for review.
            text = '\n'.join(''.join(node.itertext()) for node in root.iter() if node.tag in ['article-title', 'title', 'p', 'tr'])
            (out / f'{pmc}.txt').write_text(text, encoding='utf-8')
            rows.append(dict(source_paper_id=doi, pmcid=pmc, url=url, status='full_text_retrieved'))
        except Exception as e:
            rows.append(dict(source_paper_id=doi, pmcid=pmc, url=url, status=str(e)))
    pd.DataFrame(rows).to_csv(out / 'pmc_inventory.csv', index=False)
    print(pd.DataFrame(rows).to_string(index=False))


def summarize_access():
    out = Path('outputs/paper_sources')
    inv = pd.read_csv(out / 'retrieval_inventory.csv').fillna('')
    pmc_path = out / 'pmc_inventory.csv'
    pmc = pd.read_csv(pmc_path) if pmc_path.exists() else pd.DataFrame(columns=['source_paper_id', 'status', 'pmcid'])
    reviews = pd.read_csv('audit/paper_review.csv').set_index('source_paper_id')
    rows = []
    for row in inv.to_dict('records'):
        doi = row['source_paper_id']
        matches = pmc.loc[pmc.source_paper_id.eq(doi)]
        xml = matches.loc[matches.status.eq('full_text_retrieved')]
        reviewed = reviews.loc[doi, 'review_status'] != 'full_text_not_reviewed'
        row['publisher_fetch_status'] = row.pop('fetch_status')
        row['pmc_id'] = xml.pmcid.iloc[0] if not xml.empty else ''
        row['review_status'] = reviews.loc[doi, 'review_status']
        row['access_interpretation'] = ('relevant_full_text_reviewed' if reviewed else 'full_text_not_reviewed; HTTP success does not establish full text')
        rows.append(row)
    pd.DataFrame(rows).to_csv('audit/access_inventory.csv', index=False, encoding='utf-8-sig')
    print(f'Access inventory: {len(rows)} source records; review scopes kept separate from retrieval.')


if __name__ == '__main__':
    import sys
    if '--tables' in sys.argv:
        fetch_tables()
    elif '--pmc' in sys.argv:
        fetch_pmc()
    elif '--inventory' in sys.argv:
        summarize_access()
    else:
        main()
