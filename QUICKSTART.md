# ⚡ Quick Start Guide

**Deploy XLR8 in 30 Minutes - No Coding Required**

## The 3-Step Process

### Step 1: Upload to GitHub (10 min)
1. Go to https://github.com/signup (create account if needed)
2. Create new repository: https://github.com/new 
   - Name: `xlr8-hcmpact`
   - Privacy: Private
   - Don't add README
3. Upload ALL files from this folder
4. Click "Commit changes"

### Step 2: Deploy to Railway (15 min)
1. Go to https://railway.app/
2. Login with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select `xlr8-hcmpact`
5. Go to Settings:
   - Generate Domain (copy this URL!)
   - Start Command: `streamlit run app.py --server.address=0.0.0.0`
6. Click "Redeploy"
7. Wait 3 minutes

### Step 3: Test (5 min)
1. Open your Railway URL
2. Navigate to "Advanced PDF Parser" tab
3. Upload a test PDF
4. Click "Parse PDF"
5. Done! 🎉

## 🎯 Quick Feature Test

### Test PDF Parsing:
1. Upload any PDF with tables
2. Click "🚀 Parse PDF"
3. Review extracted data
4. Download as Excel

### Test Custom Mapping:
1. Click "🗺️ Generate Mapping Template"
2. Download "📝 Mapping Editor (HTML)"
3. Open HTML file in browser
4. Edit field mappings
5. Download modified JSON
6. Upload JSON back to XLR8
7. Re-parse with custom mappings

## 💰 Cost
- **First month**: FREE ($5 credit)
- **Ongoing**: $5-10/month
- **Tip**: Set budget limit to $10 in Railway settings

## 🔐 Security
- All data stays in your Railway environment
- No external API calls by default
- PII automatically detected and anonymized
- Encrypted data transmission

## 🆘 Need Detailed Help?
See **DEPLOYMENT_GUIDE.md** for:
- Step-by-step screenshots
- Troubleshooting tips
- Common issues and solutions
- Maintenance instructions

## 📞 Common Questions

**Q: Do I need to install anything?**  
A: No! Everything runs in the cloud.

**Q: Can my team access it?**  
A: Yes! Share your Railway URL with anyone.

**Q: What if I mess up?**  
A: Just redeploy from Railway. Your code is safe in GitHub.

**Q: How do I update the app?**  
A: Update files in GitHub → Railway auto-deploys.

## ✅ Success Checklist

After deployment:
- [ ] Application loads at Railway URL
- [ ] Can upload PDF files
- [ ] Parsing works (even with test data)
- [ ] Can download results
- [ ] Mapping editor downloads
- [ ] Team can access URL

---

**That's it! You're ready to accelerate UKG implementations!** 🚀

For detailed documentation, see README.md
