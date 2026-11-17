-- One definition of each measure, reused by every mart (single source of truth).
DROP VIEW IF EXISTS v_measures;
CREATE VIEW v_measures AS
SELECT
    *,
    CASE WHEN status_group = 'completed' THEN 1 ELSE 0 END AS is_completed,
    CASE WHEN status_group = 'cancelled' THEN 1 ELSE 0 END AS is_cancelled,
    CASE WHEN status_group = 'no_show'   THEN 1 ELSE 0 END AS is_no_show,
    CASE WHEN status_group = 'completed' THEN billed_amount    ELSE 0 END AS billed_completed,
    CASE WHEN status_group = 'completed' THEN collected_amount ELSE 0 END AS collected_completed,
    -- Per-visit shortfall: an overpayment on one visit never hides an unpaid one.
    CASE WHEN status_group = 'completed' AND billed_amount > collected_amount
         THEN billed_amount - collected_amount ELSE 0 END AS shortfall
FROM fct_appointments;
