import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, SessionLocal
from wb_parser import analyze_niche
from crud import create_niche_analysis, get_niche_analyses, get_niche_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WB Niche Analyzer",
    description="Анализ ниши Wildberries: парсинг, хранение в PostgreSQL, дашборд",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

@app.on_event("startup")
async def on_startup():
    logger.info("Starting up... Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/analyze")
async def analyze(
    query: str = Query(..., description="Поисковый запрос на WB"),
    top_n: int = Query(10, ge=1, le=30),
    max_feedbacks: int = Query(80, ge=20, le=200),
    search_pages: int = Query(2, ge=1, le=5),
    save: bool = Query(True, description="Сохранить результат в PostgreSQL"),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await analyze_niche(
            query=query,
            top_n=top_n,
            max_feedbacks=max_feedbacks,
            search_pages=search_pages,
        )
        if save and not result.get("error"):
            try:
                await create_niche_analysis(db, result)
                logger.info(f"Saved analysis for query: {query}")
            except Exception as e:
                logger.error(f"Failed to save analysis: {e}")
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_post(body: dict, db: AsyncSession = Depends(get_db)):
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
        if body.get("save", True) and not result.get("error"):
            try:
                await create_niche_analysis(db, result)
            except Exception as e:
                logger.error(f"Failed to save analysis: {e}")
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/niches")
async def api_niches(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    try:
        items = await get_niche_analyses(db, skip=skip, limit=limit)
        data = []
        for n in items:
            data.append({
                "id": n.id,
                "query": n.query,
                "analyzed_at": n.analyzed_at.isoformat() if n.analyzed_at else None,
                "competitors_analyzed": n.competitors_analyzed,
                "avg_price": n.avg_price,
                "median_orders_30d_low": n.median_orders_30d_low,
                "median_orders_30d_high": n.median_orders_30d_high,
                "forecast": n.new_product_forecast,
            })
        return {"items": data, "count": len(data)}
    except Exception as e:
        logger.error(f"Failed to fetch niches: {e}")
        return {"items": [], "count": 0, "error": str(e)}

@app.get("/api/niche/{niche_id}")
async def api_niche_detail(niche_id: int, db: AsyncSession = Depends(get_db)):
    try:
        niche = await get_niche_analysis(db, niche_id)
        if not niche:
            raise HTTPException(status_code=404, detail="Niche not found")
        competitors = []
        for c in niche.competitors:
            se = c.sales_estimate
            competitors.append({
                "article_id": c.article_id,
                "name": c.name,
                "brand": c.brand,
                "price": c.price,
                "rating": c.rating,
                "total_feedbacks_wb": c.total_feedbacks_wb,
                "sales_estimate": {
                    "reviews_last_30d": se.reviews_last_30d if se else None,
                    "estimated_orders_30d_low": se.estimated_orders_30d_low if se else None,
                    "estimated_orders_30d_high": se.estimated_orders_30d_high if se else None,
                    "estimated_revenue_30d_low": se.estimated_revenue_30d_low if se else None,
                    "estimated_revenue_30d_high": se.estimated_revenue_30d_high if se else None,
                } if se else None,
            })
        return {
            "id": niche.id,
            "query": niche.query,
            "analyzed_at": niche.analyzed_at.isoformat() if niche.analyzed_at else None,
            "market_summary": {
                "competitors_analyzed": niche.competitors_analyzed,
                "avg_price": niche.avg_price,
                "min_price": niche.min_price,
                "max_price": niche.max_price,
                "median_orders_30d_low": niche.median_orders_30d_low,
                "median_orders_30d_high": niche.median_orders_30d_high,
                "total_market_revenue_30d_low": niche.total_market_revenue_30d_low,
                "total_market_revenue_30d_high": niche.total_market_revenue_30d_high,
                "new_product_forecast": niche.new_product_forecast,
            },
            "competitors": competitors,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch niche {niche_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
