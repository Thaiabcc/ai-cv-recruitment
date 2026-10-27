"""Fixed API adapter: no user-controlled requests or detail-page crawling."""
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

import httpx

API_URL = 'https://www.arbeitnow.com/api/job-board-api'
SOURCES = {
    'careerviet.vn': {'name': 'CareerViet', 'country': 'VN', 'scope': 'Việt Nam · 2 từ khóa, tối đa 6 tin chi tiết/lượt'},
    'topdev.vn': {'name': 'TopDev', 'country': 'VN', 'scope': 'Việt Nam · 2 từ khóa, tối đa 6 tin chi tiết/lượt'},
    'www.arbeitnow.com': {'name': 'Arbeitnow', 'country': 'international', 'scope': 'Đức / quốc tế · 100 tin mới nhất'},
}
_cache = None
_cache_until = 0


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
        if tag in ('p', 'li', 'br', 'h1', 'h2', 'h3'): self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1)
        if tag in ('p', 'li'): self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def clean_text(value):
    parser = PlainText()
    parser.feed(str(value or '')[:200000])
    return '\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())


def normalize(raw):
    url = urlsplit(str(raw.get('url', '')))
    if (url.scheme != 'https' or url.hostname != 'www.arbeitnow.com' or url.username
            or url.password or url.port not in (None, 443) or not url.path.startswith('/jobs/')):
        raise ValueError('Unapproved job URL')
    title = clean_text(raw.get('title'))[:255]
    description = clean_text(raw.get('description'))[:60000]
    if not title or not description: raise ValueError('Missing job content')
    return {'url': urlunsplit(('https', 'www.arbeitnow.com', url.path.rstrip('/'), '', '')),
            'title': title, 'company': clean_text(raw.get('company_name'))[:255],
            'location': clean_text(raw.get('location'))[:255], 'salary_text': '',
            'description': description, 'remote': raw.get('remote') is True,
            'tags': [clean_text(t)[:100] for t in raw.get('tags', [])[:30] if isinstance(t, str)],
            'source': 'Arbeitnow'}


def fetch_jobs(domain='www.arbeitnow.com', query=None):
    if domain not in SOURCES: raise ValueError('Nguồn chưa được hỗ trợ.')
    if domain != 'www.arbeitnow.com':
        from app.vietnam_sources import fetch_vietnam
        return fetch_vietnam(domain, query)
    global _cache, _cache_until
    if _cache is not None and time.monotonic() < _cache_until: return _cache
    # At most two attempts, one newest-feed page (normally 100 jobs), cached five minutes.
    for attempt in range(2):
        try:
            with httpx.Client(timeout=20, follow_redirects=False) as client:
                with client.stream('GET', API_URL, headers={'User-Agent': 'AI-CV-Recruitment/0.4 academic-project'}) as response:
                    response.raise_for_status()
                    if response.is_redirect: raise ValueError('Unexpected redirect')
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 5_000_000: raise ValueError('Feed too large')
            import json
            rows = json.loads(raw)['data']
            if not isinstance(rows, list): raise ValueError('Invalid feed')
            jobs = {}
            for row in rows[:100]:
                try:
                    job = normalize(row)
                    jobs[job['url']] = job
                except (ValueError, TypeError, AttributeError): continue
            if rows and not jobs: raise ValueError('No readable jobs')
            _cache, _cache_until = list(jobs.values()), time.monotonic() + 300
            return _cache
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            if attempt == 1: raise ValueError('Không lấy được dữ liệu Arbeitnow sau 2 lần thử.') from None
            time.sleep(1)


def matches(job, query):
    keywords = query['keywords']
    # Retrieval only, no suitability score. Exact token boundaries avoid Java matching JavaScript.
    haystack = ' '.join([job['title'], job['description'], ' '.join(job['tags'])]).casefold()
    text_match = any(re.search(r'(?<!\w)' + re.escape(word.casefold()) + r'(?!\w)', haystack) for word in keywords)
    location = normalize_location(query.get('location', ''))
    job_location = normalize_location(job['location'])
    location_match = not location or location in job_location or (location in ('remote', 'tu xa') and job['remote'])
    return text_match and location_match


def normalize_location(value):
    import unicodedata
    value = unicodedata.normalize('NFKD', value.casefold().replace('đ', 'd'))
    value = ''.join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r'[^a-z0-9]+', ' ', value).strip()
    for pattern, replacement in [(r'\b(?:tp\s+)?(?:ho\s+chi\s+minh|hcmc|hcm|saigon|sai\s+gon)\b', 'ho chi minh'),
                                  (r'\bha\s*noi\b', 'ha noi'), (r'\bda\s*nang\b', 'da nang')]:
        value = re.sub(pattern, replacement, value)
    return value
