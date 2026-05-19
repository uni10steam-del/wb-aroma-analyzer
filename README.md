# WB Niche Analyzer

Анализатор ниши **Wildberries** для оценки продаж конкурентов и прогнозирования выручки нового товара.

**Оптимизировано под нишу:** автомобильные ароматизаторы  
**Работает с любой нишей:** передайте нужный `query` в параметре.

---

## 🚀 Быстрый старт (локально)

```bash
git clone https://github.com/ВАШ_РЕПОЗИТОРИЙ.git
cd wb-aroma-analyzer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Откройте http://localhost:8000/docs — интерактивная документация Swagger.

---

## 🛤 Деплой на Railway из GitHub

### Шаг 1. Создайте репозиторий на GitHub

1. Создайте новый репозиторий (можно приватный).
2. Загрузите в него файлы этого проекта:
   - `main.py`
   - `wb_parser.py`
   - `requirements.txt`
   - `Procfile`
   - `railway.json`
   - `.gitignore`
3. Закоммитьте и запушьте:

```bash
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/ВАШ_РЕПОЗИТОРИЙ.git
git push -u origin main
```

### Шаг 2. Создайте проект на Railway

1. Зайдите на [railway.app](https://railway.app) и авторизуйтесь.
2. Нажмите **"New Project"** → **"Deploy from GitHub repo"**.
3. Выберите ваш репозиторий `wb-aroma-analyzer`.
4. Railway автоматически определит Python-проект по `requirements.txt` и `railway.json`.
5. Нажмите **Deploy**.

### Шаг 3. Проверьте работу

После деплоя Railway выдаст вам URL вида:
```
https://wb-aroma-analyzer-production.up.railway.app
```

Проверьте:
```bash
curl https://ВАШ-URL.railway.app/health
```

Должен вернуть `{"status":"ok"}`.

---

## 📡 API Endpoints

### `GET /analyze`

**Параметры:**
- `query` — поисковый запрос (обязательный)
- `top_n` — сколько карточек анализировать (1–30, default: 10)
- `max_feedbacks` — макс. отзывов на карточку (20–200, default: 80)
- `search_pages` — страниц поиска WB (1–5, default: 2)

**Пример запроса:**
```bash
curl "https://ВАШ-URL.railway.app/analyze?query=автомобильные+ароматизаторы&top_n=10"
```

**Пример ответа:**
```json
{
  "query": "автомобильные ароматизаторы",
  "analyzed_at": "2026-05-19T12:00:00",
  "market_summary": {
    "competitors_analyzed": 10,
    "avg_price": 450.0,
    "min_price": 199.0,
    "max_price": 1290.0,
    "median_orders_30d_low": 165,
    "median_orders_30d_high": 300,
    "total_market_revenue_30d_low": 850000.0,
    "total_market_revenue_30d_high": 1500000.0,
    "new_product_forecast": {
      "pessimistic_1pct_orders_30d": 2,
      "realistic_3pct_orders_30d": 5,
      "optimistic_10pct_orders_30d": 30,
      "pessimistic_revenue_30d": 900.0,
      "realistic_revenue_30d": 2250.0,
      "optimistic_revenue_30d": 13500.0
    }
  },
  "competitors": [
    {
      "article_id": 123456789,
      "name": "Ароматизатор автомобильный ...",
      "brand": "BrandName",
      "price": 399.0,
      "rating": 4.7,
      "total_feedbacks_wb": 1240,
      "scraped_feedbacks": 80,
      "sales_estimate": {
        "total_reviews": 1240,
        "reviews_last_30d": 45,
        "reviews_last_7d": 12,
        "estimated_orders_30d_low": 248,
        "estimated_orders_30d_high": 450,
        "estimated_revenue_30d_low": 98952.0,
        "estimated_revenue_30d_high": 179550.0
      }
    }
  ]
}
```

### `POST /analyze`

Для интеграций, где удобнее POST:
```bash
curl -X POST https://ВАШ-URL.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"автомобильные ароматизаторы","top_n":10}'
```

---

## 🧮 Как считается прогноз

### Оценка продаж конкурента
1. Собираем отзывы за последние 30 дней.
2. Для автомобильных ароматизаторов используем коэффициент:  
   **1 отзыв ≈ 5.5–10 заказов** (мало кто оставляет отзыв на дешёвый товар).
3. `orders = reviews × multiplier`.
4. `revenue = orders × price`.

### Прогноз для нового товара
- **Пессимистичный:** 1% от медианы конкурента (новая карточка без рейтинга).
- **Реалистичный:** 3% от медианы (с базовой рекламой и нормальным фото).
- **Оптимистичный:** 10% от медианы (сильное УТП, агрессивная реклама).

---

## ⚠️ Ограничения и риски

1. **WB блокирует массовые запросы.** Скрипт использует:
   - семафор (макс. 3 параллельных запроса)
   - случайные задержки 0.6–1.2 сек между запросами
   - retry с бэкоффом

   Если Railway IP попадёт в бан — запросы вернут 403. В этом случае:
   - перезапустите сервис (Railway выдаст новый IP)
   - или используйте прокси (требует доработки)

2. **Точность прогноза.** Это **прокси-оценка**, не точные данные WB.  
   Реальные продажи могут отличаться в 2–3 раза.

3. **Время выполнения.** Анализ 10 карточек занимает 15–40 секунд из-за задержек.

---

## 🔧 Другие ниши

Просто меняйте параметр `query`:
- `?query=парфюм+автомобильный`
- `?query=освежитель+воздуха+машина`
- `?query=ароматизатор+под+сиденье`

---

## 📁 Структура проекта

```
wb-aroma-analyzer/
├── main.py              # FastAPI приложение
├── wb_parser.py         # Логика парсинга WB
├── requirements.txt     # Зависимости
├── Procfile             # Команда запуска для Railway/Heroku
├── railway.json         # Конфиг Railway (Nixpacks)
├── .gitignore
└── README.md
```

---

## 📄 Лицензия

MIT. Используйте на свой страх и риск.  
Соблюдайте правила Wildberries при частом парсинге.
