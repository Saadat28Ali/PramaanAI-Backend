from flask import Flask, request;

app = Flask(__name__);

@app.route('/', methods=["GET"])
def hello_world():
	return "Hello world";

@app.route("/ocr", methods=["GET", "POST"])
def ocr_upload():
	if request.method == "POST":
		request.files["image"].save("./ocr_uploads/new.png");
		return "File uploaded.";
	else:
		return "Retry with POST method.";
