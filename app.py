from flask import Flask, request;
from os import path, mkdir, scandir, remove
from time import strftime

app = Flask(__name__);

@app.route('/', methods=["GET"])
def hello_world():
	return "Hello world";

@app.route("/ocr", methods=["GET", "POST"])
def ocr_upload():
	if request.method == "POST":

		if request.form["function"] == "upload":

			# trying to make the ./ocr directory
			# if it already exists, this part is skipped

			try:
				mkdir(path.abspath("./ocr"));
			except FileExistsError:
				pass;

			# saving the received file in ./ocr
			# the filename is based on time of upload

			with open(path.abspath(f"./ocr/{strftime("%H-%M-%S %d-%m-%Y")}.png"), "wb") as fh:
				request.files["image"].save(fh);

			# returning response

			return "File uploaded.";

		elif request.form["function"] == "delete all":

			# deleting all files in ./ocr subdir

			for d in scandir(path.abspath("./ocr/")):
				print(d);
				if path.isfile(d):
					remove(d);

			return "Deleted all files from server.";

	else:
		return "Retry with POST method.";
