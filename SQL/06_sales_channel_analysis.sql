USE policybazaar_db;
-- Codes retained; no inferred channel names or online/offline labels.
SELECT * FROM vw_channel_performance ORDER BY Interested_Customers DESC, Policy_Sales_Channel LIMIT 10;
-- 1,000 is an analyst-selected exploratory size floor, not statistical significance.
SELECT * FROM vw_channel_performance WHERE Total_Customers >= 1000
ORDER BY Interest_Rate DESC, Total_Customers DESC, Policy_Sales_Channel LIMIT 10;
SELECT * FROM vw_channel_performance ORDER BY Policy_Sales_Channel;
