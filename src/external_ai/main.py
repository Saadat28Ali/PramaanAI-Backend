from os import path, getcwd;
import httpx;

# GLOBALS
# --------------------------------------------------

ROOT_DIR: str = path.abspath(getcwd());

# --------------------------------------------------

async def external_ocr(filename: str):
	async with httpx.AsyncClient(timeout = 20.0) as client:
		with open(path.abspath(path.join(ROOT_DIR, filename)), "rb") as f:
#			files = {"image": (path.abspath(path.join(ROOT_DIR, filename)), f, "application/octet-stream")};
			response = await client.post(
#				"https://8000-01m1c4fxrw0vbrba3x0mf49meg.cloudspaces.litng.ai/predict",
				"https://pramaanai-model2.onrender.com/api/v1/ela-only",
				files = {
					"file": f
				}
			);
			response.raise_for_status();
			return response.json();
