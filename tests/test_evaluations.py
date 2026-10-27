import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from sqlalchemy import select

import test_week4
from app.config import settings
from app.evaluation_ai import Assessment, evaluate_job, score_assessment
from app.evaluation_worker import process_evaluation_once
from app.models import Evaluation, EvaluationBatch, SearchRun, SearchRunJob
from app.worker import process_once


def criterion(category='skills', quote='Python', status='matched', field='profile.skills', evidence='Python'):
    return {'category': category, 'requirement_quote': quote, 'status': status,
            'evidence_field': field, 'candidate_quote': evidence}


def assessment(*items):
    return Assessment.model_validate({'criteria': list(items)})


def response(*items, done=True, reason='stop'):
    return httpx.Response(200, json={'done': done, 'done_reason': reason,
        'message': {'content': json.dumps({'criteria': list(items)}, ensure_ascii=False)}})


class ScoringTests(unittest.TestCase):
    def test_weighted_score_coverage_and_unknown(self):
        result = score_assessment(assessment(criterion(), criterion('experience', '3 năm kinh nghiệm', 'partial', 'profile.experience', '1 năm kinh nghiệm'),
            criterion('education', 'Đại học', 'unknown', '', '')), 'Python; 3 năm kinh nghiệm; Đại học',
            {'profile.skills': 'Python', 'profile.experience': '1 năm kinh nghiệm'})
        self.assertEqual(result['score'], 65)
        self.assertEqual(result['information_coverage'], 80)
        self.assertEqual(result['details']['possible_score'], 85)
        self.assertEqual(len(result['unknown_criteria']), 1)

    def test_missing_category_renormalizes_and_all_unknown_is_not_zero(self):
        result = score_assessment(assessment(criterion()), 'Python', {'profile.skills': 'Python'})
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['details']['breakdown'][0]['weight'], 100)
        for data in (assessment(), assessment(criterion(status='unknown', field='', evidence=''))):
            result = score_assessment(data, 'Python', {})
            self.assertIsNone(result['score']); self.assertEqual(result['status'], 'insufficient')

    def test_fabricated_evidence_downgrades_to_unknown_and_source_quote_rejected(self):
        result = score_assessment(assessment(criterion()), 'Python', {'profile.skills': 'Java'})
        self.assertIsNone(result['score']); self.assertEqual(len(result['unknown_criteria']), 1)
        for description in ('Java', 'Pythonista'):
            with self.assertRaises(HTTPException): score_assessment(assessment(criterion()), description, {'profile.skills': 'Python'})
        deduplicated = score_assessment(assessment(criterion(), criterion()), 'Python', {'profile.skills': 'Python'})
        self.assertEqual(len(deduplicated['details']['criteria']), 1)

    def test_unfinished_education_cannot_receive_full_degree_credit(self):
        item = criterion('education', 'Có bằng đại học ngành CNTT', 'matched', 'profile.education', 'Sinh viên năm cuối ngành CNTT')
        result = score_assessment(assessment(item), item['requirement_quote'], {'profile.education': item['candidate_quote']})
        self.assertEqual(result['score'], 50)
        self.assertEqual(result['missing'][0]['status'], 'partial')
        allowed = dict(item, requirement_quote='Sinh viên năm cuối hoặc có bằng đại học ngành CNTT')
        result = score_assessment(assessment(allowed), allowed['requirement_quote'], {'profile.education': allowed['candidate_quote']})
        self.assertEqual(result['score'], 100)

    def test_one_tool_does_not_satisfy_an_entire_compound_requirement(self):
        item = criterion(quote='ROS/ROS2, Ubuntu Linux, Docker, Git.', evidence='Git')
        result = score_assessment(assessment(item), item['requirement_quote'], {'profile.skills': 'Git'})
        self.assertEqual(result['score'], 50)
        self.assertEqual(result['missing'][0]['status'], 'partial')

    def test_technical_tool_list_is_not_evidence_of_soft_skills(self):
        for quote in ('Tư duy hệ thống, giải quyết vấn đề.', 'Làm việc nhóm và độc lập.'):
            item = criterion(quote=quote, evidence='Python, FastAPI, MySQL, Git')
            result = score_assessment(assessment(item), quote, {'profile.skills': item['candidate_quote']})
            self.assertIsNone(result['score'])
            self.assertEqual(result['unknown_criteria'][0]['status'], 'unknown')
        item = criterion(quote='Làm việc nhóm và độc lập.', evidence='Làm việc nhóm')
        result = score_assessment(assessment(item), item['requirement_quote'], {'profile.skills': item['candidate_quote']})
        self.assertEqual(result['score'], 50)
        full = dict(item, candidate_quote='Teamwork, independently')
        result = score_assessment(assessment(full), item['requirement_quote'], {'profile.skills': full['candidate_quote']})
        self.assertEqual(result['score'], 100)

    def test_absence_is_not_unmet_and_explicit_shortfall_is_allowed(self):
        item = criterion(quote='Java', status='unmet', evidence='Python')
        result = score_assessment(assessment(item), 'Java', {'profile.skills': 'Python'})
        self.assertIsNone(result['score'])
        item = criterion('experience', '3 năm kinh nghiệm', 'unmet', 'profile.experience', 'Tổng kinh nghiệm: 1 năm kinh nghiệm')
        result = score_assessment(assessment(item), '3 năm kinh nghiệm', {'profile.experience': 'Tổng kinh nghiệm: 1 năm kinh nghiệm'})
        self.assertEqual(result['score'], 0); self.assertEqual(result['information_coverage'], 100)
        inferred = dict(item, candidate_quote='1 năm kinh nghiệm')
        result = score_assessment(assessment(inferred), '3 năm kinh nghiệm', {'profile.experience': '1 năm kinh nghiệm'})
        self.assertIsNone(result['score'])

    def test_sensitive_requirements_are_not_scored(self):
        item = criterion(quote='Nữ dưới 25 tuổi')
        result = score_assessment(assessment(item, criterion()), 'Nữ dưới 25 tuổi. Python.', {'profile.skills': 'Python'})
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['details']['excluded_sensitive'], 1)

    def test_exact_basic_skills_can_recover_unknown_without_inference(self):
        item = criterion(quote='Có thể sử dụng Git.', status='unknown', field='', evidence='')
        result = score_assessment(assessment(item), item['requirement_quote'], {'profile.skills': 'Python, Git'})
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['matched'][0]['candidate_quote'], 'Git')
        result = score_assessment(assessment(item), item['requirement_quote'], {'profile.projects': 'Git tracker'})
        self.assertIsNone(result['score'])
        result = score_assessment(assessment(item), item['requirement_quote'], {'profile.skills': 'Python; chưa biết Git'})
        self.assertIsNone(result['score'])
        advanced = dict(item, requirement_quote='Thành thạo Git trong 5 năm')
        result = score_assessment(assessment(advanced), advanced['requirement_quote'], {'profile.skills': 'Git'})
        self.assertIsNone(result['score'])

    def test_local_payload_excludes_contacts_and_uses_8192_schema(self):
        with patch.object(settings, 'ai_provider', 'ollama'), patch('app.evaluation_ai._post', return_value=response(criterion())) as post:
            result = evaluate_job({'profile': {'skills': 'Python', 'full_name': 'SECRET NAME', 'email': 'private@example.com'},
                                   'cv': {'phone': '0909123456'}}, {'description': 'Yêu cầu Python'})
            self.assertEqual(result['score'], 100)
            body = post.call_args.kwargs['json']; self.assertEqual(body['options']['num_ctx'], 8192)
            self.assertNotIn('private@example.com', str(body)); self.assertNotIn('SECRET NAME', str(body))
            self.assertNotIn('0909123456', str(body)); self.assertIn('format', body)
            self.assertEqual(post.call_args.args[0], 'http://127.0.0.1:11434/api/chat')

    def test_ai_errors_and_long_inputs_never_create_score(self):
        with patch.object(settings, 'ai_provider', 'ollama'):
            for result, code in [(response(done=False), 502), (response(reason='length'), 502),
                                 (httpx.Response(200, json={'message': {'content': '{}'}}), 502), (httpx.Response(503), 503)]:
                with patch('app.evaluation_ai._post', return_value=result):
                    with self.assertRaises(HTTPException) as exc: evaluate_job({}, {'description': 'Python'})
                    self.assertEqual(exc.exception.status_code, code)
            for error, code in [(httpx.ReadTimeout('timeout'), 504), (httpx.ConnectError('offline'), 503)]:
                with patch('app.evaluation_ai._post', side_effect=error):
                    with self.assertRaises(HTTPException) as exc: evaluate_job({}, {'description': 'Python'})
                    self.assertEqual(exc.exception.status_code, code)
            with patch('app.evaluation_ai._post') as post:
                with self.assertRaises(HTTPException) as exc: evaluate_job({}, {'description': 'Python ' * 3000})
                self.assertEqual(exc.exception.status_code, 422); post.assert_not_called()


class EvaluationAPITests(unittest.TestCase):
    setUp = test_week4.SearchTests.setUp
    tearDown = test_week4.SearchTests.tearDown
    register = test_week4.SearchTests.register
    prepare = test_week4.SearchTests.prepare
    factory = test_week4.SearchTests.factory
    enqueue = test_week4.SearchTests.enqueue

    def ready(self, two=False):
        cv = self.prepare(); run = self.enqueue(cv)
        rows = [test_week4.sample()]
        if two: rows.append(dict(test_week4.sample(), url='https://www.arbeitnow.com/jobs/second', title='Second job'))
        with patch('app.worker.fetch_jobs', return_value=rows): process_once(self.factory)
        return run

    def start(self, run):
        with patch.object(settings, 'ai_provider', 'ollama'):
            response = self.client.post(f"/api/searches/{run['id']}/evaluations")
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_auth_ownership_and_csrf(self):
        self.assertEqual(self.client.get('/api/evaluations/1').status_code, 401)
        run = self.ready(); batch = self.start(run)
        self.register(self.other, {'email': 'other-' + self.email, 'password': 'Test-password-123'})
        for path in (f"/api/evaluations/{batch['id']}", f"/api/searches/{run['id']}/evaluations"):
            self.assertEqual(self.other.get(path).status_code, 404)
        self.assertEqual(self.other.post(f"/api/evaluations/{batch['id']}/cancel").status_code, 404)
        self.assertEqual(self.other.post(f"/api/searches/{run['id']}/evaluations").status_code, 404)
        self.assertEqual(self.client.post(f"/api/searches/{run['id']}/evaluations", headers={'X-Requested-With': ''}).status_code, 403)

    def test_database_timestamps_share_the_application_utc_clock(self):
        run = self.ready(); batch = self.start(run)
        created = datetime.fromisoformat(batch['created_at'].rstrip('Z'))
        self.assertLess(abs((created - datetime.utcnow()).total_seconds()), 5)
        if self.mysql:
            offset = self.connection.exec_driver_sql('SELECT TIMESTAMPDIFF(SECOND, UTC_TIMESTAMP(), NOW())').scalar()
            self.assertEqual(offset, 0)

    def test_duplicate_pending_guard_cancel_and_no_jobs(self):
        cv = self.prepare(); run = self.enqueue(cv)
        self.assertEqual(self.client.post(f"/api/searches/{run['id']}/evaluations").status_code, 409)
        with patch('app.worker.fetch_jobs', return_value=[]): process_once(self.factory)
        self.assertEqual(self.client.post(f"/api/searches/{run['id']}/evaluations").status_code, 409)

    def test_worker_snapshot_ranking_and_preserves_prior_batch(self):
        run = self.ready(two=True); batch = self.start(run)
        self.assertEqual(self.client.post(f"/api/searches/{run['id']}/evaluations").status_code, 409)
        self.client.put('/api/profile', json={'full_name': 'Changed', 'skills': 'Java'})
        low = score_assessment(assessment(criterion(status='partial')), 'Python', {'profile.skills': 'Python'})
        high = score_assessment(assessment(criterion()), 'Python', {'profile.skills': 'Python'})
        with patch('app.evaluation_worker.evaluate_job', side_effect=[low, high]) as ai:
            process_evaluation_once(self.factory)
            self.assertEqual(ai.call_args.args[0]['profile']['skills'], 'Python')
        result = self.client.get(f"/api/evaluations/{batch['id']}").json()
        self.assertEqual(result['status'], 'completed'); self.assertEqual(result['processed_jobs'], 2)
        self.assertEqual([r['score'] for r in result['results']], [100, 50])
        with self.factory() as db:
            db.get(EvaluationBatch, batch['id']).created_at = datetime.utcnow() - timedelta(seconds=31); db.commit()
        newer = self.start(run)
        self.assertNotEqual(newer['id'], batch['id'])
        self.assertEqual(self.client.get(f"/api/evaluations/{batch['id']}").json()['results'], result['results'])
        self.assertEqual(len(self.client.get(f"/api/searches/{run['id']}/evaluations").json()['items']), 2)

    def test_partial_provider_failure_and_unknown_scores(self):
        run = self.ready(two=True); batch = self.start(run)
        unknown = score_assessment(assessment(criterion(status='unknown', field='', evidence='')), 'Python', {})
        with patch('app.evaluation_worker.evaluate_job', side_effect=[HTTPException(502, 'Invalid JSON'), unknown]):
            process_evaluation_once(self.factory)
        result = self.client.get(f"/api/evaluations/{batch['id']}").json()
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(all(row['score'] is None for row in result['results']))
        self.assertEqual(result['counts'], {'failed': 1, 'insufficient': 1})

    def test_tied_scores_rank_more_complete_evidence_first(self):
        run = self.ready(two=True); batch = self.start(run)
        less = score_assessment(assessment(criterion(), criterion(quote='SQL', status='unknown', field='', evidence='')), 'Python and SQL', {'profile.skills': 'Python'})
        more = score_assessment(assessment(criterion(status='partial')), 'Python', {'profile.skills': 'Python'})
        self.assertEqual(less['score'], more['score'])
        with patch('app.evaluation_worker.evaluate_job', side_effect=[less, more]): process_evaluation_once(self.factory)
        result = self.client.get(f"/api/evaluations/{batch['id']}").json()
        self.assertEqual([row['information_coverage'] for row in result['results']], [100, 50])

    def test_history_paginates_without_exposing_other_users(self):
        run = self.ready(); first = self.start(run)
        with self.factory() as db:
            owner = db.get(EvaluationBatch, first['id']).user_id
            for _ in range(20):
                db.add(EvaluationBatch(user_id=owner, search_run_id=run['id'], status='completed',
                    total_jobs=0, model='test-model', rubric_version='evidence-v1'))
            db.commit()
        page = self.client.get(f"/api/searches/{run['id']}/evaluations").json()
        self.assertEqual(len(page['items']), 20)
        older = self.client.get(f"/api/searches/{run['id']}/evaluations?before_id={page['next_before_id']}").json()
        self.assertEqual([row['id'] for row in older['items']], [first['id']])

    def test_offline_does_not_repeat_service_calls(self):
        run = self.ready(two=True); batch = self.start(run)
        with patch('app.evaluation_worker.evaluate_job', side_effect=HTTPException(503, 'offline')) as ai:
            process_evaluation_once(self.factory); self.assertEqual(ai.call_count, 1)
        result = self.client.get(f"/api/evaluations/{batch['id']}").json()
        self.assertEqual(result['status'], 'failed'); self.assertEqual(result['counts']['failed'], 2)

    def test_cancel_fences_inflight_result(self):
        run = self.ready(two=True); batch = self.start(run)
        def delayed(*args, **kwargs):
            self.client.post(f"/api/evaluations/{batch['id']}/cancel")
            return score_assessment(assessment(criterion()), 'Python', {'profile.skills': 'Python'})
        with patch('app.evaluation_worker.evaluate_job', side_effect=delayed): process_evaluation_once(self.factory)
        result = self.client.get(f"/api/evaluations/{batch['id']}").json()
        self.assertEqual(result['status'], 'cancelled')
        self.assertTrue(all(row['status'] == 'cancelled' and row['score'] is None for row in result['results']))

    def test_stale_worker_recovers_and_does_not_rerun_completed_job(self):
        run = self.ready(two=True); batch = self.start(run)
        with self.factory() as db:
            stored = db.get(EvaluationBatch, batch['id']); stored.status = 'running'; stored.worker_token = 'old'
            stored.heartbeat_at = datetime.utcnow() - timedelta(minutes=7)
            rows = db.scalars(select(Evaluation).where(Evaluation.batch_id == batch['id']).order_by(Evaluation.id)).all()
            rows[0].status = 'insufficient'; rows[1].status = 'running'; rows[1].attempts = 1
            db.commit()
        with patch('app.evaluation_worker.evaluate_job', return_value=score_assessment(assessment(criterion()), 'Python', {'profile.skills': 'Python'})) as ai:
            process_evaluation_once(self.factory); self.assertEqual(ai.call_count, 1)
        self.assertEqual(self.client.get(f"/api/evaluations/{batch['id']}").json()['status'], 'completed')

    def test_two_worker_interruptions_stop_retrying(self):
        run = self.ready(); batch = self.start(run)
        with self.factory() as db:
            stored = db.get(EvaluationBatch, batch['id']); stored.status = 'running'
            stored.heartbeat_at = datetime.utcnow() - timedelta(minutes=7)
            row = db.scalar(select(Evaluation).where(Evaluation.batch_id == batch['id']))
            row.status = 'running'; row.attempts = 2; db.commit()
        with patch('app.evaluation_worker.evaluate_job') as ai:
            process_evaluation_once(self.factory); ai.assert_not_called()
        self.assertEqual(self.client.get(f"/api/evaluations/{batch['id']}").json()['status'], 'failed')
