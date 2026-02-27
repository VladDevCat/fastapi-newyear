from datetime import date
from fastapi import FastAPI

app = FastAPI(title="New Year Info API")


@app.get("/info")
def get_info():
    today = date.today()
    next_new_year = date(today.year + 1, 1, 1)
    days_before_new_year = (next_new_year - today).days
    return {"days_before_new_year": days_before_new_year}