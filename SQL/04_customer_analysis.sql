USE policybazaar_db;
-- Run 07_create_views.sql before this analysis.
SELECT Age_Group, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Age_Group ORDER BY MIN(Age_Group_Sort);

SELECT Gender, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Gender ORDER BY Gender;

SELECT Previous_Insurance_Status, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Previous_Insurance_Status ORDER BY Previous_Insurance_Status;

SELECT Vehicle_Damage_Category, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Vehicle_Damage_Category ORDER BY Vehicle_Damage_Category;

SELECT Vehicle_Age, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Vehicle_Age ORDER BY MIN(Vehicle_Age_Sort);

SELECT Region_Code, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Region_Code ORDER BY Region_Code;

SELECT Age_Group, Gender, Previous_Insurance_Status, Vehicle_Damage_Category, COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate FROM vw_customer_analytics GROUP BY Age_Group, Gender, Previous_Insurance_Status, Vehicle_Damage_Category ORDER BY Interest_Rate DESC;
