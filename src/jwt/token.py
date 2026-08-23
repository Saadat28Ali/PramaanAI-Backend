import jwt;
from dotenv import dotenv_values;
from time import time;

secret: str = dotenv_values(".env")["SECRET"];

def createToken(payload: dict) -> str:
	payload["exp"] = round(time(), 2) + float(30*24*60*60); # token has validity of 30 days
	return jwt.encode(payload, secret, algorithm="HS256");

def verifyToken(token: str) -> bool:
	try:
		payload: dict = jwt.decode(token, secret, algorithms=["HS256"]);
	except jwt.exceptions.InvalidTokenError as e:
		print(f"Token error: {e}");
		return False;
	return True;
