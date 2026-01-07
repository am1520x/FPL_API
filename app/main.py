# app/main.py
from fastapi import FastAPI
from app.api.router import router

app = FastAPI(title="FPL Entry API", description="An API to fetch and analyse Fantasy Premier League data.", version="1.0.0", contact={
    "name": "FPL Entry API Support",
    "url": "https://github.com/am1520x/FPL_API",
})

app.include_router(router)

@app.get("/")
def root():
    return {"name": "FPL Entry API", "docs": "/docs"}

