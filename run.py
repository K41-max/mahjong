from app import sio_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run:sio_app", host="0.0.0.0", port=8000, reload=True)
