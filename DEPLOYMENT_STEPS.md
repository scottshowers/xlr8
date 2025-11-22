# XLR8 V2.0 DEPLOYMENT GUIDE
## Copy-Paste Steps for GitHub Web Interface

---

## STEP 1: CREATE PROCFILE

1. Go to your GitHub repo
2. Click "Add file" → "Create new file"
3. Name: `Procfile` (no extension)
4. Paste this:

```
web: cd backend && pip install -r requirements.txt --break-system-packages && cd /app/frontend && npm install && npm run build && cd /app && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

5. Click "Commit new file"

---

## STEP 2: CREATE BACKEND/REQUIREMENTS.TXT

1. Click "Add file" → "Create new file"
2. Name: `backend/requirements.txt`
3. Paste this:

```
fastapi==0.108.0
uvicorn[standard]==0.25.0
websockets==12.0
python-multipart==0.0.6
pydantic==2.5.3
anthropic==0.8.1
```

4. Click "Commit new file"

---

## STEP 3: CREATE BACKEND/MAIN.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/main.py`
3. Copy from: `/mnt/user-data/outputs/backend/main.py`
4. Click "Commit new file"

---

## STEP 4: CREATE BACKEND/WEBSOCKET_MANAGER.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/websocket_manager.py`
3. Copy from: `/mnt/user-data/outputs/backend/websocket_manager.py`
4. Click "Commit new file"

---

## STEP 5: CREATE BACKEND/ROUTERS/__INIT__.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/routers/__init__.py`
3. Copy from: `/mnt/user-data/outputs/backend/routers/__init__.py`
4. Click "Commit new file"

---

## STEP 6: CREATE BACKEND/ROUTERS/CHAT.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/routers/chat.py`
3. Copy from: `/mnt/user-data/outputs/backend/routers/chat.py`
4. Click "Commit new file"

---

## STEP 7: CREATE BACKEND/ROUTERS/UPLOAD.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/routers/upload.py`
3. Copy from: `/mnt/user-data/outputs/backend/routers/upload.py`
4. Click "Commit new file"

---

## STEP 8: CREATE BACKEND/ROUTERS/STATUS.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/routers/status.py`
3. Copy from: `/mnt/user-data/outputs/backend/routers/status.py`
4. Click "Commit new file"

---

## STEP 9: CREATE BACKEND/ROUTERS/PROJECTS.PY

1. Click "Add file" → "Create new file"
2. Name: `backend/routers/projects.py`
3. Copy from: `/mnt/user-data/outputs/backend/routers/projects.py`
4. Click "Commit new file"

---

## STEP 10: CREATE FRONTEND/PACKAGE.JSON

1. Click "Add file" → "Create new file"
2. Name: `frontend/package.json`
3. Copy from: `/mnt/user-data/outputs/frontend/package.json`
4. Click "Commit new file"

---

## STEP 11: CREATE FRONTEND/VITE.CONFIG.JS

1. Click "Add file" → "Create new file"
2. Name: `frontend/vite.config.js`
3. Copy from: `/mnt/user-data/outputs/frontend/vite.config.js`
4. Click "Commit new file"

---

## STEP 12: CREATE FRONTEND/TAILWIND.CONFIG.JS

1. Click "Add file" → "Create new file"
2. Name: `frontend/tailwind.config.js`
3. Copy from: `/mnt/user-data/outputs/frontend/tailwind.config.js`
4. Click "Commit new file"

---

## STEP 13: CREATE FRONTEND/POSTCSS.CONFIG.JS

1. Click "Add file" → "Create new file"
2. Name: `frontend/postcss.config.js`
3. Copy from: `/mnt/user-data/outputs/frontend/postcss.config.js`
4. Click "Commit new file"

---

## STEP 14: CREATE FRONTEND/INDEX.HTML

1. Click "Add file" → "Create new file"
2. Name: `frontend/index.html`
3. Copy from: `/mnt/user-data/outputs/frontend/index.html`
4. Click "Commit new file"

---

## STEP 15: CREATE FRONTEND/SRC/MAIN.JSX

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/main.jsx`
3. Copy from: `/mnt/user-data/outputs/frontend/src/main.jsx`
4. Click "Commit new file"

---

## STEP 16: CREATE FRONTEND/SRC/INDEX.CSS

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/index.css`
3. Copy from: `/mnt/user-data/outputs/frontend/src/index.css`
4. Click "Commit new file"

---

## STEP 17: CREATE FRONTEND/SRC/APP.JSX

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/App.jsx`
3. Copy from: `/mnt/user-data/outputs/frontend/src/App.jsx`
4. Click "Commit new file"

---

## STEP 18: CREATE FRONTEND/SRC/SERVICES/API.JS

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/services/api.js`
3. Copy from: `/mnt/user-data/outputs/frontend/src/services/api.js`
4. Click "Commit new file"

---

## STEP 19: CREATE FRONTEND/SRC/COMPONENTS/CHAT.JSX

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/components/Chat.jsx`
3. Copy from: `/mnt/user-data/outputs/frontend/src/components/Chat.jsx`
4. Click "Commit new file"

---

## STEP 20: CREATE FRONTEND/SRC/COMPONENTS/UPLOAD.JSX

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/components/Upload.jsx`
3. Copy from: `/mnt/user-data/outputs/frontend/src/components/Upload.jsx`
4. Click "Commit new file"

---

## STEP 21: CREATE FRONTEND/SRC/COMPONENTS/STATUS.JSX

1. Click "Add file" → "Create new file"
2. Name: `frontend/src/components/Status.jsx`
3. Copy from: `/mnt/user-data/outputs/frontend/src/components/Status.jsx`
4. Click "Commit new file"

---

## STEP 22: WAIT FOR RAILWAY DEPLOY

1. Go to Railway dashboard
2. Watch deploy logs
3. Wait 5-10 minutes for npm install + build
4. Check for "Build successful" message

---

## STEP 23: TEST DEPLOYMENT

1. Open: `https://yourapp.railway.app/api/health`
2. Should see: `{"status":"healthy",...}`
3. Open: `https://yourapp.railway.app/`
4. Should see React UI with nav bar

---

## STEP 24: TEST UPLOAD (CRITICAL)

1. Go to Upload page
2. Select project
3. Upload Excel file
4. Go to Status page
5. Watch real-time progress (WebSocket should show "connected")
6. Wait for completion WITHOUT ChromaDB corruption

---

## TROUBLESHOOTING

**If frontend doesn't load:**
- Check Railway logs for npm errors
- Verify package.json is valid JSON
- Check Procfile is correct

**If WebSocket doesn't connect:**
- Status page will show "disconnected"
- Jobs will still update via 10s polling
- Check browser console for errors

**If upload fails:**
- Check backend logs in Railway
- Verify environment variables are set
- Check file size (< 100MB)

---

## SUCCESS CRITERIA

✅ Health endpoint returns healthy
✅ Frontend loads with navigation
✅ Upload completes without errors
✅ WebSocket shows "connected"
✅ Job monitor updates in real-time
✅ Chat returns relevant results

**THEN MOVE TO MONEY FEATURES!**
