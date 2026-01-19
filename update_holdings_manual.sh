#!/bin/bash
# Manual script to update portfolio holdings dates
# This requires database access

echo "To update portfolio holdings' created_at to 2026-01-01, please:"
echo ""
echo "Option 1: Execute SQL directly in your database:"
echo "  UPDATE portfolio_holdings SET created_at = '2026-01-01 00:00:00'::timestamp WHERE created_at != '2026-01-01 00:00:00'::timestamp;"
echo ""
echo "Option 2: Use the SQL file:"
echo "  psql <your_database_url> < backend/update_holding_dates.sql"
echo ""
echo "Option 3: Restart backend and call API:"
echo "  curl -X POST http://127.0.0.1:5002/api/portfolio/update-holding-dates"
