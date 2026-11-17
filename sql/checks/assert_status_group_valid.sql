SELECT * FROM fct_appointments WHERE status_group NOT IN ('completed', 'cancelled', 'no_show', 'other');
