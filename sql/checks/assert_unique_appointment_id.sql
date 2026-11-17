SELECT appointment_id, COUNT(*) AS copies FROM fct_appointments GROUP BY appointment_id HAVING COUNT(*) > 1;
