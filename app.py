from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from database import create_db_and_tables, seed_default_admin, authenticate_user


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Subaharan Detector 3000")

app.add_middleware(
    SessionMiddleware,
    secret_key="change-this-secret-key"
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")
create_db_and_tables()
seed_default_admin()

def require_login(request: Request):
    if not request.session.get("logged_in"):
        return RedirectResponse(url="/login", status_code=303)

    return None


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": None,
            "show_nav": False
        }
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = authenticate_user(username, password)

    if user:
        request.session["logged_in"] = True
        request.session["username"] = user.username
        request.session["role"] = user.role
        return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": "Invalid username or password",
            "show_nav": False
        }
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "username": request.session.get("username", "admin")
        }
    )


@app.get("/detection", response_class=HTMLResponse)
def detection(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "detection.html",
        {
            "server_status": "ONLINE",
            "pi_ip": "Not connected yet",
            "camera_status": "Not added yet"
        }
    )


@app.get("/downloads", response_class=HTMLResponse)
def downloads(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "downloads.html",
        {}
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "about.html",
        {}
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