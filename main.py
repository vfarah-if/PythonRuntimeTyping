from fastapi import FastAPI
from pydantic import BaseModel
from typing import AnyStr

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/item/{id}")
async def read_item(id: int):
    return {"id": id}


class Finfo(BaseModel):
    path: AnyStr
    size: int = 0
    inode: int = -1


class HashRecord(BaseModel):
    digest: str
    finfo: Finfo


@app.post("/finfo")
async def post_finfo(finfo: Finfo):
    return HashRecord(digest="<sha hash goes here>", finfo=finfo)
