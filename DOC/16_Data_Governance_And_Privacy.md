# 16 - Data Governance and Privacy

## 1. Status and Scope

- Status: Draft
- Privacy owner: TBD
- Security owner: TBD
- Supported jurisdictions: TBD
- Personal health data storage decision: TBD

This document applies to user input, generated output, account data, telemetry, safety events, support records, evaluation datasets, backups, and data sent to external processors.

## 2. Default Position

Until a jurisdiction-specific privacy review approves otherwise:

- do not persist conversation content;
- do not accept medical-record or medical-image uploads;
- do not use real user conversations for training or evaluation;
- do not include health content in analytics, logs, alerts, or error traces;
- do not transfer user content to an undisclosed external processor;
- do not claim that data is anonymous unless re-identification risk has been assessed.

## 3. Required Data Inventory

Before collecting a data element, record:

| Field | Required description |
|---|---|
| Data element | Exact field or event collected |
| Classification | Public, internal, confidential, personal, or sensitive health data |
| Purpose | Specific product or legal purpose |
| Legal basis | Jurisdiction-specific basis, if applicable |
| Source | User, device, system, provider, or derived |
| Storage | System and geographic region |
| Access | Roles and services permitted to read it |
| Processor | Every external recipient or subprocessor |
| Retention | Exact duration or deletion trigger |
| Deletion | Method, timing, backups, and exceptions |
| Evidence owner | Person accountable for accuracy and review |

No production collection is allowed when a required inventory field is unknown.

## 4. Data Lifecycle Controls

### Collection

- Collect only fields necessary for an approved requirement.
- Provide an understandable notice before collection.
- Record consent only where consent is the approved legal basis.
- Reject unsupported uploads and remove accidental payloads from temporary storage.

### Processing

- Separate user content from authentication and operational metadata.
- Apply input and output redaction before observability systems.
- Restrict model and retrieval providers to documented purposes.
- Prohibit secondary use without a new review and user notice where required.

### Storage

- Encrypt data in transit and at rest using approved configurations.
- Use least-privilege service and human access.
- Separate production data from development and testing.
- Record access to sensitive data and protect audit logs from modification.

### Retention and Deletion

- Assign an exact retention rule to each stored category.
- Delete expired primary data automatically.
- Define when deleted data expires from backups and replicas.
- Support verified access, correction, export, and deletion requests where applicable.
- Preserve data only under an approved legal hold with access and expiry controls.

## 5. External Processors

Before sending any user content to a model, analytics, hosting, support, or monitoring provider:

1. document the provider, data fields, purpose, region, and retention;
2. review contract, training-use, deletion, security, and subprocessor terms;
3. configure the most privacy-protective available settings;
4. disclose the transfer as legally and ethically required;
5. verify failure behavior does not leak data to logs or retries;
6. maintain a tested method to stop transfers and rotate credentials.

## 6. Logging and Observability

Allowed by default:

- random request identifier;
- coarse service timing;
- status and bounded error code;
- model or policy version;
- safety-route category without raw health content.

Prohibited by default:

- raw prompts and responses;
- names, addresses, contact details, account tokens, or device identifiers;
- symptoms, diagnoses, medication details, or medical-record content;
- secrets, credentials, authorization headers, or session cookies.

Any exception requires a documented purpose, owner, access restriction, retention period, and privacy/security approval.

## 7. Development and Evaluation Data

- Prefer generated synthetic cases.
- Label synthetic data so it cannot be mistaken for clinical evidence.
- Do not copy production databases into non-production environments.
- Review datasets for hidden identifiers and memorized real records.
- Version datasets and document provenance, intended use, exclusions, and deletion rules.
- Restrict safety evaluation results when they contain exploit details.

## 8. Incident Response Minimums

The release process must define:

- how privacy or security incidents are detected and reported;
- a 24-hour accountable contact rotation or explicit operating-hours limitation;
- containment, credential rotation, evidence preservation, and recovery procedures;
- jurisdiction-specific notification decision owners and deadlines;
- a user communication owner and approved communication process;
- post-incident control updates and regression tests.

## 9. Approval Gate

Production use is blocked until:

- supported jurisdictions are selected;
- the data inventory is complete;
- retention and deletion are implemented and tested;
- all processors and subprocessors are approved;
- access controls and audit logging are verified;
- user notices and rights workflows are reviewed;
- incident response is tested;
- privacy, security, product, and legal owners approve the release.

