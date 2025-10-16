# Installation & Setup Guide

## 🚀 Quick Start

Follow these steps to install the fixed orchestration system.

---

## Step 1: Backup Current Files

```bash
# Create backup directory
mkdir -p backups

# Backup current files
cp src/interface/assistant.py backups/assistant.py.backup
cp src/agent/autonomous.py backups/autonomous.py.backup
cp src/workers/orchestrator.py backups/orchestrator.py.backup
cp src/interface/cli.py backups/cli.py.backup
```

---

## Step 2: Replace Fixed Files

Replace the following files with the corrected versions:

### Required Files

1. **src/interface/assistant.py** - Fixed interface with orchestration support
2. **src/agent/autonomous.py** - Complete agent with orchestration integration
3. **src/workers/orchestrator.py** - Complete orchestrator implementation
4. **src/interface/cli.py** - Fixed CLI with orchestration controls

### New Files

5. **test_orchestration.py** (root directory) - Comprehensive test suite

---

## Step 3: Verify File Structure

Your project should have:

```
capetown-consultant/
├── src/
│   ├── agent/
│   │   └── autonomous.py          ← REPLACED
│   ├── interface/
│   │   ├── assistant.py          ← REPLACED
│   │   └── cli.py                ← REPLACED
│   └── workers/
│       ├── orchestrator.py        ← REPLACED
│       ├── worker.py              (existing)
│       ├── templates.py           (existing)
│       └── context_store.py       (existing)
├── test_orchestration.py          ← NEW
├── main.py                         (existing)
└── requirements.txt                (existing)
```

---

## Step 4: Verify Dependencies

Ensure all required packages are installed:

```bash
pip install -r requirements.txt

# Key packages:
# - openai
# - asyncio
# - aiolimiter
```

---

## Step 5: Configure Environment

Ensure your `.env` file has:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (for enhanced features)
PINECONE_API_KEY=...
SERPAPI_API_KEY=...
GOOGLE_SEARCH_API_KEY=...
PERPLEXITY_API_KEY=...
```

---

## Step 6: Run Tests

Validate the installation:

```bash
# Run comprehensive test suite
python test_orchestration.py test
```

**Expected Output:**
```
🧪 ORCHESTRATION SYSTEM TEST SUITE
==================================================================
Testing all integration points and functionality
==================================================================

TEST 1: Initialization
==================================================================
✅ PASS | Orchestrator initialization
✅ PASS | Orchestration enabled by default
✅ PASS | Orchestration can be disabled

TEST 2: Toggle Functionality
==================================================================
✅ PASS | Initial state
✅ PASS | Toggle to disabled
✅ PASS | Toggle to enabled

[... more tests ...]

TEST SUMMARY
==================================================================
Total Tests: 12
Passed: 12 ✅
Failed: 0 ❌
Success Rate: 100.0%
```

---

## Step 7: Test CLI

```bash
# Start the CLI
python main.py
```

**You should see:**
```
🧠 Autonomous Assistant v3.1 (Multi-Agent Orchestration)
======================================================================
✅ Features: Multi-agent orchestration, Domain specialists
======================================================================

Commands:
  exit      - Exit the program
  clear     - Clear conversation history
  config    - Show configuration
  costs     - Show cost summary
  mode      - Toggle orchestration mode
  workers   - List available workers
  status    - Show current mode and status

🎭 [ORCHESTRATION] You: 
```

---

## Step 8: Test Basic Functionality

Try these commands in the CLI:

### 1. Check Status
```
🎭 [ORCHESTRATION] You: status
```

**Expected:**
```
📊 Current Status:
  Mode: ORCHESTRATION
  User ID: cli_user
  Costs: $0.0000 / $10.00
  Model: gpt-4o
```

### 2. Toggle Mode
```
🎭 [ORCHESTRATION] You: mode
```

**Expected:**
```
✅ Switched to TRADITIONAL mode
```

### 3. List Workers
```
🤖 [TRADITIONAL] You: workers
```

**Expected:**
```
👥 Available Workers:

  Menu Planner
    Priority: 1 | Tools: web_search, wiki_fetch, memory_query
  Cost Analyst
    Priority: 1 | Tools: web_search, memory_query
  [... more workers ...]
```

---

## Step 9: Test Orchestration

Try a complex query:

```
🎭 [ORCHESTRATION] You: Design a spring menu with cost analysis for a casual Italian restaurant
```

**Expected Response Format:**
```
🎭 **Multi-Agent Orchestration Response**

======================================================================

[Synthesized strategic response combining multiple specialists...]

======================================================================
## 📊 Orchestration Metadata

**Workers Engaged:** 3
**Successful:** 3/3
**Total Execution Time:** 45.2s
**Specialists:** Menu Planner, Cost Analyst, Marketing Strategist
```

---

## Step 10: Test Traditional Mode

Toggle to traditional and try a simple query:

```
🎭 [ORCHESTRATION] You: mode
✅ Switched to TRADITIONAL mode

🤖 [TRADITIONAL] You: What is basil?
```

**Expected:** Simple, direct answer without orchestration markers.

---

## 🎯 Verification Checklist

After installation, verify:

- [ ] CLI starts without errors
- [ ] `status` command shows correct mode
- [ ] `mode` command toggles between modes
- [ ] `workers` command lists all 9 specialists
- [ ] `config` shows API keys configured
- [ ] Simple queries work (traditional mode)
- [ ] Complex queries trigger orchestration
- [ ] Test suite passes all tests

---

## 🐛 Troubleshooting

### Issue: ImportError

```bash
# Ensure you're in the project root
cd /path/to/capetown-consultant

# Verify Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Try again
python main.py
```

### Issue: "OpenAI API not configured"

```bash
# Check .env file exists
ls -la .env

# Verify OPENAI_API_KEY is set
python -c "from src.config import Config; print('API Key:', 'Set' if Config.OPENAI_API_KEY else 'Missing')"
```

### Issue: Orchestration not working

```bash
# Run diagnostic
python test_orchestration.py test

# Check logs
tail -f cache/logs/app.log
```

### Issue: Workers timeout

```bash
# This is normal for slow connections
# Workers have 2-minute timeout
# Response will still be delivered with successful workers
```

---

## 🔄 Rollback (if needed)

If you encounter issues:

```bash
# Restore from backups
cp backups/assistant.py.backup src/interface/assistant.py
cp backups/autonomous.py.backup src/agent/autonomous.py
cp backups/orchestrator.py.backup src/workers/orchestrator.py
cp backups/cli.py.backup src/interface/cli.py

# Remove test file
rm test_orchestration.py
```

---

## 📚 Next Steps

Once installed and verified:

1. **Read Documentation**
   - `ORCHESTRATION_FIX_README.md` - Detailed fix explanation
   - `ARCHITECTURE.md` - System architecture
   - `PROJECT_GUIDELINES.md` - Development guidelines

2. **Customize Workers**
   - Edit `src/workers/templates.py` to modify worker prompts
   - Add new workers by extending `WorkerType` enum

3. **Adjust Settings**
   - Modify `src/config/settings.py` for global settings
   - Change `max_workers` in orchestration calls

4. **Monitor Performance**
   - Check logs: `cache/logs/app.log`
   - Track costs: Use `costs` command in CLI

---

## ✅ Success!

If all steps completed successfully, your orchestration system is now:

✅ **Fully Integrated** - Works with main agent  
✅ **Properly Routed** - Intelligently chooses modes  
✅ **Thoroughly Tested** - All tests passing  
✅ **Production Ready** - Error handling complete  

**You can now use multi-agent orchestration for complex queries!**

---

## 💡 Usage Examples

### Simple Query (Traditional)
```python
async with AutonomousAssistant() as assistant:
    response = await assistant.chat("What's a carbonara?", "user123")
```

### Complex Query (Orchestration)
```python
async with AutonomousAssistant() as assistant:
    response = await assistant.chat(
        "Create a comprehensive restaurant plan including menu design, "
        "cost analysis, marketing strategy, and staffing recommendations",
        "user123"
    )
```

---

## 📞 Support

Questions? Check:
1. Test results: `python test_orchestration.py test`
2. Logs: `tail -f cache/logs/app.log`
3. Configuration: `python main.py` → type `config`

---

**Installation Guide Version:** 1.0  
**System Version:** 3.1.0-fixed  
**Status:** ✅ Complete