from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import socket
import subprocess
from database import (
    create_db_and_tables,
    seed_default_admin,
    authenticate_user,
    create_user,
    get_all_users,
    delete_user,
    get_user_by_id,
    count_admin_users
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

def get_pi_status():
    hostname = socket.gethostname()
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except Exception:
        ip_address = "Unknown"
        
    try:
        temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
        temperature = temp_output.replace("temp=", "").strip()
    except Exception:
        temperature = "Unavailable"
        
    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "temperature": temperature,
        "server": "ONLINE"
    }

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

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "error": None,
            "show_nav": False
        }
    )


@app.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    username = username.strip()

    if not username or not password:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "Username and password are required",
                "show_nav": False
            }
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "Passwords do not match",
                "show_nav": False
            }
        )

    new_user = create_user(username, password, role="user")

    if not new_user:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "A user with that username already exists",
                "show_nav": False
            }
        )

    request.session["logged_in"] = True
    request.session["username"] = new_user.username
    request.session["role"] = new_user.role

    return RedirectResponse(url="/dashboard", status_code=303)

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
    
    pi_status = get_pi_status()

    return templates.TemplateResponse(
        request,
        "detection.html",
        {
            "username": request.session.get("username", "Unknown"),
            "role": request.session.get("role", "user"),
            "server_status": pi_status["server"],
            "pi_ip": pi_status["ip_address"],
            "camera_status": "Not added yet",
            "temperature": pi_status["temperature"]
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

from database import (
    create_db_and_tables,
    seed_default_admin,
    authenticate_user,
    create_user,
    get_all_users,
    delete_user,
    get_user_by_id,
    count_admin_users
)


@app.post("/users/delete/{user_id}")
def delete_user_route(request: Request, user_id: int):
    redirect = require_admin(request)
    if redirect:
        return redirect

    user = get_user_by_id(user_id)

    if not user:
        return RedirectResponse(url="/users", status_code=303)

    if user.username == request.session.get("username"):
        users = get_all_users()
        return templates.TemplateResponse(
            request,
            "users.html",
            {
                "username": request.session.get("username", "Unknown"),
                "role": request.session.get("role", "user"),
                "users": users,
                "error": "You cannot delete your own account while logged in"
            }
        )

    if user.role == "admin" and count_admin_users() <= 1:
        users = get_all_users()
        return templates.TemplateResponse(
            request,
            "users.html",
            {
                "username": request.session.get("username", "Unknown"),
                "role": request.session.get("role", "user"),
                "users": users,
                "error": "You cannot delete the last admin account"
            }
        )

    delete_user(user_id)

    return RedirectResponse(url="/users", status_code=303)

@app.get("/status")
def status():
    return get_pi_status()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)