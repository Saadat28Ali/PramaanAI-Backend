# IMPORTS
# -----------------------------------------------
from flask import Flask, request;
from flask_cors import CORS;
from numpy import frombuffer, uint8;
from PIL import Image;
from cv2 import imdecode, IMREAD_COLOR, imread;

from os import path, mkdir, scandir, remove;
from time import strftime;
from copy import deepcopy;
from .hash.hashf import hashIt;

from .ai.__init__ import *
from .db.queries import testQuery, createUser, searchUser, insertDocument, gAuditLogsByUser;
from .jwt.token import createToken;
from .util import getTokenData;

# ------------------------------------------------

app = Flask(__name__);
CORS(app);

try:
	mkdir(path.abspath("./ocrfiles"));
except FileExistsError:
	pass;

RES_TEMPLATE = {
	"sucess": False,
	"msg": "Template msg",
	"details": {}
};

# FUNCTIONS
# ------------------------------------------------
def buildRes(success = False, msg = "", details = {}) -> dict:
	return {
		"success": success,
		"msg": msg,
		"details": details
	};

# ENDPOINTS
# ------------------------------------------------

@app.route('/', methods=["GET", "POST"])
def hello_world():
	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if request.method == "POST":
		# db test
		if "dbtest" in data:
			result: bool = testQuery();
			ret = buildRes(result, "DB is working." if result else "DB failed.");
	else:
		ret = buildRes(True, "The server is working.");

	return ret;

@app.route("/ocr", methods=["POST"])
def ocr_upload():
	ret: dict = deepcopy(RES_TEMPLATE);

	# Getting token data
	# --------------------------------------------------
	token_data_result: dict = getTokenData(request);
	if not token_data_result["success"]:
		return buildRes(msg="Could not get token data.", details={
			"error": token_data_result["error"]
		});

	token_data: dict = token_data_result["token_data"];

	# Getting user data
	# --------------------------------------------------

	user_data_fetch_result: dict = searchUser(token_data["email"]);
	if (not user_data_fetch_result["success"]):
		return buildRes(False, "Could not find user due to DB error.", {
			"dberror": user_data_fetch_result["error"]
		});

	user_data = user_data_fetch_result["row"];
	if (user_data is None):
		return buildRes(False, "Could not find user.");

	# Saving the image file
	# --------------------------------------------------
	# trying to make the ./ocrfiles directory
	# if it already exists, this part is skipped

	try:
		mkdir(path.abspath("./ocrfiles"));
	except FileExistsError:
		pass;

	# saving the received file in ./ocrfiles
	# the filename is based on time of upload

	if "image" not in request.files:
		ret = buildRes(msg="No image uploaded");

	filename: str = f"./ocrfiles/{strftime('%H-%M-%S %d-%m-%Y')}.png";
	with open(path.abspath(filename), "wb") as fh:
		request.files["image"].save(fh);
		print(f"File saved as {filename}.");

	# Inserting document in DB
	# --------------------------------------------------
	insert_document_result: dict = insertDocument(
		user_id = user_data["user_id"],
		document_type = "passport",
		file_path = path.abspath(filename),
	);
	if (not insert_document_result["success"]):
		return buildRes(msg="Could not add document to DB.", details={
			"dberror": result["error"]
		});

	# Passing image data into model
	# --------------------------------------------------
	pipeline = DocuNetPipeline();
	img = imread(filename, IMREAD_COLOR);

	if img is None:
		ret = buildRes(msg = "Invalid image.");

	model_result_dict: dict = {};
	with open(path.abspath(filename), "rb") as fh:
		model_result = pipeline.process(img);
		model_result_dict: dict = result.to_dict();

	# Inserting screening in DB
	# --------------------------------------------------

	# Returning final result
	# --------------------------------------------------

#	ret = buildRes(True, "Model run.", {**model_result_dict["tamper_detection"]});
	return buildRes(True, "Model run.", {**model_result_dict});

@app.route("/login", methods=["POST"])
def login():
	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if not ("email" in data and "password" in data and "role" in data):
		return buildRes(msg="Request JSON body must have keys email, password and role.");

	# Getting user data
	# --------------------------------------------------
	search_result: dict = searchUser(data["email"]);
	if not search_result["success"]:
		return buildRes(msg="User could not be found due to DB Error.", details={
			"email": data["email"],
			"password": data["password"],
			"role": data["role"],
			"dberror": search_result["error"]
		});

	user_data: dict | None = search_result["row"];
	if user_data is None:
		return buildRes(msg="User not found.", details={
			"email": data["email"],
			"password": data["password"],
			"role": data["role"],
		});

	# Matching password and returning final result
	# --------------------------------------------------
	if user_data["password_hash"] == data["password"]:
		# password correct
		ret = buildRes(msg="Password verified.", details={
			"email": data["email"],
			"password": data["password"],
			"role": data["role"],
			"token": createToken({
				"email": data["email"],
				"password": data["password"],
				"role": data["role"]
			})
		});
	else:
		# password incorrect
		ret = buildRes(msg="Password incorrect.", details={
			"email": data["email"],
			"password": data["password"],
			"role": data["role"]
		});
	return ret;

@app.route("/register", methods=["POST"])
def register():

	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if not ("name" in data and "email" in data and "password" in data and "role" in data):
		return buildRes(msg="Request JSON data must have keys email, password and role.");

	# Getting user data
	# --------------------------------------------------
	search_result: dict = searchUser(data["email"]);
	if not search_result["success"]:
		return buildRes(msg="User could not be found due to DB error.", details={
			"dberror": search_result["error"]
		});
	user_data: dict | None = search_result;

	if user_data is not None:
		return buildRes(msg="User already exists.", details={
			data["email"],
			data["name"],
			data["password"],
			data["role"]
		});

	# Creating new user in DB
	# --------------------------------------------------
	if (data["role"] not in {"officer", "admin"}):
		data["role"] = "officer";

	create_user_result: dict = createUser(data["name"], data["email"], data["password"], data["role"]);
	if not create_user_result["success"]:
		return buildRes(False, "User could not be created. DB Error.", {
			"name": data["name"],
			"email": data["email"],
			"password": data["password"],
			"role": data["role"],
			"dberror": result["message"]
		});

	# Returning final result
	# --------------------------------------------------
	return buildRes(True, "User has been created.", {
		"name": data["name"],
		"email": data["email"],
		"password": data["password"],
		"role": data["role"]
	});

@app.route("/verifyToken", methods=["POST"])
def verifyJWTToken():
	ret: dict = deepcopy(RES_TEMPLATE);

	# Getting token data
	# --------------------------------------------------
	token_data_result: dict = getTokenData(request);
	if not token_data_result["success"]:
		return buildRes(msg="Could not get token data.", details={
			"error": token_data_result["error"]
		});

	return buildRes(True, "Token is valid.", {});

@app.route("/audit_log", methods=["POST"])
def getAuditHistory():
	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	# Getting token data
	# --------------------------------------------------
	token_data_result: dict = getTokenData(request);
	if not token_data_result["success"]:
		return buildRes(msg="Could not get token data.", details={
			"error": token_data_result["error"]
		});

	token_data: dict = token_data_result["token_data"];

	# Getting user data
	# --------------------------------------------------

	user_data_fetch_result: dict = searchUser(token_data["email"]);
	if (not user_data_fetch_result["success"]):
		return buildRes(False, "Could not find user due to DB error.", {
			"dberror": user_data_fetch_result["error"]
		});

	user_data = user_data_fetch_result["row"];
	if (user_data is None):
		return buildRes(False, "Could not find user.");

	# Fetching audit logs
	# --------------------------------------------------
	audit_logs_fetch_result: dict = getAuditLogsByUser(user_data["user_id"], data.get("limit"), data.get("offset"));
	if (not audit_logs_fetch_result["success"]):
		return buildRes(msg="Could not fetch audit logs due to DB error.", details={
			"dberror": audit_logs_fetch_result["error"]
		});

	# Returning final result
	# --------------------------------------------------
	return buildRes(True, "Fetched audit logs by user.", audit_logs_fetch_result["rows"]);

@app.route("/dashboard", methods=["POST"])
def dashboard():
	

# MAIN
# ------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000);
