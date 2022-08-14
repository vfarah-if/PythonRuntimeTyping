from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/item/{id}")
async def read_item(id: int):
    return {"id": id}
