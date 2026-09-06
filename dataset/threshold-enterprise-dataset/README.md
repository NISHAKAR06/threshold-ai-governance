# Threshold Enterprise Knowledge Base

## 1. Dataset Name
**Threshold Enterprise Knowledge Base** (Synthetic Enterprise Dataset for AI Governance and RAG)

---

## 2. Dataset Purpose
The **Threshold Enterprise Knowledge Base** is a foundational, synthetic enterprise corpus designed for the **THRESHOLD AI** platform—an Enterprise Governed AI and Retrieval-Augmented Generation (RAG) system.

This dataset provides a realistic, structurally consistent, and permission-tagged corpus that models the operational reality of a modern multinational technology corporation. It establishes the schema, hierarchy, metadata standards, and categorization rules required for subsequent ingestion, retrieval benchmarking, and governance testing.

> **Note on Implementation State:**  
> This dataset has completed **Phase 1: Dataset Foundation & Metadata Structure**, **Phase 2: Human Resources Synthetic Document Creation**, **Phase 3: Information Security Synthetic Document Creation**, **Phase 4: AI Governance Synthetic Document Creation**, **Phase 5: Engineering Synthetic Document Creation**, and **Phase 6: Operations Synthetic Document Creation**. The initial synthetic enterprise source-document dataset is complete (40 total documents). The dataset is *designed to support* downstream AI workflows and is ready for future ingestion, chunking, embedding generation, vector indexing, hybrid search, permission-aware retrieval, retrieval evaluation, and AI governance testing phases, but does not itself implement indexing, retrieval algorithms, embeddings, or backend pipelines.

---

## 3. Company Overview
* **Company Name:** Threshold Enterprise Systems
* **Nature of Business:** Fictional multinational enterprise technology provider specializing in:
  * Artificial Intelligence (AI) solutions and foundation model governance
  * Enterprise Cloud platforms and infrastructure
  * Big Data platforms, analytics, and streaming architecture
  * Enterprise business software and workflows
  * Global digital transformation and advisory services
* **Company Size:** Approximately 5,000 employees globally.
* **Global Locations:**
  * **India** (Bangalore & Hyderabad - R&D and Engineering Hubs)
  * **United States** (San Francisco, CA & New York, NY - Global HQ and Sales)
  * **United Kingdom** (London - European Operations and Compliance)
  * **Singapore** (Asia-Pacific Regional Operations and AI Governance)
* **Data Integrity Notice:** All corporate entities, policies, operational documents, and data artifacts are 100% synthetic. No actual employee names, real proprietary corporate secrets, or copyrighted commercial documents are included.

---

## 4. Company Departments
Threshold Enterprise Systems operates seven primary corporate departments defined in `metadata/department_definitions.json`:

| Department ID | Department Name | Scope & Responsibilities | Key Roles |
|---|---|---|---|
| `DEPT-HR` | **Human Resources** | Talent acquisition, onboarding, workplace relations, compensation & benefits, and workforce compliance. | `HR_MANAGER`, `EMPLOYEE` |
| `DEPT-ENG` | **Engineering** | Distributed systems, cloud infrastructure, microservices, API platforms, CI/CD pipelines, and software quality. | `ENGINEER`, `MANAGER`, `EMPLOYEE` |
| `DEPT-AI-DATA` | **AI & Data** | Machine learning research, data lakes, generative AI integration, feature engineering, and model observability. | `AI_ENGINEER`, `ENGINEER`, `MANAGER`, `EMPLOYEE` |
| `DEPT-INFOSEC` | **Information Security** | Zero-trust architecture, threat detection, vulnerability management, security audits (SOC 2, ISO 27001), and incident response. | `SECURITY_ENGINEER`, `ADMIN`, `EMPLOYEE` |
| `DEPT-OPS` | **Operations** | 24/7 global service availability, IT service desk (ITSM), disaster recovery, vendor procurement, and facilities. | `OPERATIONS_MANAGER`, `MANAGER`, `EMPLOYEE` |
| `DEPT-FIN` | **Finance** | FP&A, global payroll, corporate accounting, statutory audits, tax compliance, and cloud FinOps economics. | `MANAGER`, `EMPLOYEE` |
| `DEPT-GOV` | **Enterprise Governance** | Corporate compliance, AI ethics frameworks, algorithmic risk assessment, data privacy regulations, and audit trails. | `ADMIN`, `MANAGER`, `EMPLOYEE` |

---

## 5. User Roles
The dataset strictly adheres to eight standardized enterprise roles, detailed in `metadata/role_permissions.json`:

1. **`EMPLOYEE`**: Baseline corporate workforce member across any department. Permitted access to `PUBLIC` and `INTERNAL` documentation.
2. **`MANAGER`**: Functional or people manager. Permitted access to `PUBLIC`, `INTERNAL`, and department-relevant `CONFIDENTIAL` records.
3. **`ENGINEER`**: Software, platform, or infrastructure development professional. Permitted access to `PUBLIC`, `INTERNAL`, and `Engineering` `CONFIDENTIAL` technical documentation.
4. **`AI_ENGINEER`**: Machine learning and AI systems specialist. Permitted access to `PUBLIC`, `INTERNAL`, and relevant `AI & Data` as well as `Enterprise Governance` `CONFIDENTIAL` documents.
5. **`SECURITY_ENGINEER`**: Cybersecurity professional. Permitted access to `PUBLIC`, `INTERNAL`, `Information Security` `CONFIDENTIAL` records, and explicitly authorized `RESTRICTED` security records.
6. **`OPERATIONS_MANAGER`**: Operational leader. Permitted access to `PUBLIC`, `INTERNAL`, and relevant `Operations` `CONFIDENTIAL` documents.
7. **`HR_MANAGER`**: Human resources leader. Permitted access to `PUBLIC`, `INTERNAL`, and relevant `Human Resources` `CONFIDENTIAL` documents.
8. **`ADMIN`**: Enterprise system administrator. Unrestricted administrative access across `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, and `RESTRICTED` classifications across all departments.

---

## 6. Document Classifications
Four explicit sensitivity tiers govern all documents, configured in `metadata/classification_rules.json`:

* **`PUBLIC`**: Information accessible to everyone, including external entities, customers, and partners. Requires no authentication or clearance.
* **`INTERNAL`**: Information intended for authenticated employees and authorized contractors of Threshold Enterprise Systems. Requires valid enterprise credentials.
* **`CONFIDENTIAL`**: Information accessible only to authorized departments, specific management tiers, or explicitly cleared roles. Department-aware restrictions apply.
* **`RESTRICTED`**: Highly sensitive enterprise information strictly limited to explicitly authorized roles and individuals under need-to-know controls (e.g. security breach forensics, cryptographic keys, root credentials).

---

## 7. Document Status Definitions
Document lifecycle and authority states are defined in `metadata/document_status_rules.json`:

* **`DRAFT`**: Document is under preparation, pending review or stakeholder approval, and is **not considered authoritative**. Excluded by default from standard RAG retrieval.
* **`ACTIVE`**: Current, officially approved, authoritative document enforced across the enterprise. **Prioritized** as primary source in RAG retrieval.
* **`ARCHIVED`**: Historical document retained for compliance, audit trails, and institutional memory. Non-authoritative and down-weighted in production retrieval.
* **`SUPERSEDED`**: Document replaced by a newer version or policy. Non-authoritative, lowest retrieval priority, with references pointing to superseding versions.

---

## 8. Document Types
Documents are categorized into eight standardized formats defined in `metadata/document_type_definitions.json`:

1. **`POLICY`**: High-level, mandatory enterprise rule defining required organizational conduct and compliance boundaries.
2. **`STANDARD`**: Mandatory technical, architectural, or procedural specification requiring strict adherence.
3. **`GUIDELINE`**: Recommended best practices, advisory patterns, and non-mandatory operational guidance.
4. **`PROCEDURE`**: Step-by-step sequential instructions established for repeatable operational and administrative execution.
5. **`RUNBOOK`**: Highly technical, step-by-step guide for engineers and operators to perform system maintenance and incident remediation.
6. **`HANDBOOK`**: Comprehensive reference manual compiling policies, culture, and benefits for broad organizational consumption.
7. **`FRAMEWORK`**: Broad conceptual structure establishing principles, maturity models, and governance criteria.
8. **`PLAYBOOK`**: Strategic, scenario-based operational response guide for rapid incident handling and crisis management.

---

## 9. Folder Structure
```text
dataset/
└── threshold-enterprise-dataset/
    │
    ├── README.md                              # Comprehensive dataset documentation
    │
    ├── source_documents/                      # Categorized enterprise source documents
    │   ├── hr/                                # Human Resources documents (8)
    │   ├── security/                          # Information Security documents (7)
    │   ├── ai_governance/                     # AI & Data Governance documents (10)
    │   ├── engineering/                       # Software & Cloud Engineering documents (7)
    │   └── operations/                        # Infrastructure & Business Operations documents (8)
    │
    ├── metadata/                              # Machine-readable schemas & governance rules
    │   ├── department_definitions.json        # 7 Enterprise department definitions & scopes
    │   ├── role_permissions.json              # 8 User roles & permission boundaries
    │   ├── classification_rules.json          # 4 Classification tiers & handling rules
    │   ├── document_status_rules.json         # 4 Lifecycle statuses & retrieval priority
    │   ├── document_type_definitions.json     # 8 Standard document types & intended uses
    │   └── document_registry.json             # Document registry & schema (40 documents cataloged)
    │
    ├── data/                                  # Ingestion pipeline outputs (Phase 8)
    │   ├── normalized_documents/              # Cleaned UTF-8 JSON documents with SHA-256 hashes (40)
    │   └── ingestion_manifests/               # Batch ingestion execution manifests
    │
    ├── evaluation/                            # Reserved for future RAG retrieval benchmark queries
    │
    └── adversarial_tests/                     # Reserved for future security & permission tests
```

---

## 10. Metadata Architecture
The metadata tier establishes machine-readable governance contracts that bridge document storage and future AI capabilities:

* **Department Definitions (`department_definitions.json`):** Maps department identifiers (`DEPT-HR`, `DEPT-ENG`, etc.) to corporate responsibilities and permitted roles.
* **Role Permissions (`role_permissions.json`):** Encodes the enterprise access control matrix, specifying classification boundaries, department scopes for `CONFIDENTIAL` materials, and explicit authorization scopes for `RESTRICTED` assets.
* **Classification Rules (`classification_rules.json`):** Specifies access preconditions, handling controls, encryption requirements, and header markings for all four classification levels.
* **Document Status Rules (`document_status_rules.json`):** Codifies lifecycle states, authoritative flags, and search rank weights to prioritize `ACTIVE` records over `ARCHIVED` or `SUPERSEDED` records.
* **Document Type Definitions (`document_type_definitions.json`):** Defines operational intent for policies, runbooks, frameworks, playbooks, and standards.
* **Document Registry (`document_registry.json`):** Provides a schema-validated catalog supporting thirteen document metadata attributes (`document_id`, `title`, `department`, `classification`, `version`, `status`, `effective_date`, `allowed_roles`, `document_type`, `summary`, `keywords`, `file_path`, `file_format`) populated with forty Phase 2 Human Resources, Phase 3 Information Security, Phase 4 AI Governance, Phase 5 Engineering, and Phase 6 Operations documents.

---

## 11. Future RAG Usage
This synthetic dataset is architected to serve as the ground-truth benchmark for the THRESHOLD AI platform. In subsequent phases, it will support:

1. **Document Ingestion:** Automated multi-format parsing and ingestion pipelines reading source documents and accompanying metadata.
2. **Document Chunking:** Semantic, structural, and hierarchical chunking tailored by document type (e.g. policies vs. step-by-step runbooks).
3. **Embedding Generation:** Vectorization using dense sentence transformers and sparse BM25 tokenizers.
4. **Vector Search:** Dense semantic similarity queries against high-dimensional vector indexes.
5. **Hybrid Retrieval:** Combined dense semantic and lexical keyword search utilizing the structured `keywords` and `summary` fields.
6. **Permission-Aware Retrieval:** Filtering query contexts at inference time using `allowed_roles`, `classification`, and department-level scopes to prevent unauthorized knowledge leaks.
7. **RAG Evaluation:** Benchmarking retrieval precision, recall, context relevance, faithfulness, and answer correctness against structured ground-truth questions.
8. **AI Governance & Security Testing:** Stress-testing the retrieval boundaries using adversarial prompts, indirect prompt injection tests, and privilege escalation simulations.

---

## 12. Current Dataset Coverage

* **Human Resources:** 8 documents
* **Information Security:** 7 documents
* **AI Governance:** 10 documents
* **Engineering:** 7 documents
* **Operations:** 8 documents

**Total current documents:** 40


