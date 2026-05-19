"""
WB Niche Analyzer API
Deploy: Railway (GitHub -> Railway)
Niche: автомобильные ароматизаторы / любая ниша WB
"""
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from wb_parser import analyze_niche

app = FastAPI(
    title="WB Niche Analyzer",
    description="Анализ ниши Wildberries: поиск, отзывы, оценка продаж конкурентов",
    version="1.0.0",
)

# CORS — можно дергать с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "WB Niche Analyzer",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/analyze?query=автомобильные+ароматизаторы&top_n=10",
            "health": "/health",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/analyze")
async def analyze(
    query: str = Query(..., description="Поисковый запрос на WB, например: автомобильные ароматизаторы"),
    top_n: int = Query(10, ge=1, le=30, description="Сколько карточек анализировать"),
    max_feedbacks: int = Query(80, ge=20, le=200, description="Макс. отзывов на карточку"),
    search_pages: int = Query(2, ge=1, le=5, description="Сколько страниц поиска просматривать"),
):
    """
    Анализ ниши Wildberries.

    Пример:
        /analyze?query=автомобильные+ароматизаторы&top_n=10

    Возвращает:
        - market_summary: сводка по рынку (цены, оценка выручки, прогноз для нового товара)
        - competitors: детали по каждому конкуренту
    """
    try:
        result = await analyze_niche(
            query=query,
            top_n=top_n,
            max_feedbacks=max_feedbacks,
            search_pages=search_pages,
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_post(body: dict):
    """POST-вариант для удобной интеграции."""
    query = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Field 'query' is required")
    try:
        result = await analyze_niche(
            query=query,
            top_n=body.get("top_n", 10),
            max_feedbacks=body.get("max_feedbacks", 80),
            search_pages=body.get("search_pages", 2),
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
