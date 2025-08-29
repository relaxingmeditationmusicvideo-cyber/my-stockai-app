# Quick Cloud Deployment to Railway (Free Tier Available)

# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Initialize project
railway init

# 4. Set environment variables
railway variables set ALPHA_VANTAGE_API_KEY=your_api_key_here
railway variables set NODE_ENV=production
railway variables set PORT=3000

# 5. Deploy
railway up

# Your app will be live at: https://your-app-name.up.railway.app

# Alternative: Deploy to Render (also free tier)
# 1. Push code to GitHub
# 2. Connect GitHub to Render
# 3. Create new Web Service
# 4. Set environment variables in dashboard
# 5. Deploy automatically