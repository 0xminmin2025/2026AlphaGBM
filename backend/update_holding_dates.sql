-- Update all portfolio holdings' created_at date to 2026-01-01
-- Run this SQL script directly on your database

UPDATE portfolio_holdings 
SET created_at = '2026-01-01 00:00:00'::timestamp 
WHERE created_at != '2026-01-01 00:00:00'::timestamp;

-- Verify the update
SELECT ticker, style, created_at 
FROM portfolio_holdings 
ORDER BY ticker 
LIMIT 10;
