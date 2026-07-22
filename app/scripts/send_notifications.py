from app.db import init_db
from app.notifications import deliver_pending

init_db()
print(deliver_pending())
