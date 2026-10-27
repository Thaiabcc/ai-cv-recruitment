"""Run separately: python -m app.worker [--once]. Durable MySQL queue."""
import argparse
import hashlib
import time
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.job_sources import SOURCES, fetch_jobs, matches
from app.models import Job, RecruitmentSource, SearchRun, SearchRunJob


def process_once(session_factory=SessionLocal):
    with session_factory() as db:
        now = datetime.utcnow()
        # A crashed worker cannot leave a run permanently running; explicit failure permits retry.
        db.execute(update(SearchRun).where(SearchRun.status == 'running',
            SearchRun.started_at < now - timedelta(minutes=10)).values(status='failed', finished_at=now,
            source_errors={'worker': 'Tác vụ gián đoạn hoặc quá hạn. Hãy tạo lượt tìm mới.'}))
        run = db.scalar(select(SearchRun).where(SearchRun.status == 'queued').order_by(SearchRun.id)
                        .with_for_update(skip_locked=True).limit(1))
        if not run:
            db.commit(); return False
        run.status = 'running'; run.started_at = now
        run_id, query = run.id, run.query_snapshot
        db.commit()
    errors = {}; successful = 0
    try:
        for source_id in query['source_ids']:
            with session_factory() as db:
                source = db.get(RecruitmentSource, source_id)
                if not source or not source.enabled or source.domain not in SOURCES:
                    errors[str(source_id)] = 'Nguồn đã tắt hoặc chưa được hỗ trợ.'; continue
                domain, source_name = source.domain, source.name
            try:
                result = fetch_jobs(domain, query)
                rows = result['jobs'] if isinstance(result, dict) else result
                warnings = result.get('warnings', []) if isinstance(result, dict) else []
                with session_factory() as db:
                    seen = set()
                    for row in rows:
                        if not matches(row, query): continue
                        digest = hashlib.sha256(row['url'].encode()).hexdigest()
                        if digest in seen: continue
                        seen.add(digest)
                        job = db.scalar(select(Job).where(Job.url_hash == digest))
                        if not job:
                            job = Job(source_id=source_id, url_hash=digest, **{key: row[key] for key in
                                ('url', 'title', 'company', 'location', 'salary_text', 'description')},
                                requirements={'tags': row['tags'], 'remote': row['remote']})
                            try:
                                with db.begin_nested():
                                    db.add(job); db.flush()
                            except IntegrityError:
                                # Another worker may have inserted this URL since our first read.
                                job = db.scalar(select(Job).where(Job.url_hash == digest).with_for_update())
                                if job is None: raise
                        db.add(SearchRunJob(search_run_id=run_id, job_id=job.id, snapshot=row))
                    db.commit()
                successful += 1
                if warnings: errors[str(source_id)] = source_name + ': ' + ' '.join(warnings)
            except Exception:
                # Provider errors never expose credentials, raw HTML or stack traces to the UI.
                errors[str(source_id)] = source_name + ': không thu thập được nguồn. Hãy thử lại sau.'
    finally:
        with session_factory() as db:
            run = db.get(SearchRun, run_id)
            if run.status == 'running':
                run.status = ('partial' if errors else 'completed') if successful else 'failed'
                run.source_errors = errors
                run.finished_at = datetime.utcnow()
                db.commit()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    from app.evaluation_worker import process_evaluation_once
    try:
        while True:
            # Each iteration services both queues; evaluation progress is persisted per job.
            searched = process_once()
            evaluated = process_evaluation_once()
            worked = searched or evaluated
            if args.once: break
            if not worked: time.sleep(3)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__': main()
