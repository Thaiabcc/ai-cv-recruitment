import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session

import test_accounts
from app.ai import availability, generate_career
from app.config import settings
from app.job_sources import matches, normalize
from app.models import RecruitmentSource, SearchRun, SearchRunJob
from app.worker import process_once


def sample():
    return normalize({'url': 'https://www.arbeitnow.com/jobs/test?utm_source=foo',
        'title': 'Python Developer', 'company_name': 'Test company', 'location': 'Berlin',
        'description': '<h2>Requirements</h2><p>Python and SQL</p><script>bad()</script>',
        'tags': ['Python'], 'remote': True})


class SearchTests(unittest.TestCase):
    setUp = test_accounts.AccountTests.setUp
    tearDown = test_accounts.AccountTests.tearDown
    register = test_accounts.AccountTests.register

    def prepare(self):
        self.register()
        self.client.put('/api/profile', json={'full_name': 'Ứng viên thử', 'skills': 'Python', 'desired_position': 'Backend'})
        cv = self.client.post('/api/cvs/draft').json()
        with self.factory() as db:
            db.execute(update(RecruitmentSource).values(enabled=False))
            source = db.scalar(select(RecruitmentSource).where(RecruitmentSource.domain == 'www.arbeitnow.com'))
            if not source:
                source = RecruitmentSource(name='Arbeitnow', domain='www.arbeitnow.com', enabled=True)
                db.add(source)
            else: source.enabled = True
            db.commit()
        return cv

    def factory(self):
        return Session(bind=self.connection, join_transaction_mode='create_savepoint')

    def enqueue(self, cv):
        response = self.client.post('/api/searches', json={'cv_id': cv['id'], 'keywords': 'Python', 'location': ''})
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_auth_and_ownership(self):
        self.assertEqual(self.client.get('/api/searches').status_code, 401)
        cv = self.prepare(); run = self.enqueue(cv)
        self.register(self.other, {'email': 'other-' + self.email, 'password': 'Test-password-123'})
        self.assertEqual(self.other.get('/api/searches/' + str(run['id'])).status_code, 404)
        self.assertEqual(self.other.post('/api/searches', json={'cv_id': cv['id']}).status_code, 404)
        self.assertEqual(self.other.get('/api/searches').json()['items'], [])
        self.assertEqual(self.client.post('/api/searches', json={'cv_id': cv['id']}, headers={'X-Requested-With': ''}).status_code, 403)

    def test_queue_worker_results_snapshot_and_duplicate(self):
        cv = self.prepare(); run = self.enqueue(cv)
        self.assertEqual(self.client.post('/api/searches', json={'cv_id': cv['id']}).status_code, 409)
        with patch('app.worker.fetch_jobs', return_value=[sample(), sample()]):
            self.assertTrue(process_once(self.factory))
        result = self.client.get('/api/searches/' + str(run['id'])).json()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(result['jobs']), 1)
        self.assertNotIn('<', result['jobs'][0]['description'])
        self.client.put('/api/profile', json={'full_name': 'Changed', 'skills': 'Java'})
        self.assertEqual(result['query']['profile']['skills'], 'Python')
        self.assertEqual(self.client.post('/api/searches', json={'cv_id': cv['id']}).status_code, 429)

    def test_empty_failed_and_stale_worker(self):
        cv = self.prepare(); run = self.enqueue(cv)
        with patch('app.worker.fetch_jobs', return_value=[]): process_once(self.factory)
        result = self.client.get('/api/searches/' + str(run['id'])).json()
        self.assertEqual(result['status'], 'completed'); self.assertEqual(result['jobs'], [])
        with self.factory() as db:
            item = db.get(SearchRun, run['id']); item.status = 'queued'; db.commit()
        with patch('app.worker.fetch_jobs', side_effect=ValueError('private diagnostics')): process_once(self.factory)
        result = self.client.get('/api/searches/' + str(run['id'])).json()
        self.assertEqual(result['status'], 'failed'); self.assertNotIn('private diagnostics', str(result))
        with self.factory() as db:
            item = db.get(SearchRun, run['id']); item.status = 'running'; item.started_at = datetime.utcnow()-timedelta(minutes=11); db.commit()
        process_once(self.factory)
        self.assertEqual(self.client.get('/api/searches/' + str(run['id'])).json()['status'], 'failed')

    def test_normalization_filters_and_links(self):
        job = sample()
        self.assertEqual(job['url'], 'https://www.arbeitnow.com/jobs/test')
        self.assertNotIn('bad()', job['description'])
        self.assertTrue(matches(job, {'keywords': ['Python'], 'location': 'remote'}))
        self.assertFalse(matches(job, {'keywords': ['Java'], 'location': ''}))
        self.assertFalse(matches(job, {'keywords': ['Python'], 'location': 'Hà Nội'}))
        for url in ['http://127.0.0.1/jobs/a', 'https://evil.com/jobs/a', 'javascript:alert(1)', 'https://www.arbeitnow.com:444/jobs/a']:
            with self.assertRaises(ValueError): normalize({'url': url})


class OllamaTests(unittest.TestCase):
    def setUp(self):
        context = patch.object(settings, 'ai_provider', 'ollama'); context.start(); self.addCleanup(context.stop)

    def response(self, **updates):
        data = {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps({
            'title': 'Backend', 'summary': '', 'education': '', 'skills': 'Python', 'experience': '', 'projects': ''})}}
        return httpx.Response(200, json=dict(data, **updates))

    def test_schema_and_contact_minimization(self):
        with patch('app.ai._post', return_value=self.response()) as post:
            self.assertEqual(generate_career({'skills': 'Python', 'email': 'private@example.com'}, '').skills, 'Python')
            body = post.call_args.kwargs['json']
            self.assertFalse(body['stream']); self.assertIn('required', body['format'])
            self.assertEqual(body['options']['num_ctx'], 8192)
            self.assertEqual(body['options']['num_predict'], 3072)
            self.assertNotIn('private@example.com', str(body))
            self.assertEqual(post.call_args.args[0], 'http://127.0.0.1:11434/api/chat')

    def test_errors_incomplete_and_no_cloud_fallback(self):
        from fastapi import HTTPException
        for response, status in [(httpx.Response(404), 503), (httpx.Response(500), 503),
                                  (self.response(done=False), 502), (self.response(done_reason='length'), 502),
                                  (self.response(message={'content': '{}'}), 502)]:
            with patch('app.ai._post', return_value=response), patch('app.gemini._post') as cloud:
                with self.assertRaises(HTTPException) as error: generate_career({}, '')
                self.assertEqual(error.exception.status_code, status); cloud.assert_not_called()
        for exception, status in [(httpx.ReadTimeout('timeout'), 504), (httpx.ConnectError('offline'), 503)]:
            with patch('app.ai._post', side_effect=exception):
                with self.assertRaises(HTTPException) as error: generate_career({}, '')
                self.assertEqual(error.exception.status_code, status)

    def test_local_only_configuration(self):
        from fastapi import HTTPException
        with patch.object(settings, 'ollama_base_url', 'https://example.com'), patch('app.ai._post') as post:
            with self.assertRaises(HTTPException): generate_career({}, '')
            post.assert_not_called()

    def test_oversized_input_is_not_silently_truncated(self):
        from fastapi import HTTPException
        with patch('app.ai._post') as post:
            with self.assertRaises(HTTPException) as error: generate_career({'skills': 'Python ' * 3000}, '')
            self.assertEqual(error.exception.status_code, 422)
            post.assert_not_called()
