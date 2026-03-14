# Bulk Update Error Diagnosis Report
**Date**: 2026-01-19
**Task**: `bulk_update.py --top 100` execution analysis

---

## Executive Summary

✅ **System Status**: Working as designed
📊 **Success Rate**: 93/100 (93%)
⚠️ **Failed Symbols**: 7 symbols (due to data source limitation, not system error)

---

## Error Analysis

### Failed Symbols (7 total)

| Symbol | Name | Market | Status in DB | Status in KRX | Yahoo Finance |
|--------|------|--------|--------------|---------------|---------------|
| 0004V0 | 엔비알모션 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |
| 0004Y0 | 디비금융제14호스팩 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |
| 0007C0 | 아크릴 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |
| 0008Z0 | 에스엔시스 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |
| 0009K0 | 에임드바이오 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |
| 0010V0 | 제이피아이헬스케어 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |
| 0013V0 | 삼진식품 | KOSDAQ | ACTIVE | ✅ Listed | ❌ 404 Not Found |

### Key Findings

1. **All failed symbols are valid KRX-listed stocks**
   - Verified against FinanceDataReader's `StockListing('KRX')`
   - All 7 symbols appear in the official KRX listing
   - Status: ACTIVE on KOSDAQ market

2. **Common pattern: Letter+Digit suffix (V0, Y0, C0, Z0, K0)**
   - Total 33 symbols in KRX have similar suffixes
   - These are typically:
     - Recently listed companies
     - SPACs (Special Purpose Acquisition Companies)
     - Small-cap stocks with limited coverage

3. **Root cause: Yahoo Finance data availability**
   - FinanceDataReader uses Yahoo Finance as backend
   - Yahoo Finance does not provide data for all KRX stocks
   - Especially affects:
     - Newly listed stocks (< 6 months)
     - Small market cap companies
     - Special purpose companies (SPACs)
     - Some KOSDAQ stocks with low trading volume

---

## Test Results

### Test 1: FDR Data Retrieval Test
```
Control Group (Known Good Symbols):
  ✅ PASS  005930 (삼성전자) - 244 rows
  ✅ PASS  000660 (SK하이닉스) - 244 rows
  ✅ PASS  005380 (현대차) - 244 rows

Test Group (Failed Symbols):
  ❌ FAIL  0004V0 (엔비알모션) - 404 Error
  ❌ FAIL  0004Y0 (디비금융제14호스팩) - 404 Error
  ❌ FAIL  0007C0 (아크릴) - 404 Error
  ❌ FAIL  0008Z0 (에스엔시스) - 404 Error
  ❌ FAIL  0009K0 (에임드바이오) - 404 Error
  ❌ FAIL  0010V0 (제이피아이헬스케어) - 404 Error
  ❌ FAIL  0013V0 (삼진식품) - 404 Error
```

### Test 2: KRX Listing Verification
```
✅ All 7 symbols verified as ACTIVE in current KRX listing
✅ Symbol codes are correct and valid
✅ No delisting detected
```

---

## Diagnosis

### What's Working Correctly ✅

1. **Symbol Master Sync**: Symbols correctly loaded from KRX
2. **Error Handling**: Failed symbols properly logged to `logs/bulk_update_failed.log`
3. **Rate Limiting**: Thread-safe collection working as expected
4. **Success Rate**: 93% is excellent for automated data collection
5. **Data Quality**: 22,210 price rows and 44,048 indicator rows collected successfully

### What's NOT an Error ⚠️

This is **NOT a system bug**. The failures are due to:
- FinanceDataReader's reliance on Yahoo Finance
- Yahoo Finance's incomplete coverage of KOSDAQ stocks
- External data source limitations (not our code)

---

## Recommendations

### 1. Keep Current Behavior (Recommended) ✅

**Action**: No changes needed

**Rationale**:
- 93% success rate is excellent
- Failed symbols are properly logged
- System is resilient to data source issues
- Symbols remain ACTIVE and can be retried later

**Pros**:
- Simple, maintainable
- Handles temporary data unavailability
- Works well for 93% of stocks
- Future-proof (data may become available)

**Cons**:
- 7% of symbols won't have data

---

### 2. Alternative Data Sources (Future Enhancement)

Consider implementing fallback data sources for failed symbols:

**Option A: Naver Finance**
```python
# Example implementation
if yahoo_fails:
    try_naver_finance(symbol)
```

**Option B: KRX OHLCV API**
- Direct KRX data (most reliable)
- Requires API key registration
- May have rate limits

**Option C: Manual exclusion list**
```yaml
# config/settings.yaml
collection:
  exclude_symbols:
    - 0004V0  # Known to be unavailable
    - 0004Y0
    # ...
```

---

### 3. Monitoring & Alerting (Future Enhancement)

Track data coverage over time:
```sql
-- Query to find symbols with no data
SELECT symbol, name, market
FROM symbol_master
WHERE status = 'ACTIVE'
  AND first_date IS NULL
ORDER BY market, symbol;
```

---

## Action Items

### Immediate (None Required) ✅
- System is working correctly
- No fixes needed
- Continue using as-is

### Short-term (Optional)
- [ ] Document this behavior in README
- [ ] Add exclusion list for known problematic symbols
- [ ] Set up weekly report of uncollected symbols

### Long-term (Future Enhancement)
- [ ] Implement Naver Finance fallback
- [ ] Investigate KRX OHLCV API integration
- [ ] Build alerting for data coverage metrics

---

## Conclusion

**Status**: ✅ **System Operating Normally**

The 7 failed symbols represent a **data source limitation**, not a system error. FinanceDataReader's Yahoo Finance backend does not have data for certain KOSDAQ stocks, particularly those with letter-digit suffixes (V0, Y0, etc.).

**Success metrics**:
- ✅ 93% collection success rate
- ✅ 22,210 price records collected
- ✅ 44,048 indicator values calculated
- ✅ All errors properly logged
- ✅ Symbol validation working correctly

**Recommendation**: Continue using the system as-is. The 93% success rate is excellent for automated bulk collection. Consider alternative data sources only if coverage requirements exceed 95%.

---

## Test Scripts Created

For future reference, the following diagnostic scripts were created:

1. **`scripts/test_failed_symbols.py`**
   - Tests data retrieval for failed symbols
   - Compares with known good symbols
   - Provides detailed failure analysis

2. **`scripts/verify_krx_symbols.py`**
   - Verifies symbols against KRX official listing
   - Analyzes symbol patterns
   - Provides actionable recommendations

Run these scripts anytime to diagnose collection issues:
```bash
python scripts/test_failed_symbols.py
python scripts/verify_krx_symbols.py
```