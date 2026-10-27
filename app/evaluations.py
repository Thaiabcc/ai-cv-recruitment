from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts import current_user, mutation_guard
from app.config import settings
from app.database import get_db
from app.evaluation_ai import RUBRIC_VERSION
from app.models import Evaluation, EvaluationBatch, SearchRun, SearchRunJob, User

router = APIRouter(prefix='/api', tags=['Job evaluations'])
ACTIVE = ('queued', 'running')


def own_search(run_id, user_id, db):
    run = db.scalar(select(SearchRun).where(SearchRun.id == run_id, SearchRun.user_id == user_id))
    if not run: raise HTTPException(404, 'Không tìm thấy lượt tìm việc.')
    return run


def own_batch(batch_id, user_id, db):
    batch = db.scalar(select(EvaluationBatch).where(EvaluationBatch.id == batch_id, EvaluationBatch.user_id == user_id))
    if not batch: raise HTTPException(404, 'Không tìm thấy lượt đánh giá.')
    return batch


def batch_output(batch, db):
    counts = dict(db.execute(select(Evaluation.status, func.count()).where(Evaluation.batch_id == batch.id)
                             .group_by(Evaluation.status)).all())
    processed = sum(counts.get(status, 0) for status in ('completed', 'insufficient', 'failed', 'cancelled'))
    return {'id': batch.id, 'search_run_id': batch.search_run_id, 'status': batch.status,
            'model': batch.model, 'rubric_version': batch.rubric_version, 'total_jobs': batch.total_jobs,
            'processed_jobs': processed, 'counts': counts, 'created_at': batch.created_at.isoformat() + 'Z',
            'finished_at': batch.finished_at.isoformat() + 'Z' if batch.finished_at else None}


@router.post('/searches/{run_id}/evaluations', status_code=202, dependencies=[Depends(mutation_guard)])
def create_batch(run_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    run = own_search(run_id, user.id, db)
    if run.status not in ('completed', 'partial'):
        raise HTTPException(409, 'Hãy đợi lượt tìm việc hoàn thành trước khi đánh giá.')
    if settings.ai_provider != 'ollama': raise HTTPException(503, 'Hãy cấu hình Ollama local để đánh giá công việc.')
    if db.scalar(select(EvaluationBatch.id).where(EvaluationBatch.user_id == user.id, EvaluationBatch.status.in_(ACTIVE))):
        raise HTTPException(409, 'Bạn có lượt đánh giá đang chờ hoặc đang chạy. Hãy xem tiến độ hoặc dừng lượt đó.')
    recent = db.scalar(select(EvaluationBatch).where(EvaluationBatch.user_id == user.id)
                       .order_by(EvaluationBatch.id.desc()).limit(1))
    if recent and recent.created_at > datetime.utcnow() - timedelta(seconds=30):
        raise HTTPException(429, 'Hãy đợi 30 giây giữa hai lượt đánh giá.')
    jobs = db.scalars(select(SearchRunJob).where(SearchRunJob.search_run_id == run.id).order_by(SearchRunJob.job_id)).all()
    if not jobs: raise HTTPException(409, 'Lượt tìm chưa có tin để đánh giá.')
    batch = EvaluationBatch(user_id=user.id, search_run_id=run.id, status='queued',
                            model=settings.ollama_model, rubric_version=RUBRIC_VERSION, total_jobs=len(jobs))
    db.add(batch); db.flush()
    for job in jobs:
        db.add(Evaluation(batch_id=batch.id, search_run_id=run.id, job_id=job.job_id,
                          rubric_version=RUBRIC_VERSION, status='pending'))
    db.commit(); db.refresh(batch)
    return batch_output(batch, db)


@router.get('/searches/{run_id}/evaluations')
def list_batches(run_id: int, before_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    own_search(run_id, user.id, db)
    query = select(EvaluationBatch).where(EvaluationBatch.search_run_id == run_id, EvaluationBatch.user_id == user.id)
    if before_id is not None: query = query.where(EvaluationBatch.id < before_id)
    batches = db.scalars(query.order_by(EvaluationBatch.id.desc()).limit(21)).all()
    return {'items': [batch_output(batch, db) for batch in batches[:20]],
            'next_before_id': batches[19].id if len(batches) > 20 else None}


@router.get('/evaluations/{batch_id}')
def get_batch(batch_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    batch = own_batch(batch_id, user.id, db)
    results = db.scalars(select(Evaluation).where(Evaluation.batch_id == batch.id).order_by(
        Evaluation.score.is_(None), Evaluation.score.desc(), Evaluation.information_coverage.desc(), Evaluation.job_id)).all()
    jobs = {row.job_id: row.snapshot for row in db.scalars(select(SearchRunJob).where(SearchRunJob.search_run_id == batch.search_run_id))}
    return {**batch_output(batch, db), 'results': [{
        'id': result.id, 'job_id': result.job_id, 'job': jobs.get(result.job_id), 'status': result.status,
        'score': float(result.score) if result.score is not None else None,
        'information_coverage': float(result.information_coverage) if result.information_coverage is not None else None,
        'matched': result.matched, 'missing': result.missing, 'unknown_criteria': result.unknown_criteria,
        'explanation': result.explanation, 'suggestions': result.suggestions, 'details': result.details}
        for result in results]}


@router.post('/evaluations/{batch_id}/cancel', dependencies=[Depends(mutation_guard)])
def cancel_batch(batch_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Serialize against worker commits so a cancelled batch cannot be overwritten.
    batch = db.scalar(select(EvaluationBatch).where(EvaluationBatch.id == batch_id,
                      EvaluationBatch.user_id == user.id).with_for_update())
    if not batch: raise HTTPException(404, 'Không tìm thấy lượt đánh giá.')
    if batch.status not in ACTIVE: return batch_output(batch, db)
    batch.status = 'cancelled'; batch.worker_token = None; batch.finished_at = datetime.utcnow()
    for result in db.scalars(select(Evaluation).where(Evaluation.batch_id == batch.id, Evaluation.status.in_(('pending', 'running')))):
        result.status = 'cancelled'; result.explanation = 'Đã dừng theo yêu cầu; tin này chưa được đánh giá.'
    db.commit()
    return batch_output(batch, db)
