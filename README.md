Insurance Analytics | Power BI & MySQL
An interactive, three-page Power BI report exploring customer insurance interest, annual premium distributions, and sales-channel performance across 381,109 customer records.

 An independent portfolio project inspired by insurance marketplaces such as Policybazaar.
This project uses a public insurance cross-sell dataset, not internal Policybazaar data. Response = 1 indicates interest in vehicle insurance, not a confirmed purchase. Premium currency is unspecified, and channel codes do not identify online/offline channels. The dataset does not support calendar-based trends.

Project objective
Turn customer-level insurance data into an interactive report that helps answer:
- Which customer groups express the most interest in vehicle insurance?
- How does interest differ by age, gender, vehicle damage, and previous insurance?
- How do recorded annual premiums vary across customer and vehicle groups?
- Which sales-channel codes have the highest interested-customer counts and interest rates?
Technology stack
Tool	Role
MySQL Server	Store customer records and expose reporting views
MySQL Workbench / SQL	Create tables, validate data, and analyze customer segments
Power Query	Connect to MySQL and prepare column types
DAX	Calculate filter-aware KPIs and segment metrics
Power BI Desktop	Build interactive report pages, charts, slicers, and tables


Data workflow
CSV dataset → MySQL table → SQL views → Power Query → DAX measures → Power BI report

The supplied SQL importer contains dataset rows as INSERT statements. It is an alternative to importing the CSV manually; use only one loading method.

The report uses vw_customer_analytics, loaded as Customers, at one row per customer. This single-table model does not require relationships to the channel summary view.
Report pages
1. Executive Overview
High-level customer counts, insurance interest, average premium, and comparisons by customer and vehicle characteristics.

2. Customer Analysis
Customer distribution and interest rates across age, gender, previous insurance, vehicle damage, and region codes, with a detailed customer-segment matrix.

3. Premium & Sales Channels
Total, average, and median recorded annual premiums; premium distributions; channel comparisons; and detailed channel metrics.

The channel-interest-rate visual includes only channels with at least 1,000 customers in the current filter selection, reducing emphasis on rates from very small groups. The detailed channel table retains all channels.

Full-sample KPIs
These are reference values with all filters cleared.
Metric	Value
Total Customers	381,109
Interested Customers	46,710
Not Interested Customers	334,399
Interest Rate	12.26%
Average Annual Premium	30,564.39
Median Annual Premium	31,669.00
Total Recorded Annual Premium	11,648,363,949.00


The total recorded premium is an aggregation of the supplied premium field, not verified revenue.
Selected findings
- 12.26% of customers express interest in vehicle insurance.
- Customers aged 35–44 have 14,529 interested customers and an interest rate of approximately 21.59%.
- Customers aged 45–54 have an interest rate of approximately 20.18%.
- Customers reporting vehicle damage show a substantially higher observed interest rate than those reporting no damage.
- Premiums are concentrated in lower ranges, with a long tail of higher values; the histogram makes this distribution visible.
These are descriptive associations within the training sample, not evidence of causation or guaranteed future conversions.
