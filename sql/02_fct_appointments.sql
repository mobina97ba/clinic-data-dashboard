-- Fact table: only rows that passed every validation rule.
DROP TABLE IF EXISTS fct_appointments;
CREATE TABLE fct_appointments AS
SELECT
    source_row, appointment_id, clinic, appointment_date,
    SUBSTR(appointment_date, 1, 7) AS month,
    status, status_group, billed_amount, collected_amount, patient_id, marketing_source
FROM stg_appointments
WHERE reject_reason IS NULL;
