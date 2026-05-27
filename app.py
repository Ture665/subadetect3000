from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
from database import (
    create_db_and_tables,
    seed_default_admin,
    authenticate_user,
    create_user,
    get_all_users,
    delete_user
)


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

def require_admin(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    if request.session.get("role") != "admin":
        return RedirectResponse(url="/dashboard", status_code=303)

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
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user")
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
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user"),
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
        {
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user")
        }
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "about.html",
        {
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user")
        }
    )

@app.get("/account", response_class=HTMLResponse)
def account(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request,
        "account.html",
        {
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user")
        }
    )

@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    redirect = require_admin(request)
    if redirect:
        return redirect

    users = get_all_users()

    return templates.TemplateResponse(
        request,
        "users.html",
        {
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user"),
            "users": users,
            "error": None
        }
    )

@app.post("/users/create", response_class=HTMLResponse)
def create_user_route(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("user")
):
    redirect = require_admin(request)
    if redirect:
        return redirect

    if not username.strip() or not password.strip():
        users = get_all_users()

        return templates.TemplateResponse(
            request,
            "users.html",
            {
                "username": request.session.get("username", "admin"),
                "role": request.session.get("role", "user"),
                "users": users,
                "error": "Username and password are required"
            }
        )

    create_user(username.strip(), password, role)

    return RedirectResponse(url="/users", status_code=303)


@app.post("/users/delete/{user_id}")
def delete_user_route(request: Request, user_id: int):
    redirect = require_admin(request)
    if redirect:
        return redirect

    delete_user(user_id)

    return RedirectResponse(url="/users", status_code=303)

@app.get("/status")
def status():
    return {
        "server": "online",
        "project": "Subaharan Detector 3000",
        "camera": "not_added_yet"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)