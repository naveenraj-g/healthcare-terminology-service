from dependency_injector import containers, providers
from app.core.database import Database
from app.core.config import settings


class CoreContainer(containers.DeclarativeContainer):
    database = providers.Singleton(
        Database,
        db_url=settings.TERMINOLOGY_DATABASE_URL,
    )
