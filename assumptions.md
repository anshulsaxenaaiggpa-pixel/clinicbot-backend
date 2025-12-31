# Engineering Assumptions Log

**Purpose:** Record all technical decisions made when requirements were ambiguous.
**Principle:** When uncertain, choose the most privacy-preserving option.

---

## Sprint 1: Security Hardening (2025-12-30)

### Admin Authentication

**Assumption 1:** Password hashing algorithm
- **Decision:** Use bcrypt with cost factor 12
- **Rationale:** Industry standard, resistant to brute force
- **Alternative considered:** Argon2 (deferred to avoid dependency bloat)

**Assumption 2:** Session duration
- **Decision:** 30 minutes inactivity timeout, 8 hours absolute
- **Rationale:** Balance security and usability per Access Control Policy
- **Conservative choice:** Could have been longer, chose shorter for security

**Assumption 3:** MFA implementation
- **Decision:** TOTP (Time-based One-Time Password) using pyotp library
- **Rationale:** No dependency on SMS provider, works offline
- **Alternative considered:** SMS-based (rejected due to telecom dependency)

**Assumption 4:** Roles definition
- **Decision:** 3 roles initially: `super_admin`, `clinic_admin`, `support_viewer`
- **Rationale:** Least privilege principle, matches Access Control Policy
- **Future:** Can add more granular roles if needed

### Data Minimization

**Assumption 5:** Chat message storage
- **Decision:** DO NOT store WhatsApp message content by default
- **Rationale:** COMPLIANCE_BASELINE.md explicitly states "Chat transcripts will NOT be stored unless required"
- **Exception:** Store only structured appointment metadata (doctor, date, time)

**Assumption 6:** Phone number storage format
- **Decision:** Store in E.164 format (+919999999999)
- **Rationale:** International standard, enables future expansion
- **Validation:** Enforced via Pydantic schemas already implemented

**Assumption 7:** Log retention for debugging
- **Decision:** Application logs retained 90 days, audit logs 5 years
- **Rationale:** Balance debugging needs with data minimization
- **Scrubbing:** All logs scrubbed of PII before storage

### Encryption

**Assumption 8:** Database encryption at rest
- **Decision:** Rely on managed database provider encryption (AWS RDS, GCP Cloud SQL)
- **Rationale:** More reliable than application-level encryption
- **Verification:** Documented in deployment checklist

**Assumption 9:** Secrets management
- **Decision:** Use environment variables + AWS Secrets Manager (or equivalent)
- **Rationale:** Never commit secrets to repo
- **Implementation:** Secrets loaded at startup, never logged

**Assumption 10:** TLS version
- **Decision:** Enforce TLS 1.3 minimum (fallback to 1.2 if necessary)
- **Rationale:** Latest security standard
- **Configuration:** Set in web server config

### Backups

**Assumption 11:** Backup retention
- **Decision:** Daily backups, retained 30 days
- **Rationale:** Balance recovery capability with storage costs
- **Privacy:** Deletion requests must also apply to backups after retention period

**Assumption 12:** Backup encryption
- **Decision:** All backups encrypted using database provider's encryption
- **Rationale:** Consistent with data-at-rest encryption
- **Verification:** Automated test to verify backup restoration works

### Logging & Monitoring

**Assumption 13:** PII scrubbing in logs
- **Decision:** Automatically mask phone numbers (show last 4 digits only)
- **Rationale:** Balance debugging with privacy
- **Example:** +919999999999 → +91XXXXXXX9999

**Assumption 14:** Admin action logging
- **Decision:** Log ALL admin actions to audit_log table
- **Rationale:** Accountability and compliance requirement
- **Immutable:** Uses existing immutable audit_log infrastructure

### Consent UX

**Assumption 15:** Minor age verification
- **Decision:** Simple yes/no prompt: "Are you 18 or older?"
- **Rationale:** Self-declaration, no age verification service needed
- **Conservative:** Reject if answer is NO, no parental consent flow in MVP

**Assumption 16:** Consent display timing
- **Decision:** Show consent on FIRST message, block all processing until YES
- **Rationale:** Per COMPLIANCE_BASELINE.md, consent required before data processing
- **UX:** Single consent covers all future interactions

### WhatsApp Integration

**Assumption 17:** Webhook security
- **Decision:** Verify Twilio signatures on all incoming webhooks
- **Rationale:** Prevent spoofed messages
- **Implementation:** Signature verification middleware

**Assumption 18:** Message retry logic
- **Decision:** Retry failed deliveries 3 times with exponential backoff
- **Rationale:** Handle temporary network issues
- **Limit:** After 3 failures, log and alert (don't retry indefinitely)

---

## Data Classification Map

### PII (Personally Identifiable Information)
**Storage:** Encrypted, access-controlled, deletable
- Phone number (E.164 format)
- Patient name (optional)
- Clinic-assigned identifiers

### Non-PII
**Storage:** Normal database tables
- Appointment date/time (without patient linkage)
- Clinic/doctor/service IDs
- Aggregate statistics

### System Logs
**Storage:** Scrubbed before persistence
- Error logs (PII masked)
- Performance metrics (anonymized)
- Security events (phone hashed)

### Audit Logs
**Storage:** Immutable, phone hashed
- Consent granted/withdrawn
- Appointment created/deleted
- Admin actions
- Retention: 5 years

### NEVER Store
- ❌ WhatsApp message content (full text)
- ❌ Medical symptoms
- ❌ Diagnosis information
- ❌ Passwords (only hashes)
- ❌ Payment card data

---

## Future Decisions Needed

1. **MFA enforcement timeline** - When to make MFA mandatory for all admins?
   - Recommendation: Immediately for super_admin, 30 days grace for others

2. **Password rotation policy** - Force password change every 90 days?
   - Recommendation: Yes, per Access Control Policy

3. **Failed login lockout** - How many attempts before lockout?
   - Recommendation: 5 attempts, 30-minute lockout (per Access Control Policy)

4. **Session storage** - Redis or database?
   - Recommendation: Redis (faster, auto-expiry)

5. **IP whitelisting for admins** - Restrict admin access to known IPs?
   - Recommendation: Optional per clinic, not enforced globally

---

**Last Updated:** 2025-12-30  
**Review Frequency:** After each sprint or when ambiguity arises
