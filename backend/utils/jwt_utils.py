from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

def create_jwt_token(data: dict, expires_in: timedelta):
    secret_key = os.getenv('SECRET_KEY')
    algorithm = os.getenv('JWT_ENCODE_ALGORITHM', 'HS256')

    to_encode = data.copy()
    expire = datetime.utcnow() + expires_in
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt