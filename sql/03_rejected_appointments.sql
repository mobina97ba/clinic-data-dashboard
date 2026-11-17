-- Every row that was left out, with the reason. Nothing disappears silently.
DROP TABLE IF EXISTS rejected_appointments;
CREATE TABLE rejected_appointments AS
SELECT source_row, appointment_id, reject_reason AS reason
FROM stg_appointments
WHERE reject_reason IS NOT NULL
ORDER BY source_row;
