# IMPORTS
# -----------------------------------------------
from flask import Flask, request;
from numpy import frombuffer, uint8;
from PIL import Image;
from cv2 import imdecode, IMREAD_COLOR, imread;

from os import path, mkdir, scandir, remove;
from time import strftime;
from copy import deepcopy;
from .hash.hashf import hashIt;

from .ai.__init__ import *
from .db.queries import testQuery, searchUser, checkPass
from .jwt.token import createToken, verifyToken
from db.queries import insert_document_and_screening
from db.queries import get_all_audit_logs

# ------------------------------------------------

app = Flask(__name__);

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

@app.route("/ocr", methods=["GET", "POST"])
def ocr_upload():

	ret: dict = {};

	if request.method == "POST":

		if "function" not in request.form:
			ret = buildRes(False, "No functions provided in form data");

		if request.form["function"] == "validate":

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

			# saving document file in DB

			# returning response

			pipeline = DocuNetPipeline();
			img = imread(filename, IMREAD_COLOR);

			if img is None:
				ret = buildRes(msg = "Invalid image.");

			with open(path.abspath(filename), "rb") as fh:
				result = pipeline.process(img);
				result_dict: dict = result.to_dict();

			ret = buildRes(True, "Model run.", {**result_dict["tamper_detection"]});

		elif request.form["function"] == "delete all":

			# deleting all files in ./ocrfiles subdir

			for d in scandir(path.abspath("./ocrfiles/")):
				print(d);
				if path.isfile(d):
					remove(d);

			ret = buildRes(True, "Deleted all files from server.");

		else:
			ret = buildRes(msg="Invalid function.");

	else:
		ret = buildRes(msg="Retry with POST method.");

	return ret;

@app.route("/login", methods=["POST"])
def login():

	ret: dict = deepcopy(RES_TEMPLATE);

	data: dict = request.get_json();

	if "email" in data and "password" in data and "role" in data:
		# query DB to find user

		search_result: dict | None = searchUser(data["email"]);
		if search_result == None:
			# user not found
			ret = buildRes(msg="User not found", details={
				"email": data["email"],
				"password": data["password"],
				"role": data["role"]
			});
		else:
			# user found
			if search_result["email"] == data["email"] and search_result["password_hash"] == data["password"]:
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

	else:
		ret = buildRes(msg="Request JSON body must have keys email, password and role.");

	return ret;

@app.route("/register", methods=["POST"])
def register():

	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if "email" in data and "password" in data and "role" in data:
		# query DB to see if the user exists

		search_result: dict | None = searchUser(data["email"]);
		if search_result == None:
			# user does not exist

			# create user in DB
			ret = buildRes(True, "User has been created.", {
				"email": data["email"],
				"password": data["password"],
				"role": data["role"]
			});
		else:
			# user already exists
			ret = buildRes(msg="User already exists", details={
				"email": data["email"],
				"password": data["password"],
				"role": data["role"]
			});
	else:
		ret = buildRes(msg="Request JSON data must have keys email, password and role.");

	return ret;

@app.route("/verifyToken", methods=["POST"])
def _verifyToken():

	ret: dict = deepcopy(RES_TEMPLATE);
	data: dict = request.get_json();

	if "token" in data:
		ret = buildRes(verifyToken(data["token"]), "Token verification complete.");
	else:
		ret = buildRes(msg="Form-data must have token field.");

	return ret;

# MAIN
# ------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)



@app.post("/api/screenings/create")
def create_screening_entry(data: dict):
    result = insert_document_and_screening(
        uploaded_by=data.get("uploaded_by"),
        document_type=data.get("document_type"),
        file_path=data.get("file_path"),
        officer_id=data.get("officer_id"),
        person_id=data.get("person_id"),
        risk_score=data.get("risk_score"),
        decision=data.get("decision", "verified"),
        status="COMPLETED"
    )
    if result:
        return {"status": "success", "data": result}
    return {"status": "error", "message": "Failed to record screening details"}, 500



@app.get("/api/audit-history")
def get_audit_history(limit: int = 50, page: int = 1):
    offset = (page - 1) * limit
    logs = get_all_audit_logs(limit=limit, offset=offset)
    return {"status": "success", "data": logs}


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "officer")

    if not name or not email or not password:
        return jsonify({"status": "error", "message": "Name, email, and password are required"}), 400

    result = register_user(name=name, email=email, raw_password=password, role=role)

    if not result["success"]:
        return jsonify({"status": "error", "message": result["message"]}), 400

    return jsonify({"status": "success", "message": result["message"], "user_id": result["user_id"]}), 201