# IMPORTS
# -----------------------------------------------
from flask import Flask, request;
from numpy import frombuffer, uint8;
from PIL import Image;
from cv2 import imdecode, IMREAD_COLOR, imread;

from os import path, mkdir, scandir, remove;
from time import strftime;
from copy import deepcopy;

from .ai.__init__ import *
from .db.queries import testQuery, searchUser, checkPass
from .jwt.token import createToken, verifyToken

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
		# if user is found compare passed details
		# else

		ret = buildRes(msg="User not found", details={
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
		# if the user does not exist, query DB to create user
		# if the user is created

		ret = buildRes(True, "User has been created.", {
			"email": data["email"],
			"password": data["password"],
			"role": data["role"]
		});

		# if the user is not created
		ret = buildRes(msg="User could not be created because <reason>", details={
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
