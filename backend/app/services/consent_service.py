from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User


def has_valid_consent(user: User) -> bool:
    return (
        user.consent_given_at is not None
        and user.consent_version == settings.consent_version
    )


async def record_consent(
    user: User,
    db: AsyncSession,
    version: str | None = None,
) -> None:
    user.consent_version = version or settings.consent_version
    user.consent_given_at = datetime.now(timezone.utc)
    await db.commit()
