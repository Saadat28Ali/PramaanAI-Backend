from flask import Flask, request;
from numpy import frombuffer, uint8;
from PIL import Image;
from cv2 import imdecode, IMREAD_COLOR, imread;

from os import path, mkdir, scandir, remove
from time import strftime

from .ai.__init__ import *
from .db.queries import testQuery, searchUser, checkPass
from .jwt.token import createToken, verifyToken

app = Flask(__name__);

try:
	mkdir(path.abspath("./ocrfiles"));
except FileExistsError:
	pass;

@app.route('/', methods=["GET", "POST"])
def hello_world():

	if request.method == "POST":
		# db test
		if "dbtest" in request.form:
			result = testQuery();
			print(result);
			return(str(result));
	return "This server is working";

@app.route("/ocr", methods=["GET", "POST"])
def ocr_upload():
	if request.method == "POST":

		if "function" not in request.form:
			return "No function provided in form data.";

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
				return "No image uploaded."

			filename: str = f"./ocrfiles/{strftime('%H-%M-%S %d-%m-%Y')}.png";
			with open(path.abspath(filename), "wb") as fh:
				request.files["image"].save(fh);
				print(f"File saved as {filename}.");

			# returning response

			pipeline = DocuNetPipeline();
			img = imread(filename, IMREAD_COLOR);

			if img is None:
				return "Invalid image.";

			with open(path.abspath(filename), "rb") as fh:
				result = pipeline.process(img);
				result_dict: dict = result.to_dict();

			return {**result_dict["tamper_detection"]};

#			if Validator.validateOCR():
#				return "OCR valid.";
#			else:
#				return "OCR invalid."
			return "OCR valid.";

		elif request.form["function"] == "delete all":

			# deleting all files in ./ocrfiles subdir

			for d in scandir(path.abspath("./ocrfiles/")):
				print(d);
				if path.isfile(d):
					remove(d);

			return "Deleted all files from server.";

		else:
			return "Invalid function."

	else:
		return "Retry with POST method.";

@app.route("/login", methods=["POST"])
def login():
	try:
		if "email" in request.form and "password" in request.form:
			# search for username in DB
			if searchUser(request.form["email"]):
				if checkPass(request.form["password"]):
					# user exists and password is correct
					# create and return JWT

					return {
						"email": True,
						"pwd": True,
						"token": createToken({
							"email": request.form["email"],
							"pwd": request.form["password"]
						})
					};
				else:
					# user exists but password is incorrect
					return {
						"email": True,
						"pwd": False,
						"token": None
					};
			else:
				# user does not exists
				return {
						"email": False,
						"pwd": False,
						"token": None
				};
		else: return "Form-data must have username and password fields.";
	except Exception as e:
		print(e);
		print(request);
	return "";

@app.route("/register", method=["POST"])
def registerUser():
	if "email" in request.form and "password" in request.form and "user_type" in request.form:
		# query DB to see if the user exists
		# if the user does not exist, query DB to create user
		# if the user is created
		return {
			created: True,
			email: request.form["email"],
			password: request.form["password"],
			user_type: request.form["user_type"],
			msg: "User has been created."
		};
		# if the user is not created
		return {
			created: False,
			email: request.form["email"],
			password: request.form["password"],
			user_type: request.form["user_type"],
			msg: "User could not be created because <reason>."
		};
	else:
		return "Request form-data must have email, password and user_type fields.";

@app.route("/verifyToken", methods=["POST"])
def _verifyToken():
	if "token" in request.form:
		return str(verifyToken(request.form["token"]));
	else:
		return "Form-data must have token field.";
	return "";

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
