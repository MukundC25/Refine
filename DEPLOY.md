# Deploy Refine to Render - Step by Step Guide

## Overview
This guide will help you deploy the Refine Resume Optimizer (Backend + Frontend + Database) to Render.com

## Prerequisites
1. GitHub account with the Refine repository pushed
2. Render.com account (free tier works)
3. Gemini API key (already configured in your .env)

---

## STEP 1: Push Latest Changes to GitHub

```bash
cd /Users/mukundchavan/Downloads/Refine
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

---

## STEP 2: Deploy Using Render Blueprint (Automatic)

### Option A: Blueprint Deploy (Recommended - Deploys everything at once)

1. Go to https://dashboard.render.com/blueprints
2. Click **"New Blueprint Instance"**
3. Connect your GitHub repository (MukundC25/Refine)
4. Render will automatically detect `render.yaml` and create:
   - PostgreSQL Database (refine-db)
   - Backend Web Service (refine-backend)
   - Frontend Static Site (refine-frontend)

5. **IMPORTANT:** After blueprint deploys, set your GEMINI_API_KEY:
   - Go to https://dashboard.render.com/
   - Click on **refine-backend** service
   - Go to **Environment** tab
   - Add environment variable:
     - Key: `GEMINI_API_KEY`
     - Value: `AIzaSyBs-pWXbnSMfFXd6zh1Xgj34SPBwQ6WvmA`
   - Click **Save Changes**
   - Click **Manual Deploy** → **Deploy latest commit**

---

## STEP 3: Deploy Manually (If Blueprint Doesn't Work)

### Deploy Backend (Python FastAPI)

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect GitHub repo: `MukundC25/Refine`
4. Configure:
   - **Name:** refine-backend
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

5. Add Environment Variables:
   ```
   GEMINI_API_KEY=AIzaSyBs-pWXbnSMfFXd6zh1Xgj34SPBwQ6WvmA
   SECRET_KEY=(generate random string)
   DATABASE_URL=(will get from PostgreSQL step)
   ```

6. Click **Create Web Service**

### Deploy PostgreSQL Database

1. Click **"New +"** → **"PostgreSQL"**
2. Name: `refine-db`
3. Plan: Free
4. Click **Create Database**
5. Copy the **Internal Database URL** and add it to backend env vars as `DATABASE_URL`

### Deploy Frontend (Static Site)

1. Click **"New +"** → **"Static Site"**
2. Connect GitHub repo: `MukundC25/Refine`
3. Configure:
   - **Name:** refine-frontend
   - **Runtime:** Node
   - **Build Command:** `cd frontend && npm install && npm run build`
   - **Publish Directory:** `frontend/dist`
   - **Plan:** Free

4. Add Environment Variable:
   ```
   VITE_API_BASE_URL=https://refine-backend.onrender.com
   ```
   (Replace with your actual backend URL after backend deploys)

5. Click **Create Static Site**

---

## STEP 4: Update Frontend API URL

After backend deploys, you need to update the frontend to point to the correct backend URL:

1. Get your backend URL: `https://refine-backend.onrender.com`
2. Go to your **refine-frontend** service on Render
3. Go to **Environment** tab
4. Update `VITE_API_BASE_URL` to your actual backend URL
5. Click **Save Changes**
6. Click **Manual Deploy** → **Deploy latest commit**

---

## STEP 5: Verify Deployment

### Check Backend Health
Open: `https://refine-backend.onrender.com/`
Should show: `{"message":"Refine API is running."}`

### Check Frontend
Open: `https://refine-frontend.onrender.com/`
Should show the Refine landing page

### Test Full Flow
1. Sign up / Log in
2. Upload a resume
3. Enter job description
4. Click "Evaluate Resume"
5. Verify Gemini API is working (should get evaluation results)

---

## Environment Variables Summary

### Backend (refine-backend)
| Variable | Value | Source |
|----------|-------|--------|
| `GEMINI_API_KEY` | `AIzaSyBs-pWXbnSMfFXd6zh1Xgj34SPBwQ6WvmA` | Your API key |
| `SECRET_KEY` | Random 32-char string | Generate or Render auto-generates |
| `DATABASE_URL` | `postgresql://...` | From Render PostgreSQL |

### Frontend (refine-frontend)
| Variable | Value | Source |
|----------|-------|--------|
| `VITE_API_BASE_URL` | `https://refine-backend.onrender.com` | Your backend URL |

---

## Troubleshooting

### Issue: Backend fails to start
- Check logs in Render dashboard
- Verify `GEMINI_API_KEY` is set correctly
- Check `DATABASE_URL` is valid

### Issue: Frontend can't connect to backend
- Verify `VITE_API_BASE_URL` matches backend URL
- Check CORS settings in backend (currently allows all origins)
- Check browser console for errors

### Issue: Database connection errors
- Verify PostgreSQL is running
- Check `DATABASE_URL` format (should start with `postgresql://`)

### Issue: Gemini API not working
- Verify `GEMINI_API_KEY` is set in environment variables
- Check backend logs for API errors
- Test API key locally first

---

## URLs After Deployment

- **Frontend:** `https://refine-frontend.onrender.com`
- **Backend API:** `https://refine-backend.onrender.com`
- **API Health Check:** `https://refine-backend.onrender.com/`

---

## Free Tier Limits (Render)

- **Web Services:** Spin down after 15 min idle, 512 MB RAM
- **PostgreSQL:** 90-day expiration, 1 GB storage
- **Static Sites:** Unlimited, 100 GB bandwidth/month

For production use, consider upgrading to paid plans.

---

## Next Steps After Deployment

1. Test all features (signup, login, resume upload, evaluation)
2. Add custom domain (optional)
3. Set up monitoring
4. Configure backup for database

---

## Support

If issues arise:
1. Check Render logs (most helpful)
2. Test backend API directly with curl/Postman
3. Verify environment variables are set correctly
4. Check Gemini API key has sufficient quota
