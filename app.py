from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI(title="Subaharan Detector 3000")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# Temporary fake user until we add database login
VALID_USERNAME = "admin"
VALID_PASSWORD = "admin"


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": None
        }
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": "Invalid username or password"
        }
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "server_status": "ONLINE",
            "pi_ip": "Not connected yet",
            "camera_status": "Not added yet"
        }
    )


@app.get("/status")
def status():
    return {
        "server": "online",
        "project": "Subaharan Detector 3000",
        "camera": "not_added_yet"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)