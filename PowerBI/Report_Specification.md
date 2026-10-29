# Three-page report construction specification

These are implementation specifications, not a native report. The PNGs are static data-based design previews, not Power BI screenshots. All previews show the complete sample without filters.

## Canvas and styling

Use a 1600 × 1000 custom canvas. Sidebar x=0, y=0, w=220, h=1000; fill #0B2B55. Main background #F3F8FE. Header x=245,y=15,w=1080,h=65. Sidebar has a project label and page navigator, not a copied company logo. Add “Independent portfolio project; customer interest, not purchases” below the title. Do not add a fake last-updated business date, dollar sign or growth arrows.

KPI row: four cards at x=245,515,785,1055; y=100; w=250,h=105. Chart grid: x=245,615,985; y=245 and 570; w=345,h=280. Slicer column: x=1360, y=100,w=220,h=800. Titles 13–14 pt Segoe UI Semibold, labels 10–11 pt, KPI values 26–30 pt. White chart containers, light blue borders, blue #1671F3 and #8DBDFA series. Add a compact insight text box at x=245,y=890,w=1080,h=75. Use tooltips rather than densely labelling all categories.

## All pages: slicers and interactions

Seven dropdown slicers: Gender, Age_Group, Vehicle_Age, Vehicle_Damage_Category, Previous_Insurance_Status, Region_Code, Policy_Sales_Channel. Use Customers fields. Put all on each page; use Sync slicers to sync and show all seven across pages. Enable search on code dropdowns. No default selection. Sort age and vehicle categories by their sort columns. Use Edit interactions: every slicer filters every data visual and KPI; for charts, choose Filter (not Highlight) on other charts so counts/rates use the same visible population. A static insight box must say “Full-sample findings; unaffected by slicers” or be replaced with dynamic DAX text before final publication.

Use a page navigator in the sidebar. In Desktop test navigator buttons with Ctrl+click. Add tooltips with Total Customers, Interested Customers, Interest Rate %, and Average Annual Premium. Do not use pre-aggregated SQL views for chart rates. Never sum or average row-level percentages.

## Page 1: Executive Overview

Cards: Total Customers; Interested Customers; Interest Rate %; Average Annual Premium.

Six chart slots in reading order:
1. Donut: legend Interest_Status, values Total Customers.
2. Bar: Age_Group, Interested Customers; sorted by Age_Group_Sort.
3. Column: Vehicle_Damage_Category, Interest Rate %.
4. Bar: Gender, Total Customers.
5. Column: Previous_Insurance_Status, Total Customers; add Interest Rate % as tooltip.
6. Bar: Vehicle_Age, Total Customers; add Interest Rate % as tooltip.

The static overview preview uses interest rate for vehicle age to make segment differences visible; final native report uses the customer-count bar above. Both metrics are supplied in expected tables.

Insights: use the full-sample values in Business_Insights.md, with the full-sample label. No purchase claims.

## Page 2: Customer Analysis

Use eight visuals in a 3-column grid with two main rows y=245 and 510 (height 220) plus a final row y=775 (height 170). Keep slicers at right and omit the full-sample insight footer on this page to prevent overlap.

1. Age_Group / Total Customers, column.
2. Gender / Total Customers, bar.
3. Age_Group / Interest Rate %, line or column.
4. Gender / Interest Rate %, column.
5. Previous_Insurance_Status / Total Customers and Interested Customers, clustered column; rate tooltip.
6. Vehicle_Damage_Category / Total Customers and Interested Customers, clustered column; rate tooltip.
7. Region_Code / Total Customers, bar; top 10 by count, rate tooltip, all codes available via slicer and table.
8. Matrix spanning two chart widths: rows Age_Group, Gender, Previous_Insurance_Status, Vehicle_Damage_Category; values Total Customers, Interested Customers, Interest Rate %, Average Annual Premium. Add Region_Code as optional drill-down row. Enable hierarchy drill controls; totals must recalculate the rate.

Cards remain the same as page 1. Static preview displays six representative customer visuals; the native report must include all eight specified here.

## Page 3: Premium and Sales Channel Analysis

Cards: Total Recorded Annual Premium; Average Annual Premium; Median Annual Premium; Interested Customers. Use the same eight-visual arrangement as page 2, with the final channel table spanning two widths.

1. Age_Group / Average Annual Premium, column; Total Recorded Annual Premium tooltip.
2. Vehicle_Age / Average Annual Premium, column; total premium tooltip.
3. Policy_Sales_Channel / Interested Customers, bar (all codes; scrolling allowed).
4. Policy_Sales_Channel / Interest Rate %, column; visual-level Channel Sample Eligible = 1. Title “Channel Interest Rate (≥1,000 customers in current selection)”.
5. Top 10 channels: Policy_Sales_Channel / Interested Customers, descending. Native Top N = 10 using Interested Customers. Include Total Customers and Interest Rate % tooltips; tied ranks may show more than 10 in Power BI. Expected CSV uses channel code ascending to break count ties.
6. Premium histogram: create Annual_Premium bins (width 10,000); values Total Customers. Retain all premiums and use a log scale where supported.
7. Vehicle_Age / Total Recorded Annual Premium, column.
8. Detailed table: Policy_Sales_Channel; Total Customers; Interested Customers; Interest Rate %; Total Recorded Annual Premium; Average Annual Premium. Include all codes, sortable by each measure. Do not apply the rate-chart size filter to the table.

## Local acceptance tests

Clear all filters and compare the nine required DAX measures with Validation/Expected_KPIs.json. Compare chart categories with Validation/*_Expected.csv. Confirm slicers all affect cards/charts, combined slicers produce the expected SQL population, clearing filters restores totals, and all three navigator buttons work. In a deliberately empty selection, interest rate should be blank rather than a fabricated zero. Export screenshots from Desktop only after these tests. Replace this package's static previews with those actual screenshots when publishing your portfolio.
