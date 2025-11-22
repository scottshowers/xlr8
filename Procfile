web: cd backend && pip install -r requirements.txt --break-system-packages && cd /app/frontend && npm install && npm run build && cd /app && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
