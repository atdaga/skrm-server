from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.schemas.user import UserInDB

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "fccd6f72cca5af6c24e6fbff3c106f0f27a6e0d77f56ac505416f894da6a5cbf"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user(username: str):
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        print(f"AD: User dict: {user_dict}")
        return UserInDB(**user_dict)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = get_user(username)
    if user is not None and verify_password(password, user.hashed_password):
        return user


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(f"AD: Encoded JWT: {encoded_jwt}")
    return encoded_jwt
