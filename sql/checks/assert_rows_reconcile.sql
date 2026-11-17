-- Every raw row must end up in exactly one of: fct_appointments or rejected_appointments.
SELECT 'row counts do not reconcile' AS problem
WHERE (SELECT COUNT(*) FROM raw_appointments)
   <> (SELECT COUNT(*) FROM fct_appointments) + (SELECT COUNT(*) FROM rejected_appointments);
