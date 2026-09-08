from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_error
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles: str):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted for this role")
        return user
    return _checker


require_admin = require_roles("admin")
require_admin_or_member = require_roles("admin", "member")


def require_feature(*features: str):
    """Gate an endpoint on the admin-editable permissions grid.

    Passing several features means "any one of these is enough" - used where a
    screen is reachable from more than one place. This is the server-side half
    of the grid: the sidebar hides what a role cannot use, and this makes sure
    typing the URL or calling the API directly gets the same answer.
    """
    def _checker(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        from app.services import permissions as perms

        if not any(perms.is_allowed(db, user.role, f) for f in features):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not permitted for this role",
            )
        return user
    return _checker
