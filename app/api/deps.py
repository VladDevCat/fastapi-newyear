from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.item_service import ItemService


def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    return ItemService(db)