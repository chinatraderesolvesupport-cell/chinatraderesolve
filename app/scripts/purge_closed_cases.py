from app.config import settings
from app.db import init_db, soft_delete_expired

init_db()
print({"anonymized": soft_delete_expired(settings.retention_days), "retention_days": settings.retention_days})
