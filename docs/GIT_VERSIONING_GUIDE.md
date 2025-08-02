# Git Versioning Guide for ERP General Ledger System 📚

A comprehensive guide to version control for your ERP project using Git and GitHub.

## 🎯 Core Concepts

### 1. **Commits = Snapshots**
Each commit is a complete snapshot of your project at a specific point in time.

```bash
# Your current commit
cbf239a - "Initial commit: Complete ERP General Ledger System"
```

Think of it like saving different versions of a document:
- `ProjectV1.doc` → Commit 1
- `ProjectV2.doc` → Commit 2  
- `ProjectV3.doc` → Commit 3

But Git is much smarter - it only stores the changes between versions.

### 2. **Branches = Parallel Development**
Branches let you work on different features simultaneously without breaking your main code.

```
main branch:     A ─── B ─── C ─── D
                      │
feature branch:       └─ E ─── F ─── G
```

## 🛠️ Common Versioning Workflows

### **Making Changes to Your ERP System**

Let's say you want to add a new analytics report:

```bash
# 1. Check current status
git status

# 2. Create a new branch for your feature
git checkout -b feature/cash-flow-analytics

# 3. Make your changes (edit files, add new pages, etc.)
# ... work on your new cash flow analytics page ...

# 4. Stage your changes
git add pages/Cash_Flow_Analytics.py
git add utils/cash_flow_utils.py

# 5. Commit your changes
git commit -m "Add cash flow analytics with trend analysis

• New cash flow analytics page with monthly trends
• Added cash flow utility functions
• Enhanced navigation to include cash flow metrics
• Interactive charts showing operating, investing, financing flows"

# 6. Push your branch to GitHub
git push -u origin feature/cash-flow-analytics
```

### **Viewing History**

```bash
# See all commits
git log --oneline

# See detailed history
git log --graph --pretty=format:"%h %s (%an, %ar)"

# See what changed in a specific commit
git show cbf239a

# See file history
git log --follow -- pages/Balance_Sheet.py
```

## 🌿 Branching Strategies

### **Feature Branch Workflow** (Recommended for your ERP)

```
main branch:         A ─── B ─── C ─── D ─── H
                          │             │   │
analytics branch:         └─ E ─── F ───┘   │
                                           │
reporting branch:                     G ───┘
```

**Example branches for your ERP:**
- `main` - Stable, production-ready code
- `feature/advanced-analytics` - New analytics features
- `feature/mobile-ui` - Mobile-responsive interface
- `bugfix/pdf-export-fix` - Fix PDF generation issues
- `feature/audit-trail` - Add audit logging
- `feature/inventory-tracking` - Inventory management module
- `hotfix/security-patch` - Urgent security fixes

### **Creating and Managing Branches**

```bash
# Create and switch to new branch
git checkout -b feature/inventory-tracking

# Switch between branches
git checkout main
git checkout feature/inventory-tracking

# See all branches
git branch -a

# See current branch
git branch

# Delete a branch (after merging)
git branch -d feature/inventory-tracking

# Delete remote branch
git push origin --delete feature/inventory-tracking
```

## 🔄 Merging Changes

### **Merge vs. Rebase**

**Merge** (preserves history):
```
main:     A ─── B ─── C ─── D ─── M
               │               │
feature:       └─ E ─── F ─────┘
```

**Rebase** (clean, linear history):
```
main:     A ─── B ─── C ─── D ─── E' ─── F'
```

```bash
# Merge approach (recommended for collaboration)
git checkout main
git pull origin main  # Get latest changes
git merge feature/cash-flow-analytics

# Rebase approach (cleaner history)
git checkout feature/cash-flow-analytics
git rebase main
git checkout main
git merge feature/cash-flow-analytics

# Fast-forward merge (when possible)
git merge --ff-only feature/simple-fix
```

## 🏷️ Tagging Releases

Tags mark important milestones (like releases):

```bash
# Create a tag for version 1.0
git tag -a v1.0.0 -m "ERP GL System v1.0.0 - Initial Release

Features:
• Complete financial reporting suite
• Advanced analytics dashboard
• User authentication and management
• PDF export capabilities"

# Push tags to GitHub
git push origin v1.0.0

# Push all tags
git push origin --tags

# See all tags
git tag -l

# See tag details
git show v1.0.0

# Delete a tag
git tag -d v1.0.0
git push origin --delete tag v1.0.0
```

## 📈 Versioning Your ERP System

### **Semantic Versioning (Recommended)**

Format: `MAJOR.MINOR.PATCH` (e.g., `v2.1.3`)

- **MAJOR** (2): Breaking changes, major new features
- **MINOR** (1): New features, backwards compatible
- **PATCH** (3): Bug fixes, small improvements

**Example progression for your ERP:**
- `v1.0.0` - Initial release (what you have now)
- `v1.1.0` - Add inventory management module
- `v1.1.1` - Fix PDF export bug
- `v1.2.0` - Add mobile responsive design
- `v1.3.0` - Add API endpoints
- `v2.0.0` - Major UI redesign, database schema changes

### **Release Workflow Example**

```bash
# Working on version 1.1.0
git checkout -b release/v1.1.0

# Make final adjustments, update version numbers
# Edit version files, update changelogs, etc.
git commit -m "Prepare release v1.1.0"

# Merge to main
git checkout main
git merge release/v1.1.0

# Tag the release
git tag -a v1.1.0 -m "Release v1.1.0 - Inventory Management

New Features:
• Inventory tracking and management
• Stock level alerts
• Purchase order integration
• Inventory valuation methods

Bug Fixes:
• Fixed PDF export formatting issues
• Improved database query performance
• Enhanced error handling"

# Push everything
git push origin main
git push origin v1.1.0

# Clean up release branch
git branch -d release/v1.1.0
```

## 🔍 Practical Examples for Your ERP

### **Scenario 1: Adding New Analytics Page**

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/profit-loss-analytics

# 2. Create new files and develop
touch pages/Profit_Loss_Analytics.py
# ... develop the feature ...
# Edit utils/navigation.py to add menu item

# 3. Test your changes
# Run your application and test the new feature

# 4. Commit changes with descriptive message
git add pages/Profit_Loss_Analytics.py utils/navigation.py
git commit -m "Add profit & loss analytics with YoY comparison

• New P&L analytics page with year-over-year comparison
• Monthly and quarterly trend analysis
• Variance analysis with color-coded indicators
• Export functionality for P&L data
• Added navigation menu item for P&L analytics"

# 5. Push and create pull request on GitHub
git push -u origin feature/profit-loss-analytics
# Then create PR on GitHub web interface
```

### **Scenario 2: Fixing a Bug**

```bash
# 1. Create bugfix branch
git checkout main
git pull origin main
git checkout -b bugfix/pdf-export-formatting

# 2. Fix the issue
# ... edit utils/pdf_generator.py ...

# 3. Test the fix
# Verify the bug is resolved

# 4. Commit fix with detailed description
git add utils/pdf_generator.py
git commit -m "Fix PDF formatting issue with long account names

• Truncate account names that exceed column width
• Add ellipsis (...) for truncated names
• Ensure consistent table formatting across all reports
• Add word wrapping for long descriptions
• Fix alignment issues in multi-line cells

Fixes: #123 (if you're using GitHub issues)"

# 5. Merge back to main (for hotfixes)
git checkout main
git merge bugfix/pdf-export-formatting
git push origin main

# 6. Clean up
git branch -d bugfix/pdf-export-formatting
```

### **Scenario 3: Viewing Project History**

```bash
# See what's changed since last version
git log v1.0.0..HEAD --oneline

# See commits by author
git log --author="antonbenosapro"

# See changes in last week
git log --since="1 week ago"

# See who changed what in a specific file
git blame pages/Balance_Sheet.py

# Compare two versions
git diff v1.0.0 v1.1.0

# See changes in a specific commit
git show --stat cbf239a

# Search commit messages
git log --grep="PDF"
```

## 🚀 Advanced Features

### **Rollback to Previous Version**

```bash
# Revert specific commit (safe, creates new commit)
git revert HEAD
git revert cbf239a

# Reset to specific commit (DESTRUCTIVE - use carefully)
git reset --soft HEAD~1    # Keep changes staged
git reset --mixed HEAD~1   # Keep changes unstaged
git reset --hard HEAD~1    # LOSE ALL CHANGES

# Reset specific file to previous version
git checkout HEAD~1 -- pages/Balance_Sheet.py
```

### **Stashing Work in Progress**

```bash
# Save current work without committing
git stash save "WIP: working on new analytics feature"

# See all stashes
git stash list

# Apply latest stash
git stash pop

# Apply specific stash
git stash apply stash@{1}

# Create branch from stash
git stash branch feature/new-work stash@{0}
```

### **Cherry-picking Commits**

```bash
# Apply specific commit to current branch
git cherry-pick abc1234

# Cherry-pick multiple commits
git cherry-pick abc1234 def5678

# Cherry-pick without committing (review first)
git cherry-pick --no-commit abc1234
```

### **Interactive Rebase (Clean up History)**

```bash
# Clean up last 3 commits
git rebase -i HEAD~3

# Options in interactive mode:
# pick = use commit
# reword = change commit message
# edit = stop to amend commit
# squash = combine with previous commit
# drop = remove commit
```

## 🔧 Useful Git Commands for Daily Development

### **Status and Information**

```bash
# Current status
git status
git status -s  # Short format

# Current branch
git branch --show-current

# Remote information
git remote -v

# Configuration
git config --list
```

### **Synchronizing with Remote**

```bash
# Fetch latest changes (don't merge)
git fetch origin

# Pull latest changes (fetch + merge)
git pull origin main

# Push current branch
git push

# Push new branch
git push -u origin feature/new-branch

# Force push (use carefully)
git push --force-with-lease origin feature/branch
```

### **Undoing Changes**

```bash
# Unstage file
git reset HEAD filename.py

# Discard unstaged changes
git checkout -- filename.py

# Discard all unstaged changes
git checkout .

# Amend last commit (if not pushed yet)
git commit --amend -m "Updated commit message"
```

## 🎯 Best Practices for Your ERP

### 1. **Descriptive Commit Messages**

**Good Examples:**
```bash
git commit -m "Add revenue forecasting to analytics dashboard

• Implement 12-month revenue projection algorithm
• Add interactive forecast charts with confidence intervals  
• Include scenario planning (optimistic/realistic/pessimistic)
• Update navigation to include forecasting section
• Add unit tests for forecasting calculations"

git commit -m "Fix user authentication timeout issue

• Increase session timeout from 30 to 60 minutes
• Add automatic session renewal for active users
• Improve error messaging for expired sessions
• Update session cleanup background task"
```

**Bad Examples:**
```bash
git commit -m "fixed stuff"
git commit -m "updates"
git commit -m "."
```

### 2. **Logical Commits**
- One feature or fix per commit
- Keep related changes together
- Separate formatting from functional changes
- Don't mix unrelated changes

### 3. **Branch Naming Conventions**
- `feature/descriptive-name` - New features
- `bugfix/issue-description` - Bug fixes
- `hotfix/urgent-fix` - Urgent production fixes
- `release/version-number` - Release preparation
- `docs/documentation-update` - Documentation changes

### 4. **Regular Synchronization**
```bash
# Daily routine
git checkout main
git pull origin main
git checkout your-feature-branch
git rebase main  # Keep your branch up to date
```

### 5. **Code Review Process**
- Always use Pull Requests for main branch
- Review code before merging
- Use GitHub's review features
- Test before merging

## 📝 Common Workflows Summary

### **Feature Development**
```bash
git checkout main
git pull origin main
git checkout -b feature/new-feature
# ... develop ...
git add .
git commit -m "Descriptive message"
git push -u origin feature/new-feature
# Create PR on GitHub
```

### **Bug Fix**
```bash
git checkout main
git pull origin main
git checkout -b bugfix/fix-description
# ... fix bug ...
git add .
git commit -m "Fix: description of fix"
git push -u origin bugfix/fix-description
# Create PR on GitHub
```

### **Release Preparation**
```bash
git checkout -b release/v1.2.0
# Update version numbers, changelog
git commit -m "Prepare release v1.2.0"
git checkout main
git merge release/v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin main
git push origin v1.2.0
```

## 🆘 Emergency Procedures

### **Accidentally Committed to Wrong Branch**
```bash
# Move last commit to correct branch
git reset --soft HEAD~1
git stash
git checkout correct-branch
git stash pop
git commit
```

### **Need to Undo Last Commit (Not Pushed)**
```bash
git reset --soft HEAD~1  # Keep changes
git reset --hard HEAD~1  # Lose changes
```

### **Pushed Bad Commit to Main**
```bash
# Revert the commit (creates new commit)
git revert bad-commit-hash
git push origin main
```

## 🔗 GitHub Integration

### **Creating Pull Requests**
1. Push your feature branch to GitHub
2. Go to your repository on GitHub
3. Click "Compare & pull request"
4. Fill in description with:
   - What changes were made
   - Why they were made
   - How to test them
   - Any breaking changes

### **Using GitHub Issues**
- Link commits to issues: `git commit -m "Fix user login bug - Fixes #123"`
- Reference issues: `git commit -m "Improve performance - Related to #456"`

---

## 📚 Additional Resources

- [Official Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)

---

**Remember**: Version control is about collaboration, history, and safety. When in doubt, commit early and often with good messages. You can always clean up history later with interactive rebase before sharing your work!