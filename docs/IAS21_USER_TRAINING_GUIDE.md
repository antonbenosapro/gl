# IAS 21 User Training Guide
**The Effects of Changes in Foreign Exchange Rates - IFRS Compliance**

## Overview
This guide provides comprehensive training on using the IAS 21 compliance features in the GL system for proper foreign currency accounting under IFRS standards.

**Target Audience:** Controllers, Accountants, Financial Analysts  
**Training Time:** 2-3 hours  
**Prerequisites:** Basic understanding of foreign currency accounting

---

## Table of Contents
1. [IAS 21 Fundamentals](#ias-21-fundamentals)
2. [System Navigation](#system-navigation) 
3. [Exchange Difference Classification](#exchange-difference-classification)
4. [Net Investment Hedges](#net-investment-hedges)
5. [Translation Methods](#translation-methods)
6. [Functional Currency Management](#functional-currency-management)
7. [Reporting and Disclosures](#reporting-and-disclosures)
8. [Common Scenarios](#common-scenarios)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## IAS 21 Fundamentals

### What is IAS 21?
IAS 21 "The Effects of Changes in Foreign Exchange Rates" is the IFRS standard governing foreign currency accounting. It addresses:
- **Functional currency determination** 
- **Foreign currency transaction recording**
- **Translation of foreign operations**
- **Exchange difference classification**
- **Required disclosures**

### Key Concepts

#### 1. **Functional Currency (IAS 21.9-14)**
The currency of the primary economic environment where the entity operates.

**Assessment Factors:**
- Currency that mainly influences sales prices
- Currency of country whose competitive forces determine sales prices  
- Currency that mainly influences labor, material, and other costs
- Currency in which funds from financing activities are generated
- Currency in which operating activities receipts are usually retained

#### 2. **Exchange Differences Classification**
- **Transaction Differences (Para 28-29):** Recognized in P&L immediately
- **Translation Differences (Para 39):** Recognized in OCI for net investments
- **Net Investment Differences (Para 32-33):** Recognized in OCI, recycled on disposal

#### 3. **Translation Methods**
- **Current Rate Method:** All assets/liabilities at closing rate, equity at historical rates
- **Temporal Method:** Monetary items at current rates, non-monetary at historical rates

---

## System Navigation

### Accessing IAS 21 Features

#### Main Dashboard
1. **Login** to the GL system
2. Navigate to **"Foreign Currency"** section
3. Select **"IAS 21 Compliance"** from the menu

#### Key Menu Options:
- 📊 **FX Compliance Reports** - Main reporting interface
- 🏛️ **Functional Currency Management** - Entity assessments
- 💱 **Exchange Rate Management** - Rate setup and maintenance
- 🛡️ **Net Investment Hedges** - Hedge relationships
- 📋 **Translation Methods** - Current rate vs temporal analysis

### User Roles and Permissions
- **Controllers:** Full access to all features
- **Accountants:** Read/write access to functional currency assessments
- **Analysts:** Read-only access to reports and disclosures
- **Auditors:** Read-only access to audit trails and documentation

---

## Exchange Difference Classification

### Step-by-Step Process

#### 1. **Identify Transaction Type**
```
Is it a monetary item? 
├─ YES → Is settlement planned in foreseeable future?
│  ├─ YES → Transaction Difference (P&L)
│  └─ NO → Net Investment (OCI)
└─ NO → Is it measured at fair value?
   ├─ YES → Follow fair value accounting location
   └─ NO → Historical cost (no exchange differences)
```

#### 2. **Using the Classification Tool**
1. Navigate to **"Exchange Difference Classification"**
2. Enter transaction details:
   - **Transaction ID**
   - **Monetary/Non-monetary classification**
   - **Settlement terms**
   - **Intercompany status**
3. System automatically classifies per IAS 21
4. Review classification and treatment guidance

#### 3. **Manual Override (if needed)**
- Override available for Controller-level users
- Requires business justification
- Maintains audit trail of changes

### Classification Examples

#### Example 1: Regular Trade Receivable
- **Type:** Monetary item
- **Settlement:** Planned within 90 days
- **Classification:** Transaction Difference → P&L
- **IAS 21 Reference:** Paragraph 28

#### Example 2: Intercompany Loan - No Settlement
- **Type:** Monetary item  
- **Settlement:** Not planned or likely
- **Classification:** Net Investment → OCI
- **IAS 21 Reference:** Paragraph 15, 32

#### Example 3: Inventory at Cost
- **Type:** Non-monetary item
- **Measurement:** Historical cost
- **Classification:** No exchange differences
- **IAS 21 Reference:** Paragraph 23(b)

---

## Net Investment Hedges

### Overview
Net investment hedges protect against FX exposure on investments in foreign operations (subsidiaries, branches, associates).

### Setting Up Net Investment Hedges

#### 1. **Hedge Documentation**
Navigate to **"Net Investment Hedges"** → **"Create New Hedge"**

**Required Information:**
- **Hedge Instrument:** FX forward, option, or swap
- **Hedged Item:** Net investment in foreign operation
- **Hedge Ratio:** Usually 1:1 but can vary
- **Hedge Effectiveness Method:** Dollar offset or regression
- **Inception Date:** Start of hedge relationship

#### 2. **Effectiveness Testing**
- **Frequency:** Quarterly minimum
- **Methods Available:**
  - Dollar offset test
  - Regression analysis
  - Scenario analysis
- **Effectiveness Range:** 80% - 125%

#### 3. **Accounting Treatment**
- **Effective Portion:** Recognized in OCI
- **Ineffective Portion:** Recognized in P&L immediately
- **On Disposal:** OCI amounts recycled to P&L

### Hedge Workflow
```
1. Create Hedge Documentation
2. Set Up Effectiveness Testing Schedule
3. Record Hedge Instrument Fair Value Changes
4. Perform Effectiveness Tests
5. Record Effective/Ineffective Portions
6. Monitor Hedge Performance
7. On Disposal → Recycle OCI to P&L
```

---

## Translation Methods

### Current Rate Method (IAS 21.39)
**When to Use:** Entity's functional currency ≠ presentation currency

**Translation Rules:**
- **Assets & Liabilities:** Current exchange rate at period end
- **Equity:** Historical exchange rates
- **Income & Expenses:** Exchange rates at transaction dates (or average)
- **Exchange Differences:** Recognized in OCI

### Temporal Method  
**When to Use:** Remeasurement (rare under IAS 21)

**Translation Rules:**
- **Monetary Items:** Current exchange rate
- **Non-monetary Items:** Historical exchange rates
- **Exchange Differences:** Recognized in P&L

### Using the Translation Tool

#### 1. **Access Translation Analysis**
Navigate to **"Translation Methods"** → **"Method Comparison"**

#### 2. **Input Parameters**
- **Entity:** Select entity for analysis
- **Functional Currency:** Entity's functional currency
- **Presentation Currency:** Reporting currency
- **Translation Date:** Period end date

#### 3. **Review Results**
System shows side-by-side comparison:
- **Current Rate Method Impact**
- **Temporal Method Impact**  
- **Recommendation:** Based on IAS 21 requirements

#### 4. **Generate Documentation**
- Export analysis to PDF
- Include in audit documentation
- Support for method selection

---

## Functional Currency Management

### Functional Currency Assessment

#### 1. **Initial Assessment**
Navigate to **"Functional Currency Management"** → **"New Assessment"**

**Assessment Criteria:**
- **Primary Economic Environment**
- **Cash Flow Indicators**
- **Sales Price Indicators**  
- **Cost Structure Indicators**
- **Financing Indicators**

#### 2. **Scoring System**
System automatically scores each factor:
- **High Confidence:** Score ≥ 8/10
- **Medium Confidence:** Score 5-7/10
- **Low Confidence:** Score < 5/10

#### 3. **Review and Approval**
- Controller review required for all assessments
- Document business rationale
- Set review frequency (typically annual)

### Functional Currency Changes

#### 1. **When Changes Are Permitted**
Only when there's a change in underlying transactions, events, and conditions.

#### 2. **Processing Changes (IAS 21.35-37)**
1. Navigate to **"Functional Currency Changes"**
2. Enter change details and justification
3. System applies prospective treatment:
   - Translates all items at change date rate
   - Translated amounts become new historical cost
   - No restatement of comparatives

#### 3. **Required Documentation**
- Business justification for change
- Impact analysis
- Board/management approval evidence

---

## Reporting and Disclosures

### IAS 21 Required Disclosures (Para 51-57)

#### 1. **Accessing Reports**
Navigate to **"FX Compliance Reports"** → **"IAS 21 Disclosures"**

#### 2. **Available Reports**

##### **Exchange Differences in P&L (Para 52a)**
- FX gains recognized in profit or loss
- FX losses recognized in profit or loss
- Net impact by period

##### **Exchange Differences in OCI (Para 52b)**
- Opening OCI balance
- Period movements
- Closing OCI balance
- Component breakdown (assets, liabilities, hedges)

##### **Functional Currency Disclosure (Para 53)**
- Current functional currency
- Changes during the period
- Reasons for any changes

##### **Presentation Currency (Para 54)**
- Presentation currency used
- Reason if different from functional currency
- Translation method applied

#### 3. **Report Customization**
- **Period Selection:** Monthly, quarterly, annual
- **Entity Selection:** Individual or consolidated
- **Format Options:** PDF, Excel, dashboard view
- **Comparison Views:** Period-over-period, budget vs actual

### CTA Reconciliation Report

#### 1. **Accessing CTA Reports**
Navigate to **"FX Compliance Reports"** → **"CTA Reconciliation"**

#### 2. **CTA Waterfall Analysis**
Visual representation showing:
- Opening CTA balance
- Asset translation adjustments
- Liability translation adjustments
- Net investment hedge adjustments
- Closing CTA balance

#### 3. **Drill-Down Capability**
- Click any component for detailed breakdown
- Account-level detail available
- Export to Excel for further analysis

---

## Common Scenarios

### Scenario 1: European Subsidiary
**Background:** US parent company with European subsidiary

**Steps:**
1. **Assess Functional Currency**
   - Primary operations in Europe
   - Sales/costs/financing in EUR
   - **Result:** EUR functional currency

2. **Translation to USD (Presentation)**
   - Use current rate method
   - Assets/liabilities at period-end rate
   - Equity at historical rates
   - Translation differences → OCI

3. **Reporting**
   - Generate IAS 21 disclosures
   - Include CTA reconciliation
   - Document translation method

### Scenario 2: Net Investment Hedge
**Background:** Hedge FX exposure on EUR subsidiary investment

**Steps:**
1. **Set Up Hedge**
   - Hedge instrument: EUR/USD forward
   - Hedged item: Net investment in EUR subsidiary
   - Document hedge relationship

2. **Effectiveness Testing**
   - Quarterly dollar offset test
   - Effective portion → OCI
   - Ineffective portion → P&L

3. **On Disposal/Liquidation**
   - Recycle hedge reserve from OCI → P&L
   - Recycle CTA from OCI → P&L

### Scenario 3: Intercompany Loans
**Background:** Long-term intercompany loan with no settlement plan

**Steps:**
1. **Classification Assessment**
   - Monetary item: Yes
   - Settlement planned: No
   - **Result:** Part of net investment

2. **Accounting Treatment**
   - Exchange differences → OCI
   - Include in CTA reconciliation
   - No P&L impact unless settled

3. **Documentation**
   - Support no-settlement conclusion
   - Review annually for changes

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Exchange Rate Not Found"
**Symptoms:** Error when processing FX transactions
**Solution:**
1. Check exchange rate setup in **"Exchange Rate Management"**
2. Verify rate date matches transaction date
3. Add missing rates manually if needed
4. Set up automatic rate feeds for future

#### Issue 2: "Classification Unclear"
**Symptoms:** System cannot auto-classify exchange difference
**Solution:**
1. Review transaction characteristics
2. Check intercompany status
3. Verify settlement terms
4. Use manual classification with justification

#### Issue 3: "CTA Balance Mismatch"
**Symptoms:** CTA reconciliation doesn't balance
**Solution:**
1. Run **"CTA Reconciliation Report"**
2. Check for unprocessed translation adjustments
3. Verify opening balances
4. Review period-end procedures

#### Issue 4: "Hedge Effectiveness Failed"
**Symptoms:** Hedge effectiveness test outside 80-125% range
**Solution:**
1. Review hedge ratio
2. Check calculation methodology
3. Consider hedge rebalancing
4. Document ineffectiveness in P&L

### Getting Help
- **System Help:** Click (?) icons for context-sensitive help
- **Training Materials:** Available in **"Help"** → **"Training Resources"**
- **Support Team:** Contact finance systems team for technical issues
- **Accounting Team:** Contact senior accountants for accounting questions

---

## Best Practices

### Month-End Procedures

#### 1. **Week Before Period End**
- [ ] Review open FX positions
- [ ] Update exchange rates
- [ ] Prepare hedge effectiveness tests
- [ ] Review functional currency assessments

#### 2. **Period End Day**
- [ ] Capture closing exchange rates
- [ ] Run FX revaluation process
- [ ] Process hedge accounting entries
- [ ] Generate preliminary CTA analysis

#### 3. **First Week of New Period**
- [ ] Complete hedge effectiveness testing
- [ ] Finalize FX revaluation entries
- [ ] Generate IAS 21 disclosure reports
- [ ] Review and approve all FX entries

### Quality Controls

#### 1. **Four-Eyes Principle**
- All FX entries require approval
- Functional currency assessments need controller sign-off
- Exchange rate changes need dual approval

#### 2. **Reconciliation Controls**
- Monthly CTA reconciliation
- Hedge reserve roll-forward
- Exchange rate variance analysis
- OCI component analysis

#### 3. **Documentation Requirements**
- Maintain hedge documentation files
- Keep functional currency assessment support
- Document significant exchange rate movements
- Retain effectiveness test calculations

### System Maintenance

#### 1. **Regular Tasks**
- **Daily:** Exchange rate updates
- **Weekly:** FX position monitoring  
- **Monthly:** Hedge effectiveness testing
- **Quarterly:** Functional currency review
- **Annually:** Full IAS 21 compliance review

#### 2. **Year-End Procedures**
- Complete annual effectiveness testing
- Generate full year IAS 21 disclosures
- Update functional currency assessments
- Review hedge documentation completeness

---

## Appendices

### Appendix A: IAS 21 Paragraph Reference Quick Guide
- **Para 9-14:** Functional currency determination
- **Para 15:** Net investment definition
- **Para 23:** Non-monetary items
- **Para 28-29:** Transaction differences
- **Para 32-33:** Net investment differences
- **Para 35-37:** Functional currency changes
- **Para 39:** Translation method
- **Para 48-49:** Disposal of foreign operations
- **Para 51-57:** Disclosure requirements

### Appendix B: Exchange Rate Sources
- **Bloomberg:** Real-time professional rates
- **Reuters:** Market rates with audit trail
- **Central Banks:** Official rates for regulatory compliance
- **Fed Reserve:** USD-based official rates

### Appendix C: System Keyboard Shortcuts
- **Ctrl+F:** Find/search within reports
- **Ctrl+E:** Export current view
- **Ctrl+P:** Print current report
- **F1:** Context-sensitive help
- **Alt+H:** Access help menu

### Appendix D: Training Checklist
- [ ] Complete IAS 21 fundamentals review
- [ ] Practice exchange difference classification
- [ ] Set up sample net investment hedge
- [ ] Run translation method comparison  
- [ ] Generate sample IAS 21 disclosures
- [ ] Complete month-end simulation
- [ ] Pass system competency assessment

---

## Training Completion Certificate

**User:** _________________ **Date:** _________________

**Training Completed:** IAS 21 Compliance System Training

**Competency Areas Assessed:**
- [ ] IAS 21 fundamentals understanding
- [ ] System navigation proficiency
- [ ] Exchange difference classification
- [ ] Net investment hedge management
- [ ] Translation method application
- [ ] Reporting and disclosure generation

**Supervisor Approval:** _________________ **Date:** _________________

**Next Review Date:** _________________

---

*This training guide is current as of August 2025. For questions or updates, contact the Finance Systems Team.*