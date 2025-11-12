# 🚀 XLR8 Deployment Guide

**Complete step-by-step deployment instructions for non-technical users**

## 📋 Prerequisites

Before you begin, you'll need:
- [ ] Computer with internet connection
- [ ] Web browser (Chrome, Firefox, Edge, or Safari)
- [ ] Email address
- [ ] 30-45 minutes of time

**No coding experience required!**

---

## Step 1: Create GitHub Account (5 minutes)

### If you already have a GitHub account, skip to Step 2.

1. **Go to GitHub**
   - Open your web browser
   - Visit: https://github.com/signup

2. **Create Account**
   - Enter your email address
   - Click "Continue"
   - Create a password
   - Create a username
   - Complete the puzzle
   - Click "Create account"

3. **Verify Email**
   - Check your email inbox
   - Find email from GitHub
   - Click the verification link
   - Return to GitHub

✅ **Checkpoint**: You should now be logged into GitHub

---

## Step 2: Upload XLR8 to GitHub (10 minutes)

### Create Repository

1. **Start New Repository**
   - Click the "+" icon (top right of GitHub)
   - Select "New repository"

2. **Repository Settings**
   - **Repository name**: `xlr8-hcmpact`
   - **Description**: "XLR8 by HCMPACT - UKG Implementation Accelerator"
   - **Privacy**: Select "Private" (recommended)
   - **DO NOT** check "Add a README file"
   - Click "Create repository"

### Upload Files

3. **Upload Application Files**
   - On the repository page, click "uploading an existing file"
   - Open File Explorer/Finder
   - Navigate to your xlr8-hcmpact folder
   - Select ALL files and folders:
     - app.py
     - requirements.txt
     - README.md
     - utils/ folder
     - .streamlit/ folder
     - Any other files
   - Drag and drop them into GitHub
   - **Important**: Make sure the folder structure is preserved

4. **Commit Changes**
   - Scroll down to "Commit changes"
   - In the text box, type: "Initial upload of XLR8 v2.0"
   - Click "Commit changes" (green button)

✅ **Checkpoint**: All files should now appear in your GitHub repository

---

## Step 3: Deploy to Railway (15 minutes)

### Create Railway Account

1. **Go to Railway**
   - Visit: https://railway.app

2. **Sign Up with GitHub**
   - Click "Login with GitHub"
   - If prompted, click "Authorize Railway"
   - This connects Railway to your GitHub account

### Deploy XLR8

3. **Create New Project**
   - Click "New Project" button
   - Select "Deploy from GitHub repo"

4. **Select Repository**
   - Find "xlr8-hcmpact" in the list
   - Click on it

5. **Wait for Initial Deploy**
   - Railway will automatically start building
   - This takes 2-3 minutes
   - You'll see a progress bar
   - **First deploy will FAIL - this is normal!**

### Configure Application

6. **Open Settings**
   - Click on your deployment
   - Click "Settings" tab

7. **Add Start Command**
   - Find "Start Command" section
   - Click "Edit"
   - Enter EXACTLY:
     ```
     streamlit run app.py --server.address=0.0.0.0
     ```
   - Click outside the box to save

8. **Generate Domain**
   - Still in Settings, find "Networking" section
   - Click "Generate Domain"
   - Railway creates a URL like: `xlr8-production-xxxx.up.railway.app`
   - **Save this URL somewhere!**

9. **Redeploy**
   - Go back to "Deployments" tab
   - Click "Deploy" button (top right)
   - Wait 2-3 minutes for deployment to complete
   - Status should show "Success" with green checkmark

✅ **Checkpoint**: Your app is now live!

---

## Step 4: Test Application (5 minutes)

### Access XLR8

1. **Open Your Application**
   - Click on your Railway domain URL
   - OR copy/paste it into a new browser tab
   - XLR8 should load with the HCMPACT branding

2. **Test Basic Functions**
   - You should see:
     - "XLR8 by HCMPACT" header
     - Navigation tabs (Home, PDF Parser, Data Analysis, Security)
     - Sidebar with project selector
   - Click through each tab to verify they load

3. **Test PDF Upload (Optional)**
   - Go to "Advanced PDF Parser" tab
   - Try uploading a test PDF
   - Click "Parse PDF"
   - Verify it processes (even if results are empty, that's okay)

✅ **Checkpoint**: Application is working!

---

## Step 5: Share with Team (Optional)

### Get Shareable Link

1. **Copy Your URL**
   - Copy your Railway domain from browser address bar
   - Format: `https://xlr8-production-xxxx.up.railway.app`

2. **Share with Team**
   - Email the URL to team members
   - They can access immediately (no login required)
   - Everyone sees the same application

3. **Security Note**
   - Railway URL is private-ish (long random string)
   - Only people with the link can access
   - For added security, you can add authentication later

---

## 🎉 Deployment Complete!

Your XLR8 application is now live and ready to use!

### What You Have:
- ✅ Live web application
- ✅ Accessible from anywhere
- ✅ PDF parsing capabilities
- ✅ Custom mapping system
- ✅ Secure data handling
- ✅ Professional branding

---

## 💰 Cost & Billing

### Railway Pricing:
- **First $5/month**: FREE (included credit)
- **After free credit**: ~$5-10/month for typical usage
- **Heavy usage**: $10-20/month max

### Setting Budget Limit:

1. **Go to Railway Settings**
   - Click your profile (top right)
   - Select "Account Settings"
   - Go to "Billing" tab

2. **Set Usage Limit**
   - Find "Usage Limit"
   - Set to $10 or $20
   - Click "Save"
   - App will stop if limit reached (protection against overages)

3. **Add Payment Method**
   - Required after free $5 is used
   - Click "Add Payment Method"
   - Enter credit card info
   - Charges happen monthly

---

## 🔧 Maintenance & Updates

### Update Application:

If you need to make changes to XLR8:

1. **Update Files in GitHub**
   - Go to your GitHub repository
   - Navigate to the file you want to edit
   - Click the pencil icon (Edit)
   - Make your changes
   - Scroll down and click "Commit changes"

2. **Railway Auto-Deploys**
   - Railway detects the GitHub change
   - Automatically redeploys
   - Takes 2-3 minutes
   - No action needed on your part

### View Logs (Troubleshooting):

If something goes wrong:

1. **Check Railway Logs**
   - In Railway dashboard
   - Click on your deployment
   - Click "Logs" tab
   - See real-time application logs
   - Look for errors (usually in red)

2. **Common Issues**:
   - **"ModuleNotFoundError"**: Missing dependency - check requirements.txt
   - **"Port already in use"**: Redeploy the application
   - **"Out of memory"**: Upgrade Railway plan or optimize code
   - **"File not found"**: Check file paths and folder structure

---

## 🆘 Troubleshooting Common Issues

### Issue: "This site can't be reached"

**Possible Causes**:
- Deployment still in progress (wait 3 minutes)
- Domain not generated correctly
- Application crashed

**Solutions**:
1. Verify deployment shows "Success" in Railway
2. Check logs for errors
3. Try redeploying
4. Generate new domain if needed

### Issue: "Application Error"

**Possible Causes**:
- Wrong start command
- Missing dependencies
- File structure incorrect

**Solutions**:
1. Verify start command: `streamlit run app.py --server.address=0.0.0.0`
2. Check all files uploaded to GitHub
3. Review logs for specific error
4. Redeploy application

### Issue: "PDF Won't Upload"

**Possible Causes**:
- File too large
- Wrong file type
- Browser cache issue

**Solutions**:
1. Check file size (< 25MB recommended)
2. Ensure file is .pdf format
3. Clear browser cache
4. Try different browser
5. Check Railway logs

### Issue: "Changes Not Showing"

**Possible Causes**:
- GitHub not updated
- Railway hasn't redeployed
- Browser cache

**Solutions**:
1. Verify changes committed to GitHub
2. Wait for Railway auto-deploy (2-3 min)
3. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
4. Clear browser cache
5. Try incognito/private window

---

## 📞 Getting Help

### Before Contacting Support:

1. **Check Logs**
   - Railway logs show most errors
   - Look for red text or "ERROR"
   - Copy error messages

2. **Try Basic Fixes**
   - Redeploy application
   - Clear browser cache
   - Try different browser
   - Wait 5 minutes and try again

3. **Gather Information**
   - Railway URL
   - Error messages from logs
   - Steps to reproduce issue
   - Browser and OS version

### Contact Options:

**For Deployment Issues**:
- Railway documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

**For XLR8 Application Issues**:
- Review README.md
- Check troubleshooting sections
- Contact HCMPACT support team

---

## ✅ Post-Deployment Checklist

After successful deployment:

- [ ] Application loads successfully
- [ ] All tabs are accessible
- [ ] PDF upload works
- [ ] Mapping template generation works
- [ ] HTML editor downloads correctly
- [ ] Excel export functions properly
- [ ] Shared URL with team
- [ ] Budget limit set in Railway
- [ ] Payment method added (if past free tier)
- [ ] Bookmarked application URL
- [ ] Saved Railway login credentials
- [ ] Team trained on basic usage

---

## 🎓 Next Steps

Now that XLR8 is deployed:

1. **Test with Real Data**
   - Start with a small sample PDF
   - Generate and customize mapping
   - Verify output accuracy
   - Adjust mappings as needed

2. **Create Mapping Library**
   - Save configurations per customer
   - Organize JSON files by client
   - Share within team
   - Document any customizations

3. **Train Your Team**
   - Share this guide
   - Demo the workflow
   - Practice with sample data
   - Answer questions

4. **Monitor Usage**
   - Check Railway usage weekly
   - Review costs
   - Optimize if needed
   - Scale up if necessary

---

**Congratulations! You've successfully deployed XLR8!** 🎉

**Application URL**: [Your Railway URL Here]

**Need help?** Refer back to this guide or contact support.

---

**Last Updated**: November 2024  
**Version**: 2.0  
**Deployed by**: [Your Name]  
**Deployment Date**: [Date]
