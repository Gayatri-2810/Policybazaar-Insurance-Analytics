USE policybazaar_db;
SELECT Age_Group, COUNT(*) AS Total_Customers, SUM(Annual_Premium) AS Total_Recorded_Annual_Premium, AVG(Annual_Premium) AS Average_Annual_Premium, MIN(Annual_Premium) AS Minimum_Premium, MAX(Annual_Premium) AS Maximum_Premium FROM vw_customer_analytics GROUP BY Age_Group;

SELECT Vehicle_Age, COUNT(*) AS Total_Customers, SUM(Annual_Premium) AS Total_Recorded_Annual_Premium, AVG(Annual_Premium) AS Average_Annual_Premium, MIN(Annual_Premium) AS Minimum_Premium, MAX(Annual_Premium) AS Maximum_Premium FROM vw_customer_analytics GROUP BY Vehicle_Age;

SELECT Gender, COUNT(*) AS Total_Customers, SUM(Annual_Premium) AS Total_Recorded_Annual_Premium, AVG(Annual_Premium) AS Average_Annual_Premium, MIN(Annual_Premium) AS Minimum_Premium, MAX(Annual_Premium) AS Maximum_Premium FROM vw_customer_analytics GROUP BY Gender;

SELECT Response, COUNT(*) AS Total_Customers, SUM(Annual_Premium) AS Total_Recorded_Annual_Premium, AVG(Annual_Premium) AS Average_Annual_Premium, MIN(Annual_Premium) AS Minimum_Premium, MAX(Annual_Premium) AS Maximum_Premium FROM vw_customer_analytics GROUP BY Response;

-- Median is calculated in 03_data_validation.sql. Premium total is not revenue.
