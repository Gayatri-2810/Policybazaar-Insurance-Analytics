USE policybazaar_db;
SELECT COUNT(*) AS actual_rows, 381109 AS expected_rows,
 CASE WHEN COUNT(*)=381109 THEN 'PASS' ELSE 'FAIL' END AS row_count_check,
 COUNT(*)-COUNT(DISTINCT id) AS duplicate_id_count FROM insurance_customers;
SELECT COUNT(*) AS rows_with_nulls FROM insurance_customers WHERE `id` IS NULL OR `Gender` IS NULL OR `Age` IS NULL OR `Driving_License` IS NULL OR `Region_Code` IS NULL OR `Previously_Insured` IS NULL OR `Vehicle_Age` IS NULL OR `Vehicle_Damage` IS NULL OR `Annual_Premium` IS NULL OR `Policy_Sales_Channel` IS NULL OR `Vintage` IS NULL OR `Response` IS NULL;
SELECT COUNT(*) AS invalid_rows FROM insurance_customers
WHERE Response NOT IN (0,1) OR Previously_Insured NOT IN (0,1)
 OR Driving_License NOT IN (0,1) OR Annual_Premium < 0 OR Age NOT BETWEEN 1 AND 120
 OR Gender NOT IN ('Male','Female') OR Vehicle_Damage NOT IN ('Yes','No')
 OR Vehicle_Age NOT IN ('< 1 Year','1-2 Year','> 2 Years');
SELECT COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers,
 COUNT(*)-SUM(Response) AS Not_Interested_Customers,
 SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate,
 SUM(Annual_Premium) AS Total_Recorded_Annual_Premium,
 AVG(Annual_Premium) AS Average_Annual_Premium, AVG(Age) AS Average_Age,
 SUM(Previously_Insured) AS Previously_Insured_Customers
FROM insurance_customers;
-- Expected: 381109, 46710, 334399, 0.122563361138, 11648363949.00.
SELECT MIN(Annual_Premium) AS min_premium, MAX(Annual_Premium) AS max_premium
FROM insurance_customers;
WITH ranked AS (
 SELECT Annual_Premium, ROW_NUMBER() OVER (ORDER BY Annual_Premium) AS rn,
 COUNT(*) OVER () AS n FROM insurance_customers
)
SELECT AVG(Annual_Premium) AS median_premium FROM ranked
WHERE rn IN (FLOOR((n+1)/2), FLOOR((n+2)/2));
