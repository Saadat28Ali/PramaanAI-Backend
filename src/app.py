# IMPORTS
# -----------------------------------------------
from flask import Flask, request;
from flask_cors import CORS;

from os import path, mkdir, scandir, remove, getcwd;
from time import strftime;
from copy import deepcopy;
from .hash.hashf import hashIt;

# from .ai.__init__ import *
from .db.queries import testQuery, createUser, searchUser, insertDocument, getAuditLogsByUser, insertAuditLog, getDashboardMetrics;
from .jwt.token import createToken;
from .util import getTokenData, checkDictShape;
from .external_ai.main import external_ocr;


# GLOBALS
# ------------------------------------------------

ROOT_DIR: str = path.abspath(getcwd());

# ------------------------------------------------

app = Flask(__name__);
CORS(app);

try:
	mkdir(path.abspath(path.join(ROOT_DIR,"./ocrfiles")));
except FileExistsError:
	pass;

RES_TEMPLATE = {
	"success": False,
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
			ret = buildRes(result, "DB is working." if result else "DB failed.", {});
	else:
		ret = buildRes(True, "The server is working.");

	return ret;

@app.route("/ocr", methods=["POST"])
async def ocr_upload():
	ret: dict = deepcopy(RES_TEMPLATE);
#	data: dict = request.get_json();
	data: dict = {
		"document_type": request.form.get("document_type")
	};

	if data["document_type"] is None:
		return buildRes(False, "Request JSON must contain key document_type.");

#	if not checkDictShape(data, {"document_type"}):
#		return buildRes(False, "Request JSON must contain key document_type.");

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
		mkdir(path.abspath(path.join(ROOT_DIR, "./ocrfiles")));
	except FileExistsError:
		pass;

	# saving the received file in ./ocrfiles
	# the filename is based on time of upload

	if "image" not in request.files:
		ret = buildRes(msg="No image uploaded");
		return ret;

	filename: str = path.abspath(path.join(ROOT_DIR, f"./ocrfiles/{strftime('%H-%M-%S %d-%m-%Y')}.png"));
	with open(filename, "wb") as fh:
		request.files["image"].save(fh);
		print(f"File saved as {filename}.");

	# Inserting document in DB
	# --------------------------------------------------
	insert_document_result: dict = insertDocument(
		user_id = user_data["user_id"],
		document_type = data["document_type"],
		file_path = filename,
	);
	if (not insert_document_result["success"]):
		return buildRes(msg="Could not add document to DB.", details={
			"dberror": insert_document_result["error"]
		});

	# Passing image data into model
	# --------------------------------------------------

	result = await external_ocr(filename);

	# Inserting audit log in DB
	# --------------------------------------------------
	audit_logs_result: dict = insertAuditLog(
		user_data["user_id"],
		insert_document_result["document_id"],
		"Tampered" if result["tamper_detection"]["is_tampered"] else "Verified",
		result["tamper_detection"]["anomaly_score"],
		data["document_type"]
	);
	if (not audit_logs_result["success"]):
		return buildRes(False, "Could not insert audit log.", {
			"error": audit_logs_result.get("error"),
			"message": audit_logs_result.get("message")
		});

	print(audit_logs_result["log_id"]);

	# Returning final result
	# --------------------------------------------------

	return buildRes(True, "Model run.", result["tamper_detection"]);

@app.route("/login", methods=["POST"])
def login():
	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if not checkDictShape(data, {"email", "password"}):
		return buildRes(msg="Request JSON body must have keys email and password");

	# Getting user data
	# --------------------------------------------------
	search_result: dict = searchUser(data["email"]);
	if not search_result["success"]:
		return buildRes(msg="User could not be found due to DB Error.", details={
			"email": data["email"],
			"password": data["password"],
			"dberror": search_result["error"]
		});

	user_data: dict | None = search_result["row"];
	if user_data is None:
		return buildRes(msg="User not found.", details={
			"email": data["email"],
			"password": data["password"],
		});

	# Matching password and returning final result
	# --------------------------------------------------
	if user_data["password_hash"] == data["password"]:
		# password correct
		ret = buildRes(success=True, msg="Password verified.", details={
			"email": data["email"],
			"password": data["password"],
			"token": createToken({
				"email": data["email"],
				"password": data["password"],
			}),
			"role": user_data["role"],
			"phone": user_data["Phone"],
			"name": user_data["name"]
		});
	else:
		# password incorrect
		ret = buildRes(msg="Password incorrect.", details={
			"email": data["email"],
			"password": data["password"],
		});
	return ret;

@app.route("/register", methods=["POST"])
def register():

	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if not checkDictShape(data, {"newUserData", "adminRegistration"}):
		return buildRes(
			msg="Request JSON data must have keys newUserData, adminRegistration"
		);

	oldUserData = {};

	if (data["adminRegistration"]):
		# Creating admin user from register page
		pass;

	else:
		# Creating officer from dashboard

		print(1);

		# Getting token data
		# --------------------------------------------------
		token_data_result: dict = getTokenData(request);
		if not token_data_result["success"]:
			return buildRes(msg="Could not get token data.", details={
				"error": token_data_result["error"],
				**data
			});

		print(2);

#		token_data: dict = token_data_result["token_data"];
#		oldUserData = token_data_result["token_data"];
		oldUserData = {
			"email": token_data_result["token_data"]["email"],
			"password": token_data_result["token_data"]["password"],
		};

	# Creating user
	# --------------------------------------------------

	create_user_result: dict = createUser(
		oldUserData=oldUserData,
		newUserData=data["newUserData"],
		admin_registration=data["adminRegistration"]
	);
	return create_user_result;

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

@app.route("/audit_logs", methods=["POST"])
def getAuditHistory():
	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if not checkDictShape(data, {"limit", "offset"}):
		return {
			"success": False,
			"error": "JSON data requeires keys limit and offset."
		};

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

	print(audit_logs_fetch_result);

	# Returning final result
	# --------------------------------------------------
	return buildRes(True, "Fetched audit logs by user.", {
		"rows": audit_logs_fetch_result["rows"],
	});

@app.route("/dashboard", methods=["POST"])
def getDashboardData():
	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if not checkDictShape(data, {"prev_day_count"}):
		return buildRes(msg="Request JSON requires key prev_day_count.");

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

	# Getting dashboard metrics
	# --------------------------------------------------

	dashboard_data_result: dict = getDashboardMetrics(
		user_data["user_id"],
		user_data["organization_id"],
		user_data["role"].lower() == "admin",
		data["prev_day_count"]
	);
	if not dashboard_data_result["success"]:
		return buildRes(False, "Could not fetch dashboard result.", {
			"message": dashboard_data_result.get("message"),
			"error": dashboard_data_result.get("error")
		});

	return buildRes(True, "Fetched dashboard data.", {
		"audit_logs_by_decision": dashboard_data_result["audit_logs_by_decision"],
		"audit_logs_by_date": dashboard_data_result["audit_logs_by_date"]
	});

# MAIN
# ------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000);

