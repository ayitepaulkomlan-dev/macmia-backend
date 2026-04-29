"""
routers/auth.py — Endpoints d'authentification MACMIA
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import sqlite3
import logging

from database import (
    get_db, hash_password, verify_password,
    create_session, get_user_by_token, delete_session,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/register")
async def register(req: RegisterRequest):
    if len(req.username.strip()) < 2:
        raise HTTPException(400, "Nom d'utilisateur trop court (min 2 caractères)")
    if len(req.password) < 6:
        raise HTTPException(400, "Mot de passe trop court (min 6 caractères)")
    if "@" not in req.email:
        raise HTTPException(400, "Adresse email invalide")

    conn = get_db()
    try:
        pw_hash = hash_password(req.password)
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (req.username.strip(), req.email.lower().strip(), pw_hash),
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        token = create_session(user_id)
        logger.info(f"Nouveau compte créé : {req.username.strip()}")
        return {"token": token, "username": req.username.strip()}
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if "username" in msg:
            raise HTTPException(409, "Ce nom d'utilisateur est déjà pris")
        if "email" in msg:
            raise HTTPException(409, "Cette adresse email est déjà utilisée")
        raise HTTPException(409, "Compte déjà existant")
    finally:
        conn.close()


@router.post("/auth/login")
async def login(req: LoginRequest):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE email = ?",
            (req.email.lower().strip(),),
        ).fetchone()
        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(401, "Email ou mot de passe incorrect")
        token = create_session(row["id"])
        return {"token": token, "username": row["username"]}
    finally:
        conn.close()


@router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        delete_session(authorization[7:])
    return {"ok": True}


@router.get("/auth/me")
async def me(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Non authentifié")
    user = get_user_by_token(authorization[7:])
    if not user:
        raise HTTPException(401, "Session expirée ou invalide")
    return {"username": user["username"], "email": user["email"]}
