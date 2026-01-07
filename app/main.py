# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.router import router

app = FastAPI(title="FPL Entry API", description="An API to fetch and analyse Fantasy Premier League data.", version="1.0.0", contact={
    "name": "FPL Entry API Support",
    "url": "https://github.com/am1520x/FPL_API",
})

app.mount("/images", StaticFiles(directory="images"), name="images")
app.include_router(router)

@app.get("/")
def root():
    return {"name": "FPL API, providing Fantasy Premier League data and analysis", "docs": "/docs"}

@app.get("/manager/{manager_id}")
async def get_manager_data(manager_id: int):
    """
    Fetch data for a specific FPL manager.

    ### How to find your manager ID:
    1. Go to your team page on the official FPL website, e.g. your current points
    2. Your ID is the number in the url: `entry/XXXXXXX/event/`

    ![FPL Guide](/images/manager_id_guide.png)
    """
    return {"manager_id": manager_id, "data": "Manager data would be fetched and returned here."}

@app.get("/league/{league_id}")
async def get_league_data(league_id: int):
    """
    Fetch data for a specific FPL league.

    ### How to find your league ID:
    1. Go to the league table page on the official FPL website.
    2. The ID is the number in the url: `league/XXXXXXX/standings/`

    ![FPL Guide](/images/league_id_guide.png)
    """
    return {"league_id": league_id, "data": "League data would be fetched and returned here."}
