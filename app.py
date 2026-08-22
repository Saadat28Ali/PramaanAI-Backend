from flask import Flask, request;
from os import path, mkdir
from time import time, gmtime

app = Flask(__name__);

@app.route('/', methods=["GET"])
def hello_world():
	return "Hello world";

@app.route("/ocr", methods=["GET", "POST"])
def ocr_upload():
	if request.method == "POST":

		# trying to make the ./ocr directory
		# if it already exists, this part is skipped

		try:
			mkdir(path.abspath("./ocr"));
		except FileExistsError:
			pass;

		# saving the received file in ./ocr
		# the filename is based on time of upload

		current_time = gmtime(time());
		with open(path.abspath(f"./ocr/{current_time.tm_hour}-{current_time.tm_min}-{current_time.tm_sec} {current_time.tm_mday}-{current_time.tm_mon}-{current_time.tm_year}.png"), "wb") as fh:
			request.files["image"].save(fh);

		# returning response

		return "File uploaded.";
	else:
		return "Retry with POST method.";
