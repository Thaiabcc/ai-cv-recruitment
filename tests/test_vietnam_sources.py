import json
import unittest
from unittest.mock import patch

import httpx
from sqlalchemy import select

import test_week4
from app.job_sources import matches
from app.models import RecruitmentSource
from app.vietnam_sources import (PublicPage, fetch_vietnam, job_postings, listing_url,
                                 normalize_posting, read_page, valid_detail)
from app.worker import process_once

CV_URL = 'https://careerviet.vn/vi/tim-viec-lam/python-dev.35ABC123.html'
TD_URL = 'https://topdev.vn/detail-jobs/python-developer-12345'


def posting(**changes):
    return {'@type': 'JobPosting', 'title': 'Python Developer',
            'description': '<p>Phát triển Python API.</p><script>bad()</script>',
            'hiringOrganization': {'name': 'Công ty mẫu'},
            'jobLocation': {'address': {'addressLocality': 'Hà Nội', 'addressCountry': 'VN'}},
            'validThrough': '2099-12-31', 'skills': 'Python, SQL',
            'baseSalary': {'currency': 'VND', 'value': {'minValue': 20000000, 'maxValue': 30000000, 'unitText': 'MONTH'}},
            **changes}


class VietnamParserTests(unittest.TestCase):
    def test_jobposting_normalization_dates_salary_and_location(self):
        job = normalize_posting(posting(), CV_URL, 'careerviet.vn')
        self.assertEqual(job['salary_text'], '20000000–30000000 VND/tháng')
        self.assertNotIn('bad()', job['description'])
        self.assertEqual(job['company'], 'Công ty mẫu')
        self.assertTrue(matches(job, {'keywords': ['Python'], 'location': 'Hanoi'}))
        self.assertFalse(matches(job, {'keywords': ['Python'], 'location': 'TP.HCM'}))
        job['location'] = 'Thành phố Hồ Chí Minh, VN'
        self.assertTrue(matches(job, {'keywords': ['Python'], 'location': 'TP.HCM'}))
        self.assertIsNone(normalize_posting(posting(validThrough='2000-01-01'), CV_URL, 'careerviet.vn'))
        td = normalize_posting(posting(), TD_URL, 'topdev.vn')
        self.assertEqual(td['salary_text'], '')
        self.assertIn('đăng nhập', td['salary_note'])
        self.assertFalse(td['remote'])

    def test_detail_urls_are_fixed_origin_and_public_paths(self):
        self.assertEqual(valid_detail(CV_URL + '?tracking=x', 'careerviet.vn'), CV_URL)
        for url in ['http://127.0.0.1/private', 'https://evil.com/detail-jobs/job-1',
                    'https://careerviet.vn/vi/jobseekers/jobs/apply?id=1',
                    'https://topdev.vn:443@evil.com/detail-jobs/job-1',
                    'https://topdev.vn:444/detail-jobs/job-1']:
            with self.assertRaises(ValueError): valid_detail(url, 'topdev.vn')
        self.assertEqual(listing_url('careerviet.vn', 'Lập trình Python'), 'https://careerviet.vn/viec-lam/lap-trinh-python-k-vi.html')
        self.assertIn('C%2B%2B', listing_url('topdev.vn', 'C++'))

    def test_public_jsonld_graph_and_duplicate_links(self):
        fixture = '<script type="application/ld+json">' + json.dumps({'@graph': [posting()]}).replace('</', '<\\/') + '</script>'
        page = PublicPage(); page.feed(fixture)
        self.assertEqual(len(list(job_postings(json.loads(page.json_blocks[0])))), 1)
        listing = f'<a href="{CV_URL}">A</a><a href="{CV_URL}?src=x">B</a><a href="https://evil.com/private">No</a>'
        def reader(client, url, domain): return fixture if '/vi/tim-viec-lam/' in url else listing
        with patch('app.vietnam_sources.read_page', side_effect=reader):
            batch = fetch_vietnam('careerviet.vn', {'keywords': ['Python', 'SQL']})
        self.assertEqual(len(batch['jobs']), 1)
        self.assertEqual(batch['warnings'], [])

    def test_one_detail_error_returns_partial_batch(self):
        second = CV_URL.replace('35ABC123', '35ABC124')
        listing = f'<a href="{CV_URL}">A</a><a href="{second}">B</a>'
        fixture = '<script type="application/ld+json">' + json.dumps(posting()).replace('</', '<\\/') + '</script>'
        def reader(client, url, domain):
            if url == second: raise ValueError('Unparseable content')
            return fixture if url == CV_URL else listing
        with patch('app.vietnam_sources.read_page', side_effect=reader):
            result = fetch_vietnam('careerviet.vn', {'keywords': ['Python']})
        self.assertEqual(len(result['jobs']), 1); self.assertTrue(result['warnings'])

    def test_robots_denial_redirect_and_cache(self):
        from app import vietnam_sources as module
        for forbidden in (False, True):
            module._robots.clear(); module._pages.clear()
            calls = []
            def handler(request):
                calls.append(str(request.url))
                return httpx.Response(200, text='User-agent: *\nDisallow: /' if forbidden else 'User-agent: *\nAllow: /') if request.url.path == '/robots.txt' else httpx.Response(200, text='<p>public</p>')
            with httpx.Client(transport=httpx.MockTransport(handler)) as client, patch('app.vietnam_sources.time.sleep'):
                if forbidden:
                    with self.assertRaises(ValueError): read_page(client, CV_URL, 'careerviet.vn')
                    self.assertEqual(len(calls), 1)
                else:
                    self.assertEqual(read_page(client, CV_URL, 'careerviet.vn'), '<p>public</p>')
                    read_page(client, CV_URL, 'careerviet.vn'); self.assertEqual(len(calls), 2)
        module._robots.clear(); module._pages.clear()
        with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(302, headers={'location': 'http://127.0.0.1'}))) as client:
            with self.assertRaises(ValueError): read_page(client, CV_URL, 'careerviet.vn')
        module._robots.clear(); module._pages.clear()


class VietnamSearchTests(unittest.TestCase):
    setUp = test_week4.SearchTests.setUp
    tearDown = test_week4.SearchTests.tearDown
    register = test_week4.SearchTests.register
    prepare = test_week4.SearchTests.prepare
    factory = test_week4.SearchTests.factory

    def setup_sources(self):
        cv = self.prepare()
        with self.factory() as db:
            ids = []
            for domain in ('careerviet.vn', 'topdev.vn'):
                source = db.scalar(select(RecruitmentSource).where(RecruitmentSource.domain == domain))
                if not source:
                    source = RecruitmentSource(domain=domain, name=domain, enabled=True); db.add(source)
                source.enabled = True
                db.flush(); ids.append(source.id)
            db.commit()
        return cv, ids

    def test_defaults_prioritize_vietnam_and_source_selection(self):
        cv, ids = self.setup_sources()
        for chosen in ([], [-1], [99999999]):
            self.assertEqual(self.client.post('/api/searches', json={'cv_id': cv['id'], 'source_ids': chosen}).status_code, 422)
        result = self.client.post('/api/searches', json={'cv_id': cv['id'], 'keywords': 'Python'}).json()
        self.assertEqual(set(result['query']['source_ids']), set(ids))
        self.assertIn('Việt Nam', result['query']['scope'])

    def test_one_source_failure_keeps_other_results(self):
        cv, ids = self.setup_sources()
        run = self.client.post('/api/searches', json={'cv_id': cv['id'], 'keywords': 'Python', 'location': 'Hà Nội'}).json()
        def adapter(domain, query):
            if domain == 'topdev.vn': raise ValueError('Blocked source')
            return {'jobs': [normalize_posting(posting(), CV_URL, domain)], 'warnings': []}
        with patch('app.worker.fetch_jobs', side_effect=adapter): process_once(self.factory)
        result = self.client.get('/api/searches/' + str(run['id'])).json()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(result['jobs']), 1)
        self.assertEqual(result['jobs'][0]['source'], 'CareerViet')
        self.assertIn(str(ids[1]), result['source_errors'])
