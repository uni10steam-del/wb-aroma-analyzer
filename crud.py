from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from models import NicheAnalysis, Competitor, CompetitorSaleEstimate

async def create_niche_analysis(db: AsyncSession, data: dict) -> NicheAnalysis:
    ms = data.get("market_summary", {}) or {}
    nf = ms.get("new_product_forecast")
    niche = NicheAnalysis(
        query=data.get("query", ""),
        analyzed_at=data.get("analyzed_at"),
        competitors_analyzed=ms.get("competitors_analyzed", 0),
        avg_price=ms.get("avg_price"),
        min_price=ms.get("min_price"),
        max_price=ms.get("max_price"),
        median_orders_30d_low=ms.get("median_orders_30d_low"),
        median_orders_30d_high=ms.get("median_orders_30d_high"),
        total_market_revenue_30d_low=ms.get("total_market_revenue_30d_low"),
        total_market_revenue_30d_high=ms.get("total_market_revenue_30d_high"),
        new_product_forecast=nf,
        raw_summary=ms,
    )
    db.add(niche)
    await db.flush()
    await db.refresh(niche)
    for c in data.get("competitors", []):
        comp = Competitor(
            niche_id=niche.id,
            article_id=c.get("article_id"),
            name=c.get("name"),
            brand=c.get("brand"),
            price=c.get("price"),
            rating=c.get("rating"),
            total_feedbacks_wb=c.get("total_feedbacks_wb"),
            scraped_feedbacks=c.get("scraped_feedbacks"),
        )
        db.add(comp)
        await db.flush()
        await db.refresh(comp)
        se = c.get("sales_estimate")
        if se:
            est = CompetitorSaleEstimate(
                competitor_id=comp.id,
                total_reviews=se.get("total_reviews"),
                reviews_last_30d=se.get("reviews_last_30d"),
                reviews_last_7d=se.get("reviews_last_7d"),
                first_review=se.get("first_review"),
                last_review=se.get("last_review"),
                estimated_orders_30d_low=se.get("estimated_orders_30d_low"),
                estimated_orders_30d_high=se.get("estimated_orders_30d_high"),
                estimated_orders_7d_low=se.get("estimated_orders_7d_low"),
                estimated_orders_7d_high=se.get("estimated_orders_7d_high"),
                estimated_revenue_30d_low=se.get("estimated_revenue_30d_low"),
                estimated_revenue_30d_high=se.get("estimated_revenue_30d_high"),
                estimated_revenue_7d_low=se.get("estimated_revenue_7d_low"),
                estimated_revenue_7d_high=se.get("estimated_revenue_7d_high"),
            )
            db.add(est)
    await db.commit()
    return niche

async def get_niche_analyses(db: AsyncSession, skip: int = 0, limit: int = 50) -> List[NicheAnalysis]:
    result = await db.execute(select(NicheAnalysis).order_by(desc(NicheAnalysis.analyzed_at)).offset(skip).limit(limit))
    return result.scalars().all()

async def get_niche_analysis(db: AsyncSession, niche_id: int) -> Optional[NicheAnalysis]:
    result = await db.execute(select(NicheAnalysis).where(NicheAnalysis.id == niche_id))
    return result.scalar_one_or_none()
