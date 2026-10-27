"""Resumable evaluation batches, heartbeat and fencing against stale/cancelled workers."""
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.database import SessionLocal
from app.evaluation_ai import evaluate_job
from app.models import Evaluation, EvaluationBatch, SearchRun, SearchRunJob


def process_evaluation_once(session_factory=SessionLocal):
    with session_factory() as db:
        stale = db.scalars(select(EvaluationBatch).where(EvaluationBatch.status == 'running',
            EvaluationBatch.heartbeat_at < datetime.utcnow() - timedelta(minutes=6)).with_for_update(skip_locked=True)).all()
        for batch in stale:
            batch.status = 'queued'; batch.worker_token = None
            for row in db.scalars(select(Evaluation).where(Evaluation.batch_id == batch.id, Evaluation.status == 'running')):
                row.status = 'pending' if row.attempts < 2 else 'failed'
                if row.status == 'failed': row.explanation = 'Worker gián đoạn hai lần. Hãy tạo lượt đánh giá mới.'
        db.flush()
        batch = db.scalar(select(EvaluationBatch).where(EvaluationBatch.status == 'queued').order_by(EvaluationBatch.id)
                          .with_for_update(skip_locked=True).limit(1))
        if not batch: db.commit(); return False
        token = str(uuid4()); batch.worker_token = token; batch.status = 'running'
        batch.started_at = batch.started_at or datetime.utcnow(); batch.heartbeat_at = datetime.utcnow()
        batch_id, model = batch.id, batch.model
        snapshot = db.get(SearchRun, batch.search_run_id).query_snapshot
        row_ids = list(db.scalars(select(Evaluation.id).where(Evaluation.batch_id == batch_id,
                          Evaluation.status == 'pending').order_by(Evaluation.id)))
        db.commit()
    service_error = None
    for row_id in row_ids:
        with session_factory() as db:
            batch = db.scalar(select(EvaluationBatch).where(EvaluationBatch.id == batch_id).with_for_update())
            if batch.status != 'running' or batch.worker_token != token: return True
            row = db.get(Evaluation, row_id)
            if row.status != 'pending': continue
            row.status = 'running'; row.attempts += 1; batch.heartbeat_at = datetime.utcnow()
            stored = db.get(SearchRunJob, (row.search_run_id, row.job_id))
            job = stored.snapshot if stored else {}
            db.commit()
        try:
            if service_error: raise HTTPException(503, service_error)
            result = evaluate_job(snapshot, job, model=model)
        except HTTPException as error:
            result = {'status': 'failed', 'score': None, 'information_coverage': None,
                      'matched': [], 'missing': [], 'unknown_criteria': [],
                      'explanation': str(error.detail), 'suggestions': [], 'details': {'error_status': error.status_code}}
            if error.status_code == 503: service_error = str(error.detail)
        except Exception:
            result = {'status': 'failed', 'score': None, 'information_coverage': None, 'matched': [], 'missing': [],
                      'unknown_criteria': [], 'explanation': 'Không xử lý được đánh giá; chưa tạo điểm cho tin này.',
                      'suggestions': [], 'details': {'error_status': 500}}
        with session_factory() as db:
            batch = db.scalar(select(EvaluationBatch).where(EvaluationBatch.id == batch_id).with_for_update())
            if batch.status != 'running' or batch.worker_token != token: return True
            row = db.get(Evaluation, row_id)
            for key, value in result.items(): setattr(row, key, value)
            row.evaluated_at = datetime.utcnow(); batch.heartbeat_at = datetime.utcnow()
            db.commit()
    with session_factory() as db:
        batch = db.scalar(select(EvaluationBatch).where(EvaluationBatch.id == batch_id).with_for_update())
        if batch.status != 'running' or batch.worker_token != token: return True
        statuses = list(db.scalars(select(Evaluation.status).where(Evaluation.batch_id == batch_id)))
        failed = statuses.count('failed')
        batch.status = 'failed' if failed == len(statuses) else 'partial' if failed else 'completed'
        batch.finished_at = datetime.utcnow(); batch.worker_token = None
        db.commit()
    return True
