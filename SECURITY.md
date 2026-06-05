# 🛡️ Security Guidelines

## Critical Rules

### 1. **NEVER Commit Secrets**
```bash
# ❌ WRONG
git add .env
git commit -m "Adding env file"

# ✅ CORRECT
# Just commit .env.example (template only)
git add .env.example
```

### 2. **Environment Variables**
```bash
# Create .env from template
cp .env.example .env

# Add your real keys
ANTHROPIC_API_KEY=your_actual_key
TAVILY_API_KEY=your_actual_key

# .gitignore protects it automatically
```

### 3. **Token Management**
- 🔑 Store tokens in `.env` only
- 🚫 NEVER hardcode in Python files
- 🔄 Rotate tokens regularly
- 🗑️ Revoke old tokens from GitHub

### 4. **If You Accidentally Commit a Secret**
```bash
# IMMEDIATELY do this:

# 1. Revoke the secret on GitHub
# 2. Create new token
# 3. Replace in .env

# 4. Remove from git history
git rm --cached .env
git commit --amend

# 5. Force push (DANGEROUS!)
git push -f origin main
```

### 5. **Before Each Commit**
```bash
# Check: No secrets in staged files
git diff --cached | grep -i "password\|token\|key\|secret"

# If found: Remove with
git reset HEAD filename
# Then add .env.example instead
```

## File Permissions

```bash
# .gitignore = Auto protected ✅
# .env = NEVER commit ✅
# .env.example = Safe to commit (template) ✅
# secrets/ folder = Auto ignored ✅
```

## Best Practices

1. ✅ Use `.env.example` as template
2. ✅ Keep `.gitignore` updated
3. ✅ Rotate tokens regularly
4. ✅ Use strong passwords
5. ✅ Enable 2FA on GitHub
6. ✅ Review `.git diff` before commit
7. ✅ Use pre-commit hooks (coming next!)

## Tools to Prevent Leaks

- `git-secrets` - Scan for secrets
- `detect-secrets` - Automatic detection
- GitHub Secret Scanning - Automatic alerts
- Pre-commit hooks - Local checks

---

**Remember: ONE leaked token = ENTIRE account compromised!** 🚨

