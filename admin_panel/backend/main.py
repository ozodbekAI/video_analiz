# backend/main.py
from fastapi import FastAPI, HTTPException
from admin_panel.backend.routers.admin_prompts import router as prompts_router
from admin_panel.backend.routers.admin_stats import router as stats_router
from admin_panel.backend.routers.admin_users import router as users_router
from admin_panel.backend.routers.admin_samples import router as samples_router
from admin_panel.backend.routers.admin_upload import router as upload_router
from admin_panel.backend.core.config import settings
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Admin Panel")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/admin/login")
def admin_login(username: str, password: str):
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        return {"token": settings.ADMIN_TOKEN}
    raise HTTPException(401, "Invalid credentials")

app.include_router(prompts_router)
app.include_router(stats_router)
app.include_router(users_router)
app.include_router(samples_router)
app.include_router(upload_router)
