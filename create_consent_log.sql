CREATE TABLE IF NOT EXISTS consent_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(15) NOT NULL,
    clinic_id UUID NOT NULL REFERENCES clinics(id),
    consent_given BOOLEAN NOT NULL,
    consent_source VARCHAR(20) NOT NULL,
    consent_version VARCHAR(20) NOT NULL,
    consent_text TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_consent_clinic_phone ON consent_log (clinic_id, phone);
CREATE INDEX IF NOT EXISTS ix_consent_log_phone ON consent_log (phone);
