"""
Registration, login, logout, and "who am I" endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
import models
import schemas
from auth import hash_password, verify_password, create_access_token, get_current_user, COOKIE_NAME

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 1 week, matches token expiry


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, response: Response, db: Session = Depends(get_db)):
    user = models.User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    db.refresh(user)

    token = create_access_token(user.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=COOKIE_MAX_AGE, samesite="lax")
    return user


@router.post("/login", response_model=schemas.UserOut)
def login(payload: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=COOKIE_MAX_AGE, samesite="lax")
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Logged out"}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
