### 쿼리 모음

```sql

SHOW Tables;


SELECT * FROM stock_prices LIMIT 10;
SELECT * FROM stock_indicators LIMIT 10;
SELECT * FROM stock_prices_weekly LIMIT 10;
SELECT * FROM stock_indicators_weekly LIMIT 10;

SELECT COUNT(*) FROM stock_prices;
-- 6496384

SELECT COUNT(*) FROM stock_indicators;
-- 12981228

SELECT COUNT(*) FROM stock_prices_weekly;
-- 1382132

SELECT COUNT(*) FROM stock_indicators_weekly;
-- 5917590

SELECT DISTINCT(market) FROM stock_prices;
SELECT DISTINCT(market) FROM stock_indicators;
SELECT DISTINCT(market) FROM stock_prices_weekly;
SELECT DISTINCT(market) FROM stock_indicators_weekly;
SELECT DISTINCT(market) FROM symbol_master;

```