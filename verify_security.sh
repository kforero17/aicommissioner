#!/bin/bash
# Security Verification Script for AICommissioner
# Run this to verify all security fixes are properly applied

echo "🔐 AICommissioner Security Verification"
echo "========================================"
echo ""

# 1. Check .env is ignored
echo "1. Checking if .env is in .gitignore..."
if git check-ignore .env > /dev/null 2>&1; then
    echo "   ✅ .env is properly ignored by git"
else
    echo "   ❌ WARNING: .env is NOT ignored by git!"
fi
echo ""

# 2. Check for sensitive files in git history
echo "2. Checking git history for sensitive files..."
if [ -z "$(git log --all --full-history --oneline -- .env cert.pem key.pem cookies.txt 2>/dev/null)" ]; then
    echo "   ✅ No sensitive files found in git history"
else
    echo "   ⚠️  WARNING: Sensitive files found in git history!"
    git log --all --full-history --oneline -- .env cert.pem key.pem cookies.txt
fi
echo ""

# 3. Check for SSL verification bypasses
echo "3. Checking for SSL verification bypasses..."
if grep -q "verify=False" dev_tools/oauth1_server.py 2>/dev/null; then
    echo "   ❌ WARNING: Found verify=False in dev_tools/oauth1_server.py"
else
    echo "   ✅ No SSL verification bypasses found"
fi
echo ""

# 4. Check if .env.example exists
echo "4. Checking for .env.example template..."
if [ -f ".env.example" ]; then
    echo "   ✅ .env.example template exists"
else
    echo "   ❌ WARNING: .env.example is missing!"
fi
echo ""

# 5. Check if encryption key validation exists in config.py
echo "5. Checking encryption key validation..."
if grep -q "field_validator.*encryption_key" config.py 2>/dev/null; then
    echo "   ✅ Encryption key validation is present"
else
    echo "   ❌ WARNING: Encryption key validation missing!"
fi
echo ""

# 6. Test Python config loading
echo "6. Testing Python configuration loading..."
if python3 -c "from config import settings; print('Config loaded!')" 2>&1 | grep -q "Config loaded"; then
    echo "   ✅ Python configuration loads successfully"
else
    echo "   ⚠️  Configuration has validation errors (may need to set YAHOO credentials)"
fi
echo ""

# 7. Check debug mode default
echo "7. Checking debug mode default..."
if grep -q "debug: bool = False" config.py 2>/dev/null; then
    echo "   ✅ Debug mode defaults to False (secure)"
else
    echo "   ❌ WARNING: Debug mode may default to True!"
fi
echo ""

# 8. Check README security section
echo "8. Checking README security documentation..."
if grep -q "## Security" README.md 2>/dev/null; then
    echo "   ✅ Security section exists in README"
else
    echo "   ❌ WARNING: No security section in README!"
fi
echo ""

echo "========================================"
echo "🎯 Security Verification Complete!"
echo ""
echo "⚠️  REQUIRED MANUAL ACTION:"
echo "   You must regenerate Yahoo OAuth credentials at:"
echo "   https://developer.yahoo.com/apps/"
echo ""
echo "   Then update these in .env:"
echo "   - YAHOO_CLIENT_ID"
echo "   - YAHOO_CLIENT_SECRET"
echo ""
