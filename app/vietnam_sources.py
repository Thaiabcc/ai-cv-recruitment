"""Small, rate-limited readers for public Vietnamese job pages, no login or API bypass."""
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.job_sources import clean_text

USER_AGENT = 'AI-CV-Recruitment/0.4 academic-project'
LIMIT = 6
_pages = {}
_robots = {}
_last_request = {}


class PublicPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.json_blocks = []
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'): self.links.append(attrs['href'])
        if tag == 'script':
            self.capture = attrs.get('type', '').lower() == 'application/ld+json'
            self.parts = []

    def handle_data(self, data):
        if self.capture: self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.capture:
            self.json_blocks.append(''.join(self.parts)); self.capture = False


def valid_detail(url, domain):
    parsed = urlsplit(url)
    pattern = (r'/vi/tim-viec-lam/[^/]+\.[0-9a-zA-Z]{8}\.html'
               if domain == 'careerviet.vn' else r'/detail-jobs/[^/]+-\d+')
    if (parsed.scheme != 'https' or parsed.hostname != domain or parsed.username or parsed.password
            or parsed.port not in (None, 443) or '%' in parsed.path or '\\' in parsed.path
            or not re.fullmatch(pattern, parsed.path)):
        raise ValueError('Unapproved detail URL')
    return urlunsplit(('https', domain, parsed.path, '', ''))


def _request(client, url):
    host = urlsplit(url).hostname
    wait = 1.2 - (time.monotonic() - _last_request.get(host, 0))
    if wait > 0: time.sleep(wait)
    _last_request[host] = time.monotonic()
    with client.stream('GET', url, headers={'User-Agent': USER_AGENT}) as response:
        if response.is_redirect: raise ValueError('Nguồn chuyển địa chỉ; cần cập nhật adapter.')
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > 4_000_000: raise ValueError('Trang vượt giới hạn 4 MB.')
    return content.decode('utf-8-sig', errors='replace')


def read_page(client, url, domain):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != domain or parsed.username or parsed.password
            or parsed.port not in (None, 443)):
        raise ValueError('Unapproved source URL')
    now = time.monotonic()
    if domain not in _robots or _robots[domain][0] < now:
        rules = RobotFileParser()
        rules.parse(_request(client, f'https://{domain}/robots.txt').splitlines())
        _robots[domain] = (now + 3600, rules)
    if not _robots[domain][1].can_fetch(USER_AGENT, url):
        raise ValueError('Nguồn không cho phép đọc đường dẫn này theo robots.txt.')
    cached = _pages.get(url)
    if cached and cached[0] > now: return cached[1]
    page = _request(client, url)
    # Keep the cache bounded across users and keyword combinations.
    if len(_pages) >= 64: _pages.pop(next(iter(_pages)))
    _pages[url] = (time.monotonic() + 600, page)
    return page


def job_postings(value):
    if isinstance(value, list):
        for item in value: yield from job_postings(item)
    elif isinstance(value, dict):
        types = value.get('@type', [])
        if 'JobPosting' in (types if isinstance(types, list) else [types]): yield value
        if '@graph' in value: yield from job_postings(value['@graph'])


def salary_text(raw):
    salary = raw.get('baseSalary') or {}
    if not isinstance(salary, dict): return ''
    value = salary.get('value')
    currency = clean_text(salary.get('currency'))
    if not currency or not isinstance(value, dict): return ''
    unit = {'MONTH': 'tháng', 'YEAR': 'năm', 'HOUR': 'giờ', 'WEEK': 'tuần'}.get(value.get('unitText'), '')
    def number(v):
        if isinstance(v, bool): return ''
        text = str(v or '')
        return text if re.fullmatch(r'\d+(?:\.\d+)?', text) and float(text) > 0 else ''
    low, high, exact = number(value.get('minValue')), number(value.get('maxValue')), number(value.get('value'))
    amount = f'{low}–{high}' if low and high else (f'Từ {low}' if low else (f'Đến {high}' if high else exact))
    return (f'{amount} {currency}' + (f'/{unit}' if unit else ''))[:255] if amount else ''


def normalize_posting(raw, url, domain):
    url = valid_detail(url, domain)
    expiry = raw.get('validThrough')
    if expiry:
        try:
            deadline = datetime.fromisoformat(str(expiry).replace('Z', '+00:00'))
            # A date-only deadline remains valid through the end of that day (Vietnam time).
            if len(str(expiry)) == 10:
                from datetime import timedelta
                deadline += timedelta(days=1)
            if deadline.tzinfo is None:
                from datetime import timedelta
                deadline = deadline.replace(tzinfo=timezone(timedelta(hours=7)))
            if deadline <= datetime.now(timezone.utc): return None
        except (ValueError, TypeError): raise ValueError('Không đọc được hạn tuyển dụng.')
    title, description = clean_text(raw.get('title'))[:255], clean_text(raw.get('description'))[:60000]
    if not title or not description: raise ValueError('Tin thiếu tiêu đề hoặc nội dung.')
    locations = raw.get('jobLocation') or []
    if isinstance(locations, dict): locations = [locations]
    names = []
    for location in locations:
        address = location.get('address') if isinstance(location, dict) else None
        if isinstance(address, dict):
            parts = list(dict.fromkeys(clean_text(address.get(key)) for key in
                ('addressLocality', 'addressRegion', 'addressCountry') if address.get(key)))
            if parts: names.append(', '.join(parts))
        elif isinstance(address, str): names.append(clean_text(address))
    organization = raw.get('hiringOrganization') or {}
    if not isinstance(organization, dict): organization = {}
    skills = raw.get('skills', '')
    if isinstance(skills, list): skills = ', '.join(str(item) for item in skills)
    return {'url': url, 'title': title, 'company': clean_text(organization.get('name'))[:255],
            'location': '; '.join(dict.fromkeys(names))[:255],
            # TopDev visibly gates salary behind login; do not expose metadata-only pay.
            'salary_text': salary_text(raw) if domain == 'careerviet.vn' else '',
            'description': description, 'remote': raw.get('jobLocationType') == 'TELECOMMUTE',
            'tags': [clean_text(s)[:100] for s in re.split(r'[,;\n]', str(skills)) if s.strip()][:30],
            'source': 'CareerViet' if domain == 'careerviet.vn' else 'TopDev',
            'salary_note': 'TopDev yêu cầu đăng nhập để xem lương.' if domain == 'topdev.vn' else '',
            'date_posted': str(raw.get('datePosted') or ''), 'expires_at': str(expiry or '')}


def listing_url(domain, keyword):
    if domain == 'topdev.vn': return 'https://topdev.vn/jobs/search?keyword=' + quote(keyword, safe='')
    word = unicodedata.normalize('NFKD', keyword.replace('đ', 'd').replace('Đ', 'D'))
    word = re.sub(r'[^a-z0-9]+', '-', word.encode('ascii', 'ignore').decode().lower()).strip('-')
    if not word: raise ValueError('Không tạo được từ khóa tìm việc cho nguồn.')
    return 'https://careerviet.vn/viec-lam/' + word + '-k-vi.html'


def fetch_vietnam(domain, query):
    jobs, warnings, links = {}, [], []
    started = time.monotonic()
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        # Two terms, first page only, then at most six detail pages for each source/run.
        for keyword in query['keywords'][:2]:
            try:
                page = PublicPage(); page.feed(read_page(client, listing_url(domain, keyword), domain))
            except (httpx.HTTPError, ValueError):
                warnings.append('Một trang tìm kiếm không đọc được.'); continue
            candidates = []
            for href in page.links:
                try: url = valid_detail(urljoin('https://' + domain, href), domain)
                except ValueError: continue
                if url not in candidates: candidates.append(url)
            # Reserve slots for each search term instead of spending all on the first term.
            for url in candidates[:3]:
                if url not in links: links.append(url)
        if not links:
            raise ValueError('Không đọc được danh sách tin; nguồn có thể đổi giao diện hoặc không có kết quả.')
        unreadable = 0
        for url in links[:LIMIT]:
            if time.monotonic() - started > 90:
                warnings.append('Đã dừng ở giới hạn thời gian của nguồn.'); break
            try:
                page = PublicPage(); page.feed(read_page(client, url, domain))
                found = False
                for block in page.json_blocks:
                    try: postings = list(job_postings(json.loads(block)))
                    except ValueError: continue
                    for posting in postings:
                        normalized = normalize_posting(posting, url, domain)
                        found = True
                        if normalized: jobs[url] = normalized
                if not found: unreadable += 1
            except (httpx.HTTPError, ValueError, TypeError, AttributeError): unreadable += 1
        if unreadable: warnings.append(f'{unreadable} tin không đọc được nội dung chi tiết.')
        if not jobs and unreadable == len(links[:LIMIT]):
            raise ValueError('Không đọc được nội dung tin; nguồn có thể đang chặn hoặc thay đổi giao diện.')
    return {'jobs': list(jobs.values()), 'warnings': warnings}
