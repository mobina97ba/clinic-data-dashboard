-- Staging: type, clean and validate raw text. One row in = one row out, plus a reject_reason.
DROP TABLE IF EXISTS stg_appointments;
CREATE TABLE stg_appointments AS
WITH base AS (
    SELECT
        source_row,
        NULLIF(TRIM(appointment_id), '')              AS appointment_id,
        NULLIF(TRIM(clinic), '')                      AS clinic_raw,
        TRIM(appointment_date)                        AS date_raw,
        LOWER(TRIM(status))                           AS status,
        REPLACE(REPLACE(REPLACE(TRIM(billed_amount),    '$', ''), ',', ''), ' ', '') AS billed_txt,
        REPLACE(REPLACE(REPLACE(TRIM(collected_amount), '$', ''), ',', ''), ' ', '') AS collected_txt,
        NULLIF(TRIM(patient_id), '')                  AS patient_id,
        NULLIF(TRIM(marketing_source), '')            AS source_raw
    FROM raw_appointments
),
typed AS (
    SELECT
        base.*,
        -- ISO dates are read as-is; dd/mm/yyyy is read day-first. Impossible dates (31/02) become NULL.
        CASE
            WHEN date_raw GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'
                 AND date(SUBSTR(date_raw, 1, 10)) = SUBSTR(date_raw, 1, 10)
                THEN SUBSTR(date_raw, 1, 10)
            WHEN date_raw GLOB '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]*'
                 AND date(SUBSTR(date_raw, 7, 4) || '-' || SUBSTR(date_raw, 4, 2) || '-' || SUBSTR(date_raw, 1, 2))
                     = SUBSTR(date_raw, 7, 4) || '-' || SUBSTR(date_raw, 4, 2) || '-' || SUBSTR(date_raw, 1, 2)
                THEN SUBSTR(date_raw, 7, 4) || '-' || SUBSTR(date_raw, 4, 2) || '-' || SUBSTR(date_raw, 1, 2)
        END AS appointment_date,
        CASE WHEN billed_txt NOT GLOB '*[^0-9.-]*' AND billed_txt GLOB '*[0-9]*'
             THEN CAST(billed_txt AS REAL) END        AS billed_amount,
        CASE WHEN collected_txt NOT GLOB '*[^0-9.-]*' AND collected_txt GLOB '*[0-9]*'
             THEN CAST(collected_txt AS REAL) END     AS collected_amount
    FROM base
),
-- Merge spellings that differ only by case/whitespace, keeping the most common one.
clinic_canon AS (
    SELECT k, name FROM (
        SELECT LOWER(clinic_raw) AS k, clinic_raw AS name,
               ROW_NUMBER() OVER (PARTITION BY LOWER(clinic_raw) ORDER BY COUNT(*) DESC, clinic_raw) AS rn
        FROM typed WHERE clinic_raw IS NOT NULL GROUP BY LOWER(clinic_raw), clinic_raw
    ) WHERE rn = 1
),
source_canon AS (
    SELECT k, name FROM (
        SELECT LOWER(source_raw) AS k, source_raw AS name,
               ROW_NUMBER() OVER (PARTITION BY LOWER(source_raw) ORDER BY COUNT(*) DESC, source_raw) AS rn
        FROM typed WHERE source_raw IS NOT NULL GROUP BY LOWER(source_raw), source_raw
    ) WHERE rn = 1
),
joined AS (
    SELECT
        t.source_row, t.appointment_id, c.name AS clinic, t.appointment_date, t.status,
        COALESCE(m.status_group, 'other')            AS status_group,
        t.billed_amount, t.collected_amount, t.patient_id,
        COALESCE(s.name, 'Unknown')                  AS marketing_source,
        ROW_NUMBER() OVER (PARTITION BY t.appointment_id ORDER BY t.source_row) AS id_rank
    FROM typed t
    LEFT JOIN clinic_canon c ON c.k = LOWER(t.clinic_raw)
    LEFT JOIN source_canon s ON s.k = LOWER(t.source_raw)
    LEFT JOIN ref_status_groups m ON m.status = t.status
)
SELECT
    joined.*,
    -- First failing rule wins; same priority order as the Python cleaner.
    CASE
        WHEN appointment_id IS NULL THEN 'Missing appointment ID'
        WHEN id_rank > 1 THEN 'Duplicate appointment ID'
        WHEN appointment_date IS NULL THEN 'Invalid date'
        WHEN billed_amount IS NULL OR collected_amount IS NULL THEN 'Missing or non-numeric amount'
        WHEN billed_amount < 0 OR collected_amount < 0 THEN 'Negative amount'
        WHEN clinic IS NULL THEN 'Missing clinic'
    END AS reject_reason
FROM joined;
