DROP TABLE IF EXISTS mart_monthly;
CREATE TABLE mart_monthly AS
SELECT
    month,
    COUNT(*)                                   AS appointments,
    SUM(is_completed)                          AS completed,
    SUM(is_cancelled)                          AS cancelled,
    SUM(is_no_show)                            AS no_show,
    SUM(billed_completed)                      AS billed,
    SUM(collected_completed)                   AS collected,
    SUM(shortfall)                             AS outstanding,
    1.0 * (SUM(is_cancelled) + SUM(is_no_show)) / COUNT(*) AS lost_rate,
    1.0 * SUM(collected_completed) / NULLIF(SUM(billed_completed), 0) AS collection_rate
FROM v_measures
GROUP BY month;
