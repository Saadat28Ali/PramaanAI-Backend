from os import path;
import httpx;

async def external_ocr(filename: str):
	async with httpx.AsyncClient(timeout = 20.0) as client:
		with open(path.abspath(filename), "rb") as f:
			files = {"image": (path.abspath(filename), f, "application/octet-stream")};
			response = await client.post(
				"https://8000-01m1c4fxrw0vbrba3x0mf49meg.cloudspaces.litng.ai/predict",
#				"https://pramaanai-model-1.onrender.com/api/v1/ela-only",
				files=files
			);
			response.raise_for_status();
			return response.json();
