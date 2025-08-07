# 🧪 Field Status Group Validation Test Journals

**Purpose:** Functional testing of FSG validation controls across all 3 hierarchy levels  
**Date:** August 7, 2025  
**Status:** Ready for Testing

---

## 📋 Test Overview

These test journals validate the **3-level FSG hierarchy**:
1. **Level 1:** Document Type Override (Highest Priority)
2. **Level 2:** GL Account Specific (Medium Priority)  
3. **Level 3:** Account Group Default (Lowest Priority)

Each test includes scenarios for **REQ** (Required), **OPT** (Optional), and **SUP** (Suppressed) field controls.

---

## ❌ Test Journal 1: VALIDATION FAILURES

**File:** `test_journal_validation_failures.csv`

### Expected Results: 
- **Total Entries:** 3 journal entries with 6+ FSG validation errors
- **Purpose:** Verify all FSG validation rules are enforced across hierarchy levels

```csv
document_number,company_code,line_number,gl_account,debit_amount,credit_amount,posting_date,description,business_unit_id,tax_code,business_area,reference,assignment,text,document_type
FSG-FAIL-001,1000,1,400001,1000.00,0.00,2025-08-07,Test Revenue Entry - Missing Required Fields,,,,,,,SA
FSG-FAIL-001,1000,2,100010,0.00,1000.00,2025-08-07,Cash Entry - Providing Suppressed Fields,123,V1,US,REF001,ASSIGN001,TEXT001,SA
FSG-FAIL-002,1000,1,110000,1500.00,0.00,2025-08-07,AR Entry - Missing Required Fields,,,,,,,DR
FSG-FAIL-002,1000,2,400001,0.00,1500.00,2025-08-07,Revenue Entry - Missing Tax Code,,,,,,,DR
FSG-FAIL-003,1000,1,100010,500.00,0.00,2025-08-07,Cash Receipt - Providing Suppressed Business Unit,456,,REF002,,,CA
FSG-FAIL-003,1000,2,500001,0.00,500.00,2025-08-07,Expense Entry - Missing Required Fields,789,V2,NORTH,REF003,ASSIGN003,TEXT003,
```

### Expected Validation Errors:

1. **Line 1 (SA + 400001):** 
   - FSG: ASSET01 (from Document Type SA)
   - Error: None expected (ASSET01 allows missing business_unit and suppresses tax_code)

2. **Line 2 (SA + 100010):**
   - FSG: ASSET01 (from Document Type SA)  
   - Error: Tax Code should not be provided (FSG: SUP - Suppressed)
   - Error: Business Unit provided but suppressed

3. **Line 3 (DR + 110000):**
   - FSG: RECV01 (from Document Type DR)
   - Error: Business Unit is required (FSG: REQ)

4. **Line 4 (DR + 400001):**
   - FSG: RECV01 (from Document Type DR)
   - Error: Business Unit is required (FSG: REQ)
   - Error: Tax Code should not be provided (FSG: SUP - suppressed in RECV01)

5. **Line 5 (CA + 100010):**
   - FSG: CASH01 (from Document Type CA)
   - Error: Business Unit should not be provided (FSG: SUP - Suppressed)

6. **Line 6 (No Doc + 300010):**
   - FSG: EXP01 (from Account Group - OPEX accounts)
   - Error: Business Unit is required (FSG: REQ)
   - Error: Business Area is required (FSG: REQ)

---

## ✅ Test Journal 2: VALIDATION SUCCESS

**File:** `test_journal_validation_success.csv`

### Expected Results:
- **All Validations Pass:** 4 journal entries with no FSG errors
- **Purpose:** Verify correct field combinations work across all hierarchy levels

```csv
document_number,company_code,line_number,gl_account,debit_amount,credit_amount,posting_date,description,business_unit_id,tax_code,business_area,reference,assignment,text,document_type
FSG-PASS-001,1000,1,400001,1000.00,0.00,2025-08-07,General Journal - ASSET01 FSG allows optional fields,,,REF001,ASSIGN001,TEXT001,SA
FSG-PASS-001,1000,2,120000,0.00,1000.00,2025-08-07,Asset Entry - ASSET01 FSG minimal requirements,,,REF002,ASSIGN002,TEXT002,SA
FSG-PASS-002,1000,1,110000,1500.00,0.00,2025-08-07,Customer Invoice AR - RECV01 requires Business Unit,100,,US,REF003,ASSIGN003,TEXT003,DR
FSG-PASS-002,1000,2,400001,0.00,1500.00,2025-08-07,Customer Invoice Revenue - RECV01 compliant,100,,US,REF004,ASSIGN004,TEXT004,DR
FSG-PASS-003,1000,1,100010,500.00,0.00,2025-08-07,Cash Receipt - CASH01 suppresses most fields,,,,REF005,ASSIGN005,TEXT005,CA
FSG-PASS-003,1000,2,110000,0.00,500.00,2025-08-07,Cash Journal AR - CASH01 override allows Business Unit,200,,US,REF006,ASSIGN006,TEXT006,CA
FSG-PASS-004,1000,1,400001,800.00,0.00,2025-08-07,Revenue Entry - REV01 all required fields provided,150,V1,NORTH,REF007,ASSIGN007,TEXT007,
FSG-PASS-004,1000,2,500001,0.00,800.00,2025-08-07,Expense Entry - EXP01 all required fields provided,200,,SOUTH,REF008,ASSIGN008,TEXT008,
```

### Expected Validation Success:

1. **Line 1 (SA + 400001):** ✅ ASSET01 - Business Unit optional, Tax Code suppressed
2. **Line 2 (SA + 120000):** ✅ ASSET01 - Minimal field requirements met  
3. **Line 3 (DR + 110000):** ✅ RECV01 - Business Unit provided, no tax code required
4. **Line 4 (DR + 400001):** ✅ RECV01 - Business Unit provided, Business Area provided
5. **Line 5 (CA + 100010):** ✅ CASH01 - No restricted fields provided
6. **Line 6 (CA + 110000):** ✅ CASH01 - Document type overrides account requirements
7. **Line 7 (No Doc + 400001):** ✅ REV01 - All required fields (Business Unit, Tax Code, Business Area)
8. **Line 8 (No Doc + 500001):** ✅ EXP01 - All required fields (Business Unit, Business Area)

---

## 🔧 Test Execution Steps

### Step 1: Upload Failure Test
1. Navigate to **Journal Entry Upload** page
2. Upload `test_journal_validation_failures.csv`
3. **Expected:** System should reject with 6+ validation errors
4. Verify error messages mention specific FSG rules (REQ/SUP)

### Step 2: Upload Success Test  
1. Upload `test_journal_validation_success.csv`
2. **Expected:** All 8 lines should validate successfully
3. Journal should be accepted for posting

### Step 3: Verify FSG Information Panel
1. Check that FSG information is displayed for each account
2. Verify hierarchy levels are shown correctly:
   - Document Type FSG (when applicable)
   - Account FSG (when no document override)
   - Account Group FSG (fallback)

---

## 📊 FSG Configuration Reference

### Current Active FSGs:
| FSG ID | Business Unit | Tax Code | Business Area | Usage |
|--------|---------------|----------|---------------|-------|
| ASSET01 | OPT | SUP | SUP | General postings |
| CASH01 | SUP | SUP | SUP | Cash transactions |
| REV01 | REQ | REQ | REQ | Revenue accounts |
| EXP01 | REQ | SUP | REQ | Expense accounts |
| RECV01 | REQ | SUP | OPT | Receivables |
| COGS01 | REQ | SUP | REQ | Cost of goods sold |

### Document Type Assignments:
- **SA** (General Journal) → ASSET01
- **CA** (Cash Journal) → CASH01  
- **DR** (Customer Invoice) → RECV01
- **KR** (Vendor Invoice) → PAYB01

### Account Assignments:
- **400001** (Revenue) → REV01 (via SALE account group)
- **100010** (Cash) → CASH01 (via CASH account group)
- **110000** (AR) → RECV01 (via RECV account group)
- **500001** (Expenses) → EXP01 (via OPEX account group)

---

## 🎯 Success Criteria

### Failure Test Should Show:
- ❌ **6+ validation errors** with specific FSG rule violations
- ❌ Clear error messages citing **FSG hierarchy levels**
- ❌ **Line-specific errors** with field names and requirements

### Success Test Should Show:
- ✅ **All 8 lines validate** without errors
- ✅ **FSG information panel** displays correct FSG for each account
- ✅ **Journal accepted** for posting

---

## 🐛 Troubleshooting

### If Tests Don't Work as Expected:

1. **Check FSG Cache:**
   ```python
   from utils.field_status_validation import field_status_engine
   field_status_engine.clear_cache()
   ```

2. **Verify Account Setup:**
   - Ensure accounts have proper account group assignments
   - Check account groups have default_field_status_group set

3. **Check Document Types:**
   - Verify document types have field_status_group assignments

4. **Review Error Messages:**
   - Should include FSG ID and specific rule (REQ/SUP/OPT)
   - Should include line numbers for batch uploads

---

## 📁 Test Files Created

**Location:** `/home/anton/erp/gl/docs/test_files/`

1. **test_journal_validation_failures.csv** - Triggers validation errors
2. **test_journal_validation_success.csv** - Passes all validations

These files are ready for functional testing of the complete FSG validation system across all 3 hierarchy levels.