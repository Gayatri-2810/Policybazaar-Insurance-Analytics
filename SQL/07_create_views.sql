USE policybazaar_db;
CREATE OR REPLACE VIEW vw_customer_analytics AS
SELECT c.*,
 CASE WHEN Age < 25 THEN 'Under 25' WHEN Age < 35 THEN '25–34' WHEN Age < 45 THEN '35–44' WHEN Age < 55 THEN '45–54' ELSE '55 and above' END AS Age_Group,
 CASE WHEN Age < 25 THEN 1 WHEN Age < 35 THEN 2 WHEN Age < 45 THEN 3 WHEN Age < 55 THEN 4 ELSE 5 END AS Age_Group_Sort,
 CASE Previously_Insured WHEN 1 THEN 'Previously Insured' ELSE 'Not Previously Insured' END AS Previous_Insurance_Status,
 CASE Vehicle_Damage WHEN 'Yes' THEN 'Damage Reported' ELSE 'No Damage Reported' END AS Vehicle_Damage_Category,
 CASE Response WHEN 1 THEN 'Interested' ELSE 'Not Interested' END AS Interest_Status,
 CASE Vehicle_Age WHEN '< 1 Year' THEN 1 WHEN '1-2 Year' THEN 2 ELSE 3 END AS Vehicle_Age_Sort
FROM insurance_customers c;

CREATE OR REPLACE VIEW vw_channel_performance AS
SELECT Policy_Sales_Channel,
 COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers,
 SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate,
 SUM(Annual_Premium) AS Total_Recorded_Annual_Premium,
 AVG(Annual_Premium) AS Average_Annual_Premium
FROM insurance_customers GROUP BY Policy_Sales_Channel;
