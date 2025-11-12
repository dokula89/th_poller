# GitHub Upload Instructions

## Step 1: Install Git

1. Download Git for Windows from: https://git-scm.com/download/win
2. Run the installer with default settings
3. Restart your terminal/PowerShell

## Step 2: Configure Git (First Time Only)

Open PowerShell and run:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 3: Create GitHub Repository

1. Go to https://github.com
2. Click the **+** icon in top right → **New repository**
3. Repository name: `th_poller` (or your preferred name)
4. Description: "Real Estate Listing Extraction System"
5. Choose **Private** (recommended) or **Public**
6. **DO NOT** initialize with README (we already have one)
7. Click **Create repository**

## Step 4: Push Your Code to GitHub

Navigate to your project folder and run these commands:

```bash
# Navigate to your project
cd c:\Users\dokul\Desktop\robot\th_poller

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: TH Poller v1.0"

# Add your GitHub repository as remote (replace USERNAME and REPO_NAME)
git remote add origin https://github.com/USERNAME/REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 5: Verify Upload

1. Go to your GitHub repository URL
2. You should see all your files listed
3. README.md will be displayed automatically

## Important Notes

### Files That Will Be Uploaded:
✅ All Python files (.py, .pyw)
✅ Configuration files (.json, .md)
✅ PowerShell scripts (.ps1)
✅ Documentation (README.md, markdown files)
✅ PHP files if present in the directory

### Files That Will Be Ignored (via .gitignore):
❌ `__pycache__/` and `*.pyc` files
❌ `debug_queue.log` and other logs
❌ `Captures/` folder (HTML/JSON captures)
❌ `.vscode/` IDE settings
❌ `*.pid` process files

### Sensitive Information Warning

Before uploading, **REMOVE OR REPLACE** any sensitive data:

1. **Database credentials** in PHP files:
   - Host: `172.104.206.182`
   - User: `seattlelisted_usr`
   - Password: `T@5z6^pl}`

2. **API keys** or tokens in any configuration files

### To Remove Sensitive Data:

Option 1: Use environment variables (recommended)
Option 2: Create a `config.example.php` with placeholder values
Option 3: Use a `.env` file (already in .gitignore)

## Alternative: GitHub Desktop (GUI)

If you prefer a graphical interface:

1. Download GitHub Desktop: https://desktop.github.com/
2. Install and sign in to GitHub
3. File → Add Local Repository → Select `th_poller` folder
4. Click "Publish repository"
5. Choose visibility (Private/Public)
6. Click "Publish"

## Updating After Initial Upload

After making changes:

```bash
git add .
git commit -m "Description of changes"
git push
```

## Need Help?

- GitHub Docs: https://docs.github.com/en/get-started
- Git Basics: https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup
- Contact: Check GitHub community forums

---

**Repository prepared on:** November 1, 2025
**Files ready:** ✅ .gitignore, README.md, requirements.txt
