from flask import Flask, request;
from os import path, mkdir, scandir, remove
from time import strftime

from ocr.validation import Validator

app = Flask(__name__);

try:
	mkdir(path.abspath("./ocrfiles"));
except FileExistsError:
	pass;

@app.route('/', methods=["GET"])
def hello_world():
	return "Hello world";

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

			with open(path.abspath(f"./ocrfiles/{strftime('%H-%M-%S %d-%m-%Y')}.png"), "wb") as fh:
				request.files["image"].save(fh);

			# returning response

			if Validator.validateOCR():
				return "OCR valid.";
			else:
				return "OCR invalid."

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

@app.route("/login", methods=["GET", "POST"])
def login():
	if request.form[""]

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
