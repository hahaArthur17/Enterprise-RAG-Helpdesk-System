from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "AI service running"}

@app.post("/ask")
def ask(question: str):
    return {"answer": "This is a mock AI response"}
