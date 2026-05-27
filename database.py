from typing import Optional
import hashlib
import secrets
from datetime import datetime

from sqlmodel import Field, Session, SQLModel, create_engine, select


DATABASE_URL = "sqlite:///database.db"

engine = create_engine(DATABASE_URL, echo=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    salt: str
    role: str = "user"

class DetectionEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    action: str
    distance: float | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()

    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    test_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(test_hash, password_hash)


def get_user_by_username(username: str):
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        return session.exec(statement).first()


def create_user(username: str, password: str, role: str = "user"):
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        existing_user = session.exec(statement).first()

        if existing_user:
            return None

        password_hash, salt = hash_password(password)

        user = User(
            username=username,
            password_hash=password_hash,
            salt=salt,
            role=role
        )

        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)

    if not user:
        return None

    if not verify_password(password, user.password_hash, user.salt):
        return None

    return user


def seed_default_admin():
    create_user("admin", "admin", role="admin")

def get_all_users():
    with Session(engine) as session:
        statement = select(User).order_by(User.id)
        return session.exec(statement).all()


def delete_user(user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)

        if not user:
            return False

        session.delete(user)
        session.commit()
        return True
    
def count_admin_users() -> int:
    with Session(engine) as session:
        statement = select(User).where(User.role == "admin")
        return len(session.exec(statement).all())


def get_user_by_id(user_id: int):
    with Session(engine) as session:
        return session.get(User, user_id)
    
def create_detection_event(name: str, action: str, distance: float | None = None):
    with Session(engine) as session:
        event = DetectionEvent(
            name=name,
            action=action,
            distance=distance
        )

        session.add(event)
        session.commit()
        session.refresh(event)
        return event


def get_recent_detection_events(limit: int = 50):
    with Session(engine) as session:
        statement = select(DetectionEvent).order_by(DetectionEvent.id.desc()).limit(limit)
        return session.exec(statement).all()


def delete_detection_event(event_id: int):
    with Session(engine) as session:
        event = session.get(DetectionEvent, event_id)

        if not event:
            return False

        session.delete(event)
        session.commit()
        return True


def clear_detection_events():
    with Session(engine) as session:
        events = session.exec(select(DetectionEvent)).all()

        for event in events:
            session.delete(event)

        session.commit()