from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Doc Assistant API", version="1.0.0")

# CORS lets your React app (running on port 5173) talk to this server (port 8000)
# Without this, the browser blocks all requests — a very common "why isn't it working" moment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Doc Assistant API is running"}
