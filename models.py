from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class NicheAnalysis(Base):
    __tablename__ = "niche_analyses"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True, nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    competitors_analyzed = Column(Integer, default=0)
    avg_price = Column(Float, nullable=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    median_orders_30d_low = Column(Integer, nullable=True)
    median_orders_30d_high = Column(Integer, nullable=True)
    total_market_revenue_30d_low = Column(Float, nullable=True)
    total_market_revenue_30d_high = Column(Float, nullable=True)
    new_product_forecast = Column(JSON, nullable=True)
    raw_summary = Column(JSON, nullable=True)
    competitors = relationship("Competitor", back_populates="niche", cascade="all, delete-orphan")

class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(Integer, primary_key=True, index=True)
    niche_id = Column(Integer, ForeignKey("niche_analyses.id"), nullable=False)
    article_id = Column(Integer, index=True, nullable=False)
    name = Column(Text, nullable=True)
    brand = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    total_feedbacks_wb = Column(Integer, nullable=True)
    scraped_feedbacks = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    niche = relationship("NicheAnalysis", back_populates="competitors")
    sales_estimate = relationship("CompetitorSaleEstimate", back_populates="competitor", uselist=False, cascade="all, delete-orphan")

class CompetitorSaleEstimate(Base):
    __tablename__ = "competitor_sale_estimates"
    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id"), unique=True, nullable=False)
    total_reviews = Column(Integer, nullable=True)
    reviews_last_30d = Column(Integer, nullable=True)
    reviews_last_7d = Column(Integer, nullable=True)
    first_review = Column(String, nullable=True)
    last_review = Column(String, nullable=True)
    estimated_orders_30d_low = Column(Integer, nullable=True)
    estimated_orders_30d_high = Column(Integer, nullable=True)
    estimated_orders_7d_low = Column(Integer, nullable=True)
    estimated_orders_7d_high = Column(Integer, nullable=True)
    estimated_revenue_30d_low = Column(Float, nullable=True)
    estimated_revenue_30d_high = Column(Float, nullable=True)
    estimated_revenue_7d_low = Column(Float, nullable=True)
    estimated_revenue_7d_high = Column(Float, nullable=True)
    competitor = relationship("Competitor", back_populates="sales_estimate")
