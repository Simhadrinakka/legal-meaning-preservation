# Dataset Inspection and Analysis Report: MILPaC Acts Dataset

**Project Title:** Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT  
**Dataset Inspected:** `data/raw/MILPaC_Acts_dataset.xlsx`  
**Execution Script:** `training/analyze_dataset.py`  
**Generated Statistics Artifact:** `reports/dataset_statistics.json`  
**Date of Analysis:** November 2026  

---

## 1. Executive Summary

As part of Task 1 for the college NLP project *"Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT"*, this report documents the structural, statistical, and linguistic inspection of the **MILPaC (Multilingual Indian Legal Parallel Corpus) Acts Dataset**.

The dataset was loaded and inspected using Python 3.13 and `pandas` via an automated analysis script ([analyze_dataset.py](file:///c:/Projects/Legal-Meaning-Preservation/training/analyze_dataset.py)). The raw corpus contains **4,036 aligned bilingual legal passage records** across **9 constitutionally recognized Indian languages**, with English (`EN`) serving as the universal source language. 

A total of **706 English-Hindi (`EN` $\rightarrow$ `HI`) aligned pairs** were isolated, spanning **5 major Indian Central Acts**. The dataset represents authoritative legal translations rather than text simplifications, making it an ideal benchmark for evaluating cross-lingual legal meaning preservation (LMP).

---

## 2. Dataset Dimensions and Schema Inspection

### 2.1 File Characteristics
- **File Name:** `MILPaC_Acts_dataset.xlsx`
- **Location:** `data/raw/`
- **Worksheet Name:** `Sheet1`
- **Integrity Status:** Read-only inspection; original Excel file remained unaltered.

### 2.2 Structural Overview
| Metric | Value |
| :--- | :--- |
| **Total Rows** | 4,036 |
| **Total Columns** | 6 |
| **Missing / Null Values** | 0 across all columns (100% complete) |
| **Exact Duplicate Rows** | 0 |
| **Total Unique Passage IDs (`id`)** | 1,740 |

### 2.3 Column Schema & Data Types
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `dataset` | `object` (string) | Dataset origin identifier (`Acts` for all records) |
| `id` | `object` (string) | Hierarchical statutory identifier (`Year_ActNo_Section_Clause`) |
| `src_lang` | `object` (string) | Source language code (`EN` across all 4,036 rows) |
| `src` | `object` (string) | Verbatim source statutory passage in English |
| `tgt_lang` | `object` (string) | Target Indian language ISO/standard code |
| `tgt` | `object` (string) | Authorized target statutory passage in the target language |

---

## 3. Language Distribution Across Corpus

The source language is exclusively **English (`EN`)** for 100% of the entries ($N = 4,036$). The target text spans 9 major Indian languages as detailed below:

| Target Language | Language Code | Aligned Records | Corpus Share (%) | Unique IDs Covered |
| :--- | :--- | :--- | :--- | :--- |
| Bengali | `BN` | 739 | 18.31% | 739 |
| **Hindi** | **`HI`** | **706** | **17.49%** | **706** |
| Marathi | `MR` | 578 | 14.32% | 578 |
| Malayalam | `ML` | 443 | 10.98% | 443 |
| Tamil | `TA` | 418 | 10.36% | 418 |
| Telugu | `TE` | 319 | 7.90% | 319 |
| Gujarati | `GU` | 316 | 7.83% | 316 |
| Punjabi | `PA` | 261 | 6.47% | 261 |
| Odia | `OR` | 256 | 6.34% | 256 |
| **Total** | — | **4,036** | **100.00%** | **1,740** (multi-way aligned) |

> [!NOTE]
> Every target language has a strict 1:1 mapping between each row and its unique passage ID (e.g., exactly 706 unique IDs for 706 Hindi rows).

---

## 4. English-Hindi (`EN` $\rightarrow$ `HI`) In-Depth Analysis

For our project focus on English-Hindi legal meaning preservation, the 706 aligned pairs were extracted and subjected to deeper profiling.

### 4.1 Acts Breakdown
The passage IDs encode the enactment year and the Act number (`YYYY_ActNo_Section_Clause`). The English-Hindi subset comprises provisions extracted from 5 key Central Acts:

| Act Identifier | Official Act Title | Hindi Record Count | Percentage |
| :--- | :--- | :--- | :--- |
| `2006_4` | The Commissions for Protection of Child Rights Act, 2005 (Act No. 4 of 2006) | 175 | 24.79% |
| `2007_56` | The Maintenance and Welfare of Parents and Senior Citizens Act, 2007 (Act No. 56 of 2007) | 144 | 20.40% |
| `1969_18` | The Registration of Births and Deaths Act, 1969 (Act No. 18 of 1969) | 135 | 19.12% |
| `1976_19` | The Bonded Labour System (Abolition) Act, 1976 (Act No. 19 of 1976) | 127 | 17.99% |
| `2008_34` | The National Investigation Agency Act, 2008 (Act No. 34 of 2008) | 125 | 17.71% |
| **Total** | — | **706** | **100.00%** |

### 4.2 Text Uniqueness and Boilerplate Repetitions
- **Unique Source Texts (`src`):** 689 (out of 706)
- **Unique Target Texts (`tgt`):** 698 (out of 706)
- **Explanation:** In legislative drafting across Commonwealth jurisdictions, standard clauses recur verbatim across separate Acts (e.g., *"1. Short title, extent and commencement"*, *"(2) It extends to the whole of India"*, *"In this Act, unless the context otherwise requires"*, and delegated rulemaking clauses *"In particular and without prejudice to the generality of the foregoing power"*). These 17 repeated source instances represent authentic statutory repetition, not data duplication.

### 4.3 Word and Token Length Statistics
| Metric | English Source (`src`) | Hindi Target (`tgt`) |
| :--- | :--- | :--- |
| **Minimum Words** | 2 | 2 |
| **Maximum Words** | 178 | 197 |
| **Mean Word Count** | 29.90 | 31.07 |
| **Median Word Count** | 23.00 | 24.00 |
| **Standard Deviation** | 25.25 | 26.17 |

### 4.4 Passage Length Granularity
- **Short Passages (< 10 words):** 150 passages (21.25%)  
  *Predominantly section headings, sub-clause titles, and simple enacting formulas (e.g., "2. Definitions", "(i) education;").*
- **Medium Passages (10 – 50 words):** 443 passages (62.75%)  
  *Core substantive statutory clauses containing active legal obligations, definitions, and procedures.*
- **Long Passages (> 50 words):** 113 passages (16.01%)  
  *Complex multi-condition provisions, provisos, non-obstante clauses, and comprehensive powers.*

---

## 5. 10 Representative English-Hindi Legal Passage Examples

The following 10 pairs were systematically sampled across all 5 Acts to illustrate varying legislative constructions, modalities, and legal complexities:

### Example 1: Short Title & Nomenclature
- **ID:** `2006_4_1_1` | **Act:** Commissions for Protection of Child Rights Act, 2005
- **Category:** Statutory Naming Clause
- **English (15 words):** `(1) This Act may be called the Commissions for Protection of Child Rights Act, 2005.`
- **Hindi (13 words):** `(1) इस अधिनियम का संक्षिप्त नाम बालक अधिकार संरक्षण आयोग अधिनियम, 2005 है।`
- **LMP Significance:** Baseline naming fidelity; validates legal entity translation (`Commissions for Protection of Child Rights` $\leftrightarrow$ `बालक अधिकार संरक्षण आयोग`).

### Example 2: Executive Commencement Discretion
- **ID:** `2006_4_1_3` | **Act:** Commissions for Protection of Child Rights Act, 2005
- **Category:** Commencement & Delegated Power
- **English (21 words):** `(3) It shall come into force on such date1 as the Central Government may, by notification in the Official Gazette, appoint.`
- **Hindi (17 words):** `(3) यह उस तारीख को प्रवृत्त होगा जो केन्द्रीय सरकार, राजपत्र में अधिसूचना द्वारा, नियत करे ।`
- **LMP Significance:** Evaluates mandatory temporal enforcement (`shall come into force` $\leftrightarrow$ `प्रवृत्त होगा`) and administrative discretion (`may... appoint` $\leftrightarrow$ `नियत करे`).

### Example 3: Statutory Legal Definition
- **ID:** `2006_4_2_2` | **Act:** Commissions for Protection of Child Rights Act, 2005
- **Category:** Definitional Scope
- **English (18 words):** `(a) "Chairperson" means the Chairperson of the Commission or of the State Commission, as the case may be;`
- **Hindi (13 words):** `(क) "अध्यक्ष" से, यथास्थिति, आयोग या राज्य आयोग का अध्यक्ष अभिप्रेत है ;`
- **LMP Significance:** Formal definitional terminology (`means` $\leftrightarrow$ `अभिप्रेत है`, `as the case may be` $\leftrightarrow$ `यथास्थिति`).

### Example 4: Complex Non-Obstante & Disqualification Clause
- **ID:** `2006_4_7_2` | **Act:** Commissions for Protection of Child Rights Act, 2005
- **Category:** Non-Obstante Overriding Clause & Penal Disqualification
- **English (140 words):** `(2) Notwithstanding anything contained in sub-section (1), the Central Government may by order remove from office the Chairperson or any other Member, if the Chairperson or, as the case may be, such other Member,— (a) is adjudged an insolvent; or (b) engages during his term of office in any paid employment outside the duties of his office;or (c) refuses to act or becomes incapable of acting; or (d) is of unsound mind and stands so declared by a competent court; or (e) has so abused his office as to render his continuance in office detrimental to the public interest; or (f) is convicted and sentenced to imprisonment for an offence which in the opinion of the Central Government involves moral turpitude; or (g) is, without obtaining leave of absence from the Commission, absent from three consecutive meetings of the Commission.`
- **Hindi (143 words):** `(2) उपधारा (1) में किसी बात के होते हुए भी, केन्द्रीय सरकार, आदेश द्वारा अध्यक्ष या किसी अन्य सदस्य को पद से हटा सकेगी यदि, यथास्थिति, अध्यक्ष या ऐसा अन्य सदस्य- (क) दिवालिया न्यायनिर्णीत किया जाता है ; या (ख) अपनी पदावधि के दौरान अपने पद के कर्तव्यों के बाहर किसी सवेतन नियोजन में लगता है ; या (ग) कार्य करने से इंकार करता है या कार्य करने में असमर्थ हो जाता है ; या (घ) विकृतचित्त का है और किसी सक्षम न्यायालय द्वारा ऐसा घोषित किया गया है ; या (ङ) अपने पद का ऐसा दुरुपयोग करता है जिससे उसका पद पर बने रहना लोकहित के लिए हानिकारक हो जाता है; या (च) किसी ऐसे अपराध के लिए सिद्धदोष ठहराया जाता है और कारावास से दंडादिष्ट किया जाता है, जिसमें केंद्रीय सरकार की राय में, नैतिक अधमता अन्तर्वलित है ; या (छ) आयोग से अनुपस्थित रहने की अनुमति लिए बिना उसकी तीन क्रमवर्ती बैठकों में अनुपस्थित रहता है।`
- **LMP Significance:** High syntactic complexity, multiple sub-conditions, and critical legal concepts: `moral turpitude` $\leftrightarrow$ `नैतिक अधमता`, `unsound mind` $\leftrightarrow$ `विकृतचित्त`, `adjudged an insolvent` $\leftrightarrow$ `दिवालिया न्यायनिर्णीत`.

### Example 5: Statutory Abolition of Bonded Labour
- **ID:** `1976_19_4_1` | **Act:** Bonded Labour System (Abolition) Act, 1976
- **Category:** Substantive Rights & Discharge of Liability
- **English (31 words):** `(1) On the commencement of this Act, the bonded labour system shall stand abolished and every bonded labourer shall, on such commencement, stand freed and discharged from any obligation to render any bonded labour.`
- **Hindi (33 words):** `(1) इस अधिनियम के प्रारम्भ पर बन्धित श्रम पद्धति का उत्सादन हो जाएगा और ऐसे प्रारम्भ पर प्रत्येक बन्धित श्रमिक, बन्धित श्रम करने की किसी बाध्यता से मुक्त और उन्मोचित हो जाएगा ।`
- **LMP Significance:** Deontic force (`shall stand abolished` $\leftrightarrow$ `उत्सादन हो जाएगा`, `freed and discharged` $\leftrightarrow$ `मुक्त और उन्मोचित`).

### Example 6: Penal Sanction and Incarceration
- **ID:** `1976_19_16_1` | **Act:** Bonded Labour System (Abolition) Act, 1976
- **Category:** Penal Provision / Criminal Sanction
- **English (35 words):** `Whoever, after the commencement of this Act, compels any person to render any bonded labour shall be punishable with imprisonment for a term which may extend to three years and also with fine which may extend to two thousand rupees.`
- **Hindi (37 words):** `जो कोई इस अधिनियम के प्रारम्भ के पश्चात्‌ किसी व्यक्ति को कोई बन्धित श्रम करने के लिए विवश करेगा वह कारावास से, जिसकी अवधि तीन वर्ष तक की हो सकेगी, और जुर्माने से भी, जो दो हजार रुपए तक का हो सकेगा, दण्डनीय होगा ।`
- **LMP Significance:** Exact punishment bounds (`shall be punishable with imprisonment... may extend to three years and also with fine`).

### Example 7: Evidentiary Presumption & Reverse Onus
- **ID:** `1976_19_15_1` | **Act:** Bonded Labour System (Abolition) Act, 1976
- **Category:** Legal Burden of Proof
- **English (31 words):** `Whenever any debt is claimed by a bonded labourer, or a Vigilance Committee, to be a bonded debt, the burden of proof that such debt is not a bonded debt shall lie on the creditor.`
- **Hindi (32 words):** `जब कभी किसी बन्धित श्रमिक या सतर्कता समिति द्वारा किसी ऋण के बारे में यह दावा किया जाता है कि वह बन्धित ऋण है तो ऐसे ऋण के बन्धित ऋण न होने के सबूत का भार लेनदार पर होगा ।`
- **LMP Significance:** Evidentiary rules (`burden of proof... shall lie on the creditor` $\leftrightarrow$ `सबूत का भार लेनदार पर होगा`).

### Example 8: Substantive Maintenance Entitlement
- **ID:** `2007_56_4_1` | **Act:** Maintenance and Welfare of Parents and Senior Citizens Act, 2007
- **Category:** Statutory Rights & Locus Standi
- **English (70 words):** `(1) A senior citizen including parent who is unable to maintain himself from his own earning or out of the property owned by him, shall be entitled to make an application under section 5 in case of— (i) parent or grand-parent, against one or more of his children not being a minor; (ii) a childless senior citizen, against such of his relative referred to in clause (g) of section 2.`
- **Hindi (78 words):** `(1) कोई वरिष्ठ नागरिक, जिसके अन्तर्गत माता-पिता हैं, जो स्वयं के अर्जन से या उसके स्वामित्वाधीन संपत्ति में से स्वयं का भरणपोषण करने में असमर्थ है,-- (i) माता-पिता या पितामह-पितामही की दशा में, अपने एक या अधिक बालकों के विरुद्ध, जो अवयस्क नहीं हैं ; (॥) किसी निःसन्‍्तान वरिष्ठ नागरिक की दशा में, अपने ऐसे नातेदार के विरुद्ध, जो धारा 2 के खंड (छ) में निर्दिष्ट है, धारा 5 के अधीन कोई आवेदन करने का हकदार होगा ।`
- **LMP Significance:** Eligibility predicates and procedural entitlements (`shall be entitled to make an application` $\leftrightarrow$ `आवेदन करने का हकदार होगा`).

### Example 9: Specific Criminal Offence (Abandonment)
- **ID:** `2007_56_24_1` | **Act:** Maintenance and Welfare of Parents and Senior Citizens Act, 2007
- **Category:** Offence with Mens Rea (Intent)
- **English (54 words):** `Whoever, having the care or protection of senior citizen leaves, such senior citizen in any place with the intention of wholly abandoning such senior citizen, shall be punishable with imprisonment of either description for a term which may extend to three months or fine which may extend to five thousands rupees or with both.`
- **Hindi (60 words):** `जो कोई, जिसके पास वरिष्ठ नागरिक की देखरेख या सुरक्षा है, ऐसे वरिष्ठ नागरिक को, किसी स्थान में, ऐसे वरिष्ठ नागरिक का पूर्णतया परित्याग करने के आशय से छोड़ेगा, वह ऐसी अवधि के किसी कारावास से, जो तीन मास तक की हो सकेगी या जुर्माने से, जो पांच हजार रुपए तक का हो सकेगा, या दोनों से, दंडनीय होगा ।`
- **LMP Significance:** Mental state requirement (`with the intention of wholly abandoning` $\leftrightarrow$ `पूर्णतया परित्याग करने के आशय से`).

### Example 10: Mandatory Statutory Duty on Public / Citizens
- **ID:** `1969_18_8_1` | **Act:** Registration of Births and Deaths Act, 1969
- **Category:** Affirmative Legal Duty
- **English (65 words):** `(1) It shall be the duty of the persons specified below to give or cause to be given, either orally or in writing, according to the best of their knowledge and belief, within such time as may be prescribed, information to the Registrar of the several particulars required to be entered in the forms prescribed by the State Government under sub-section (1) of section 16,—`
- **Hindi (58 words):** `(1) नीचे विनिर्दिष्ट व्यक्तियों का यह कर्तव्य होगा कि वे धारा 6 की उपधारा (1) के अधीन राज्य सरकार द्वारा विहित प्ररूपों में प्रविष्ट किए जाने के लिए अपेक्षित विभिन्‍न विशिष्टियों की इत्तिला अपने सर्वोत्तम ज्ञान और विश्वास के अनुसार, ऐसे समय के भीतर, जो विहित किया जाए, मौखिक या लिखित रूप में रजिस्ट्रार को दें या दिलवाएं,--`
- **LMP Significance:** Affirmative statutory duty (`It shall be the duty... to give or cause to be given` $\leftrightarrow$ `कर्तव्य होगा कि वे... मौखिक या लिखित रूप में रजिस्ट्रार को दें या दिलवाएं`).

---

## 6. Critical Conceptual Distinction: Legal Translation vs. Text Simplification

A fundamental requirement of this analysis is articulating why the MILPaC dataset comprises **authorized legal translations** rather than original-simplified legal pairs, and why conflating the two is invalid in legal NLP.

```
       ┌────────────────────────────────────────────────────────┐
       │             STATUTORY PARALLEL CORPUS                  │
       │           (English Enactment <-> Hindi Act)            │
       └───────────────────────────┬────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
         ▼                                                   ▼
┌───────────────────────────────────┐       ┌──────────────────────────────────┐
│   AUTHORIZED LEGAL TRANSLATION    │       │     LEGAL TEXT SIMPLIFICATION    │
│       (Current Project Task)      │       │      (NOT Present in Dataset)    │
├───────────────────────────────────┤       ├──────────────────────────────────┤
│ • Preserves full legal force      │       │ • Reduces reading complexity     │
│ • Maintains statutory register    │       │ • Omits technical jargon         │
│ • Precise Sanskritized Hindi      │       │ • Replaces modals with plain text│
│ • Equal judicial authority        │       │ • Paraphrases and summarizes     │
│ • Strict deontic equivalence      │       │ • Loss of exact legal standing   │
└───────────────────────────────────┘       └──────────────────────────────────┘
```

### 6.1 Authoritative Legal Standing
The Hindi texts in MILPaC are published by the **Legislative Department, Ministry of Law and Justice, Government of India**, pursuant to Article 348 of the Constitution of India and the Official Languages Act, 1963. They constitute the official authoritative Hindi text (*प्राधिकृत पाठ*) of Central Acts. In a court of law, this text carries formal statutory authority.

### 6.2 The Purpose of Statutory Translation: Equivalence, Not Simplification
- In **text simplification**, the objective is cognitive accessibility: reducing syntactic depth, shortening sentences, removing legalese, and using colloquial vocabulary.
- In **statutory translation**, the objective is **strict semantic and normative equivalence**: every right, obligation, condition precedent, and legal definition must hold exactly identical force in both languages.

### 6.3 Linguistic Register: High Formal Register
The Hindi translation does not use conversational Hindi (*बोलचाल की हिंदी*). Instead, it employs high-register, Sanskritized legal terminology (*विधिक शब्दावली*) formulated by the Official Language Commission to ensure exact conceptual correspondence with Anglo-Indian jurisprudence:
- `appointed day` $\rightarrow$ नियत दिन
- `without prejudice to the generality of the foregoing power` $\rightarrow$ पूर्वगामी शक्ति की व्यापकता पर प्रतिकूल प्रभाव डाले बिना
- `cognizance` $\rightarrow$ संज्ञान
- `moral turpitude` $\rightarrow$ नैतिक अधमता
- `abolition` $\rightarrow$ उत्सादन
- `discharge` $\rightarrow$ उन्मोचन

Treating these translations as "simplifications" would misrepresent the legal NLP task: our task is measuring **Legal Meaning Preservation (LMP)** across languages, evaluating whether legal nuances, obligations, and terminology are faithfully maintained.

---

## 7. Passages Suitable for Legal Meaning Preservation (LMP)

To build a robust benchmark for JUDGEBERT, the 706 English-Hindi pairs were analyzed to determine suitability:

| Category | Word Count | Count in Corpus | Suitability Assessment |
| :--- | :--- | :--- | :--- |
| **Short Headings / Sub-clauses** | < 10 words | 150 (21.25%) | **Low-to-Medium Priority:** Good for sanity checks, but lack rich legal semantics (e.g., "1. Short title", "2. Definitions"). |
| **Substantive Medium Clauses** | 10 – 50 words | 443 (62.75%) | **Highest Priority:** Ideal length for Transformer encoders; contains clear deontic verbs (*shall, may*), actors, and duties without risk of truncation. |
| **Complex Long Provisions** | > 50 words | 113 (16.01%) | **High Priority:** Essential for testing model capability on complex legal syntax, multi-part lists, and nested provisos (within BERT's 512-token limit). |

### Recommended Evaluation Criteria for LMP:
1. **Deontic Modal Presence:** Clauses containing normative modals (*shall, may, must, deemed to be*) that govern legal consequences.
2. **Specialized Term Density:** Clauses containing defined terms and legal constructs (*court of session, notification, inquiry, warrant*).
3. **Conditionality:** Passages with conditional conjunctions (*provided that, notwithstanding, subject to*).

---

## 8. Summary of Created Artifacts & Deliverables

1. [training/analyze_dataset.py](file:///c:/Projects/Legal-Meaning-Preservation/training/analyze_dataset.py):
   - Fully documented Python script using pandas and openpyxl.
   - Computes structural stats, language splits, token lengths, Act groupings, and 10 representative pairs.
   - Verified with exit code 0.
2. [reports/dataset_statistics.json](file:///c:/Projects/Legal-Meaning-Preservation/reports/dataset_statistics.json):
   - Machine-readable JSON export of all dataset profiling metrics.
3. [reports/dataset_analysis.md](file:///c:/Projects/Legal-Meaning-Preservation/reports/dataset_analysis.md):
   - This comprehensive, academic-standard inspection report.

---

## 9. Next Steps

With the dataset verified, profiled, and documented, the roadmap for Sunday's deadline is:
1. **Task 2: Preprocessing Pipeline (`training/preprocessing.py`)**:
   - Filter and clean the 706 English-Hindi pairs (standardize punctuation, remove trailing whitespace).
   - Create stratified train / validation / test splits across the 5 Central Acts.
   - Save processed splits to `data/processed/`.
2. **Task 3: Baseline & JUDGEBERT Setup (`training/train_baseline.py` & `training/train_judgebert.py`)**:
   - Set up multilingual encoders (e.g., multilingual BERT / IndicBERT / Legal-BERT).
   - Implement Legal Meaning Preservation (LMP) scoring formulation.
3. **Task 4: Explainability & Evaluation (`backend/explainability.py` & `backend/evaluation.py`)**:
   - Add token-level cross-lingual attribution and alignment explainability.

