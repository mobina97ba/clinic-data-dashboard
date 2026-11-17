DROP TABLE IF EXISTS mart_kpis;
CREATE TABLE mart_kpis AS
SELECT
    COUNT(*)                                   AS appointments,
    SUM(is_completed)                          AS completed,
    SUM(is_cancelled)                          AS cancelled,
    SUM(is_no_show)                            AS no_show,
    SUM(billed_completed)                      AS billed,
    SUM(collected_completed)                   AS collected,
    SUM(shortfall)                             AS outstanding,
    SUM(CASE WHEN shortfall > 0 THEN 1 ELSE 0 END) AS unpaid_visits,
    1.0 * SUM(is_cancelled) / COUNT(*)         AS cancel_rate,
    1.0 * SUM(is_no_show) / COUNT(*)           AS no_show_rate,
    1.0 * SUM(collected_completed) / NULLIF(SUM(billed_completed), 0) AS collection_rate
FROM v_measures;
