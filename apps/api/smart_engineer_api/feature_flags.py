"""Feature-flag evaluation. A flag that does not exist is off."""

import re

from sqlalchemy.orm import Session

from .db import FeatureFlag

_KEY = re.compile(r"[a-z][a-z0-9_.-]{0,99}")


def _validated(key: str) -> str:
    if not _KEY.fullmatch(key):
        raise ValueError(
            "Feature flag keys must start with a lowercase letter and contain only "
            "lowercase letters, digits, '.', '_' or '-' (at most 100 characters)."
        )
    return key


def is_enabled(session: Session, key: str, *, default: bool = False) -> bool:
    flag = session.get(FeatureFlag, _validated(key))
    return default if flag is None else flag.enabled


def set_flag(
    session: Session, key: str, enabled: bool, *, description: str | None = None
) -> FeatureFlag:
    flag = session.get(FeatureFlag, _validated(key))
    if flag is None:
        flag = FeatureFlag(key=key, enabled=enabled, description=description)
        session.add(flag)
    else:
        flag.enabled = enabled
        if description is not None:
            flag.description = description
    session.flush()
    return flag
