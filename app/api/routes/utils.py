from fastapi import APIRouter
from app.db.redis import logs_redis
from app.tasks.tasks import offload_audit_logs_to_loki

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/trigger-log-offload")
async def trigger_log_offload():
    # Manually trigger the log offloading task
    task_id = offload_audit_logs_to_loki()
    return {"status": "log offload task triggered", "task_id": str(task_id)}
