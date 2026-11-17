SELECT * FROM fct_appointments
WHERE appointment_id IS NULL OR clinic IS NULL OR appointment_date IS NULL
   OR billed_amount IS NULL OR collected_amount IS NULL;
