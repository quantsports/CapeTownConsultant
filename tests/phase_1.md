# Phase 1 Implementation Guide: Critical Bug Fixes

## 🎯 Overview

This guide provides step-by-step instructions to implement all Phase 1 critical bug fixes for the CapeTownConsultant project.

---

## 📦 Files to Update

### 1. **src/tools/schemas.py** 
- Fix memory_upsert schema (remove 'id' requirement)
- Fix profile_read schema (make 'keys' optional)

### 2. **src/tools/executor.py**
- Enhanced validation for memory_upsert items
- Handle optional keys in profile_read

### 3. **src/services/embeddings.py**
- Add event loop safety to rate limiter

### 4. **src/services/search/google.py**
- Add event loop safety to rate limiter

### 5. **tests/test_phase1_fixes.py** (NEW FILE)
- Comprehensive test suite

---

## 🔧 Step-by-Step Implementation

### Step 1: Backup Current Files

```bash
# Create a backup branch
git checkout -b phase1-bug-fixes
git add .
git commit -m "Backup before Phase 1 fixes"

# Create backup directory
mkdir -p backups/phase1
cp src/tools/schemas.py backups/phase1/
cp src/tools/executor.py backups/phase1/
cp src/services/embeddings.py backups/phase1/
cp src/services/search/google.py backups/phase1/
```

### Step 2: Apply File Updates

Replace the content of each file with the fixed versions provided in the artifacts:

1. **src/tools/schemas.py** → Use `schemas.py (Fixed)` artifact
2. **src/tools/executor.py** → Use `executor.py (Fixed)` artifact
3. **src/services/embeddings.py** → Use `embeddings.py (Fixed)` artifact
4. **src/services/search/google.py** → Use `google.py (Fixed)` artifact

### Step 3: Create Test Suite

```bash
# Create tests directory if it doesn't exist
mkdir -p tests

# Add the test file
# Use content from test_phase1_fixes.py artifact
```

### Step 4: Install Test Dependencies

```bash
# Ensure pytest and pytest-asyncio are installed
pip install pytest pytest-asyncio pytest-mock
```

---

## ✅ Verification Steps

### Quick Verification (5 minutes)

```bash
# 1. Test imports (should complete without errors)
python -c "from src.tools.schemas import ToolSchemas; print('✅ Schemas import OK')"
python -c "from src.tools.executor import ToolExecutor; print('✅ Executor import OK')"
python -c "from src.services.embeddings import EmbeddingService; print('✅ Embeddings import OK')"

# 2. Verify schema changes
python -c "
from src.tools.schemas import ToolSchemas
schema = ToolSchemas.SCHEMAS['memory_upsert']
assert 'items' in schema['required']
profile_schema = ToolSchemas.SCHEMAS['profile_read']
assert len(profile_schema['required']) == 0
print('✅ Schema fixes verified')
"
```

### Comprehensive Testing (15 minutes)

```bash
# Run the full test suite
pytest tests/test_phase1_fixes.py -v --tb=short

# Expected output:
# ✅ test_schema_requires_only_text PASSED
# ✅ test_function_definition_correct PASSED
# ✅ test_executor_validates_items_structure PASSED
# ✅ test_schema_has_no_required_params PASSED
# ✅ test_executor_handles_optional_keys PASSED
# ✅ test_embedding_service_rate_limiter_loop_safety PASSED
# ... and more
```

### Manual Integration Testing (10 minutes)

#### Test 1: Memory Operations
```bash
# Start CLI
python main.py

# Test memory storage (previously would fail)
You: Remember that I'm a restaurant owner specializing in Italian cuisine

# Expected: Should work without schema validation errors
# Look for: "memory_upsert_success" in logs

# Test memory recall
You: What do you know about me?

# Expected: Should retrieve and display stored information
```

#### Test 2: Profile Operations
```bash
# In CLI
You: Can you check my full profile?

# Expected: Should work without requiring 'keys' parameter

# Test specific keys
You: What's my role and industry?

# Expected: Should retrieve specific profile fields
```

#### Test 3: Streamlit UI
```bash
# Start Streamlit
streamlit run streamlit_app.py

# Navigate to Memory tab
# - Try searching memories
# - Should work without errors

# Navigate to Profile tab
# - View current profile (full)
# - Add new profile data
# - Should work correctly
```

---

## 🐛 Troubleshooting

### Issue: Import Errors

**Symptom**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Test Failures

**Symptom**: Tests fail with "event loop is closed" or similar

**Solution**:
```bash
# Install latest pytest-asyncio
pip install --upgrade pytest-asyncio

# Run with explicit asyncio mode
pytest tests/test_phase1_fixes.py --asyncio-mode=auto -v
```

### Issue: Pinecone Connection Errors

**Symptom**: Tests fail due to missing Pinecone API key

**Solution**: These tests mock Pinecone, but ensure:
```bash
# Add to .env (or use dummy value for tests)
PINECONE_API_KEY=test-key-for-local-testing
```

### Issue: Rate Limiter Warnings

**Symptom**: Warnings about event loops

**Solution**: This is expected if running in notebooks or certain environments. The fixes handle this gracefully.

---

## 📊 Expected Test Results

### All Tests Passing:
```
tests/test_phase1_fixes.py::TestMemoryUpsertSchema::test_schema_requires_only_text PASSED
tests/test_phase1_fixes.py::TestMemoryUpsertSchema::test_function_definition_correct PASSED
tests/test_phase1_fixes.py::TestMemoryUpsertSchema::test_executor_validates_items_structure PASSED
tests/test_phase1_fixes.py::TestProfileReadSchema::test_schema_has_no_required_params PASSED
tests/test_phase1_fixes.py::TestProfileReadSchema::test_function_definition_allows_empty_params PASSED
tests/test_phase1_fixes.py::TestProfileReadSchema::test_executor_handles_optional_keys PASSED
tests/test_phase1_fixes.py::TestProfileReadSchema::test_profile_manager_handles_none_keys PASSED
tests/test_phase1_fixes.py::TestEventLoopSafety::test_embedding_service_rate_limiter_loop_safety PASSED
tests/test_phase1_fixes.py::TestEventLoopSafety::test_rate_limiter_recreated_for_new_loop PASSED
tests/test_phase1_fixes.py::TestEventLoopSafety::test_multiple_services_independent_limiters PASSED
tests/test_phase1_fixes.py::TestMemoryExtractionIntegration::test_memory_extraction_with_auto_memory PASSED
tests/test_phase1_fixes.py::TestMemoryExtractionIntegration::test_full_chat_flow_with_memory_storage PASSED
tests/test_phase1_fixes.py::TestEdgeCases::test_memory_upsert_with_special_characters PASSED
tests/test_phase1_fixes.py::TestEdgeCases::test_profile_read_nonexistent_keys PASSED
tests/test_phase1_fixes.py::TestEdgeCases::test_concurrent_rate_limiters PASSED

==================== 15 passed in 2.34s ====================
```

---

## 🎉 Success Criteria

Your implementation is successful when:

- ✅ All 15 tests pass
- ✅ No import errors
- ✅ CLI can store and retrieve memories
- ✅ Streamlit Memory and Profile tabs work
- ✅ No schema validation errors in logs
- ✅ Auto-memory extraction works during conversations

---

## 🔄 Rollback Procedure

If issues arise:

```bash
# Restore from backup
cp backups/phase1/*.py src/tools/
cp backups/phase1/embeddings.py src/services/
cp backups/phase1/google.py src/services/search/

# Or use git
git checkout HEAD~1 -- src/tools/schemas.py src/tools/executor.py
```

---

## 📝 Commit Message Template

```
fix: Phase 1 critical bug fixes

- Fix memory_upsert schema: remove 'id' requirement, auto-generate IDs
- Fix profile_read schema: make 'keys' optional for full profile reads
- Add event loop safety to EmbeddingService rate limiter
- Add event loop safety to GoogleSearch rate limiter
- Enhanced validation in ToolExecutor for memory items
- Add comprehensive test suite (15 tests)

Resolves: #1, #2, #3, #4 (schema mismatches and event loop issues)
```

---

## 🚀 Next Steps

After Phase 1 is complete and verified:

1. **Monitor Production**: Watch logs for any new issues
2. **Phase 2 Planning**: Review optimization opportunities
3. **Documentation**: Update API docs with schema changes
4. **User Communication**: Notify users of improvements

---

## 📞 Support

If you encounter issues:

1. Check logs in `cache/logs/app.log`
2. Run tests with `-vv` flag for detailed output
3. Verify all dependencies are up to date
4. Review the specific error messages carefully

---

**Estimated Total Time**: 30-45 minutes
**Risk Level**: Low (fixes are isolated and well-tested)
**Reversibility**: High (easy rollback via git or backups)