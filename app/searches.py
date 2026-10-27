import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts import current_user, mutation_guard
from app.cvs import own_cv, saved_profile
from app.database import get_db
from app.models import RecruitmentSource, SearchRun, SearchRunJob, User
from app.job_sources import SOURCES

router = APIRouter(prefix='/api/searches', tags=['Job searches'])


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    cv_id: int = Field(gt=0)
    keywords: str = Field(default='', max_length=300)
    location: str | None = Field(default=None, max_length=200)
    source_ids: list[int] | None = Field(default=None, max_length=3)


def output(run):
    return {'id': run.id, 'cv_id': run.cv_id, 'status': run.status,
            'query': run.query_snapshot, 'source_errors': run.source_errors or {},
            'created_at': run.created_at.isoformat() + 'Z',
            'finished_at': run.finished_at.isoformat() + 'Z' if run.finished_at else None}


@router.get('/sources')
def sources(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{'id': s.id, 'name': s.name, 'enabled': s.enabled and s.domain in SOURCES,
             'country': SOURCES.get(s.domain, {}).get('country', 'VN'),
             'scope': SOURCES.get(s.domain, {}).get('scope', 'Chưa tích hợp; chưa bật thu thập')}
            for s in db.scalars(select(RecruitmentSource).order_by(RecruitmentSource.id))]


@router.get('')
def history(before_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(SearchRun).where(SearchRun.user_id == user.id)
    if before_id is not None: query = query.where(SearchRun.id < before_id)
    runs = db.scalars(query.order_by(SearchRun.id.desc()).limit(21)).all()
    return {'items': [output(r) for r in runs[:20]], 'next_before_id': runs[19].id if len(runs) > 20 else None}


@router.post('', status_code=202, dependencies=[Depends(mutation_guard)])
def create(data: SearchRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Serialize per-account enqueue, including double clicks from different browser tabs.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    parent = own_cv(data.cv_id, user.id, db)
    snapshot = saved_profile(user, db)
    active = db.scalar(select(SearchRun).where(SearchRun.user_id == user.id,
        SearchRun.status.in_(['queued', 'running'])))
    if active: raise HTTPException(409, 'Bạn có lượt tìm việc đang chờ hoặc đang chạy. Hãy xem tiến độ lượt đó.')
    recent = db.scalar(select(SearchRun).where(SearchRun.user_id == user.id).order_by(SearchRun.id.desc()).limit(1))
    if recent and recent.created_at > datetime.utcnow() - timedelta(seconds=30):
        raise HTTPException(429, 'Hãy đợi 30 giây giữa hai lượt tìm việc.')
    sources = db.scalars(select(RecruitmentSource).where(RecruitmentSource.enabled.is_(True),
        RecruitmentSource.domain.in_(SOURCES))).all()
    if data.source_ids is not None:
        requested = set(data.source_ids)
        if not requested or not requested.issubset({source.id for source in sources}):
            raise HTTPException(422, 'Hãy chọn ít nhất một nguồn đã được bật và hỗ trợ.')
        sources = [source for source in sources if source.id in requested]
    elif any(SOURCES[source.domain]['country'] == 'VN' for source in sources):
        sources = [source for source in sources if SOURCES[source.domain]['country'] == 'VN']
    if not sources: raise HTTPException(503, 'Chưa bật nguồn tuyển dụng đã tích hợp.')
    raw = data.keywords or (parent.content['document'].get('title', '') + ',' + parent.content['document'].get('skills', ''))
    keywords = list(dict.fromkeys(word.strip()[:60] for word in re.split(r'[,;\n]+', raw) if word.strip()))[:12]
    if not keywords: raise HTTPException(422, 'Hãy bổ sung vị trí/kỹ năng trong CV hoặc nhập từ khóa.')
    run = SearchRun(user_id=user.id, cv_id=parent.id, status='queued', query_snapshot={
        'keywords': keywords, 'location': snapshot.get('location', '') if data.location is None else data.location,
        'profile': snapshot, 'cv': parent.content['document'], 'source_ids': [s.id for s in sources],
        'scope': '; '.join(SOURCES[source.domain]['name'] + ': ' + SOURCES[source.domain]['scope'] for source in sources)
                 + '. Bước tìm tin lọc từ khóa/địa điểm, chưa lọc lương; có thể đánh giá bằng Ollama sau khi tìm xong.'})
    db.add(run); db.commit(); db.refresh(run)
    return output(run)


@router.get('/{run_id}')
def detail(run_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = db.scalar(select(SearchRun).where(SearchRun.id == run_id, SearchRun.user_id == user.id))
    if not run: raise HTTPException(404, 'Không tìm thấy lượt tìm việc.')
    jobs = db.scalars(select(SearchRunJob).where(SearchRunJob.search_run_id == run.id).order_by(SearchRunJob.job_id)).all()
    return {**output(run), 'jobs': [j.snapshot for j in jobs]}
