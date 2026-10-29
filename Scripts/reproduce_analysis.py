from pathlib import Path
import json, hashlib, sqlite3, zipfile, shutil, textwrap
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

P=Path(__file__).resolve().parents[1]
ROOT=P.parent
for name in ['SQL','PowerBI','Documentation','Dashboard_Screenshots','Validation','Scripts']:
    (P/name).mkdir(parents=True,exist_ok=True)
def write(name,s):
    (P/name).write_text(s,encoding='utf-8')
def table(d):
    d=d.copy()
    for c in d.select_dtypes('number'):
        d[c]=d[c].map(lambda v: f'{v:,.4f}' if isinstance(v,float) else f'{v:,}')
    return '| '+' | '.join(map(str,d.columns))+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in d.itertuples(index=False,name=None))+'\n'

d=pd.read_csv(P/'Dataset/train.csv')
original=d.copy()
cols=list(original.columns)
n=len(d); interested=int(d.Response.sum()); premium=float(d.Annual_Premium.sum())
age_labels=['Under 25','25–34','35–44','45–54','55 and above']
d['Age_Group']=pd.cut(d.Age,[0,24,34,44,54,np.inf],labels=age_labels).astype(str)
d['Age_Group_Sort']=d.Age_Group.map(dict(zip(age_labels,range(1,6))))
d['Previous_Insurance_Status']=d.Previously_Insured.map({0:'Not Previously Insured',1:'Previously Insured'})
d['Vehicle_Damage_Category']=d.Vehicle_Damage.map({'Yes':'Damage Reported','No':'No Damage Reported'})
d['Interest_Status']=d.Response.map({1:'Interested',0:'Not Interested'})
d['Vehicle_Age_Sort']=d.Vehicle_Age.map({'< 1 Year':1,'1-2 Year':2,'> 2 Years':3})
def group(col):
    x=d.groupby(col,observed=True).agg(Total_Customers=('id','size'),Interested_Customers=('Response','sum'),Total_Recorded_Annual_Premium=('Annual_Premium','sum'),Average_Annual_Premium=('Annual_Premium','mean'),Median_Annual_Premium=('Annual_Premium','median')).reset_index()
    x['Interest_Rate']=x.Interested_Customers/x.Total_Customers
    return x
groups={col:group(col) for col in ['Age_Group','Gender','Previous_Insurance_Status','Vehicle_Damage_Category','Vehicle_Age','Region_Code','Policy_Sales_Channel']}
for col,x in groups.items():
    x.to_csv(P/f'Validation/{col}_Expected.csv',index=False)
kpis={'Total Customers':n,'Interested Customers':interested,'Not Interested Customers':n-interested,'Interest Rate %':interested/n,'Total Recorded Annual Premium':premium,'Average Annual Premium':float(d.Annual_Premium.mean()),'Median Annual Premium':float(d.Annual_Premium.median()),'Average Customer Age':float(d.Age.mean()),'Previously Insured Customers':int(d.Previously_Insured.sum()),'Not Previously Insured Customers':int((d.Previously_Insured==0).sum())}
write('Validation/Expected_KPIs.json',json.dumps(kpis,indent=2))
sha=hashlib.sha256((P/'Dataset/train.csv').read_bytes()).hexdigest()
schema=pd.DataFrame({'Column':cols,'CSV inferred dtype':[str(original[c].dtype) for c in cols],'Missing':[int(original[c].isna().sum()) for c in cols],'Distinct':[original[c].nunique() for c in cols]})
profile='# Complete training-data profile\n\n'+f'All {n:,} training rows and {len(cols)} columns were read. Source: user-supplied ZIP, train.csv only.\n\nSHA-256: `{sha}`.\n\n'+table(schema)
profile+=f'\nDuplicate IDs: {d.id.duplicated().sum():,}. Duplicate complete rows: {original.duplicated().sum():,}. Duplicate feature rows excluding ID: {original.drop(columns="id").duplicated().sum():,}; these are retained because different IDs may share attributes.\n\n'
profile+='## Numerical distributions\n\n'+table(original.describe(percentiles=[.01,.25,.5,.75,.95,.99]).reset_index().rename(columns={'index':'Statistic'}))
profile+='\n## Categorical and coded-variable distributions\n\n'
for c in ['Gender','Driving_License','Region_Code','Previously_Insured','Vehicle_Age','Vehicle_Damage','Policy_Sales_Channel','Response']:
    profile+='\n### '+c+'\n\n'+table(original[c].value_counts(dropna=False).sort_index().rename_axis(c).reset_index(name='Count'))
profile+='\n## Age-group distribution and interest\n\n'+table(groups['Age_Group'])
q1,q3=d.Annual_Premium.quantile([.25,.75]); threshold=q3+1.5*(q3-q1)
profile+=f'\n## Quality decisions\n\nNo null imputation is needed. All customer IDs are unique. Response, Driving_License, and Previously_Insured are binary. Region and channel codes are whole-valued despite decimal CSV notation; they are identifiers, not continuous measures.\n\nPremium min {d.Annual_Premium.min():,.0f}; max {d.Annual_Premium.max():,.0f}; mean {d.Annual_Premium.mean():,.2f}; median {d.Annual_Premium.median():,.0f}. There are {int((d.Annual_Premium>threshold).sum()):,} premiums above the descriptive 1.5-IQR upper fence ({threshold:,.2f}). Retain these records; the fence is not evidence of error. Premium 2,630 occurs {int((d.Annual_Premium==2630).sum()):,} times; investigate source meaning rather than replacing it.\n\nResponse 1 means interest in vehicle insurance, not purchase. The target is imbalanced: {interested:,} interested and {n-interested:,} not interested ({interested/n:.4%} interested). No transaction date or verified online/offline channel mapping exists. No currency symbol is assigned because the uploaded CSV does not establish a currency. Vintage is customer tenure in days, not a calendar date. Test.csv and sample_submission.csv are excluded because they are not additional labelled training records.\n'
write('Documentation/Data_Profile.md',profile)

write('SQL/01_create_database.sql','-- Non-destructive: does not drop existing objects. MySQL 8.0.16+ recommended.\nCREATE DATABASE IF NOT EXISTS policybazaar_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\nUSE policybazaar_db;\n')
sqltypes=['INT UNSIGNED','VARCHAR(10)','TINYINT UNSIGNED','TINYINT UNSIGNED','SMALLINT UNSIGNED','TINYINT UNSIGNED','VARCHAR(15)','VARCHAR(3)','DECIMAL(12,2)','SMALLINT UNSIGNED','SMALLINT UNSIGNED','TINYINT UNSIGNED']
defs=[f'  `{c}` {t} NOT NULL'+(' PRIMARY KEY' if c=='id' else '') for c,t in zip(cols,sqltypes)]
defs += ['  CHECK (`Response` IN (0,1))','  CHECK (`Driving_License` IN (0,1))','  CHECK (`Previously_Insured` IN (0,1))',"  CHECK (`Gender` IN ('Female','Male'))","  CHECK (`Vehicle_Age` IN ('< 1 Year','1-2 Year','> 2 Years'))","  CHECK (`Vehicle_Damage` IN ('Yes','No'))",'  CHECK (`Age` BETWEEN 1 AND 120)','  CHECK (`Annual_Premium` >= 0)']
write('SQL/02_create_tables.sql','USE policybazaar_db;\n-- Deliberately fails if this table exists: avoid silently appending or overwriting.\nCREATE TABLE insurance_customers (\n'+',\n'.join(defs)+'\n) ENGINE=InnoDB;\n')
def literal(v):
    if isinstance(v,str): return "'"+v.replace("'","''")+"'"
    return str(int(v)) if float(v).is_integer() else str(v)
with (P/'SQL/02b_import_training_data.sql').open('w',encoding='utf-8') as f:
    f.write('-- Generated losslessly from the attached train.csv. Run after 02, exactly once.\nUSE policybazaar_db;\nSET SESSION sql_mode = \'STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION\';\nSTART TRANSACTION;\n')
    for start in range(0,n,500):
        f.write('INSERT INTO insurance_customers ('+','.join('`'+c+'`' for c in cols)+') VALUES\n')
        f.write(',\n'.join('('+','.join(literal(v) for v in row)+')' for row in original.iloc[start:start+500].itertuples(index=False,name=None))+';\n')
    f.write('COMMIT;\nSELECT COUNT(*) AS imported_rows FROM insurance_customers;\n')
agecase="CASE WHEN Age < 25 THEN 'Under 25' WHEN Age < 35 THEN '25–34' WHEN Age < 45 THEN '35–44' WHEN Age < 55 THEN '45–54' ELSE '55 and above' END"
sortcase='CASE WHEN Age < 25 THEN 1 WHEN Age < 35 THEN 2 WHEN Age < 45 THEN 3 WHEN Age < 55 THEN 4 ELSE 5 END'
views=f'''USE policybazaar_db;
CREATE OR REPLACE VIEW vw_customer_analytics AS
SELECT c.*,
 {agecase} AS Age_Group,
 {sortcase} AS Age_Group_Sort,
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
'''
write('SQL/07_create_views.sql',views)
nulls=' OR '.join('`'+c+'` IS NULL' for c in cols)
validation=f'''USE policybazaar_db;
SELECT COUNT(*) AS actual_rows, {n} AS expected_rows,
 CASE WHEN COUNT(*)={n} THEN 'PASS' ELSE 'FAIL' END AS row_count_check,
 COUNT(*)-COUNT(DISTINCT id) AS duplicate_id_count FROM insurance_customers;
SELECT COUNT(*) AS rows_with_nulls FROM insurance_customers WHERE {nulls};
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
-- Expected: {n}, {interested}, {n-interested}, {interested/n:.12f}, {premium:.2f}.
SELECT MIN(Annual_Premium) AS min_premium, MAX(Annual_Premium) AS max_premium
FROM insurance_customers;
WITH ranked AS (
 SELECT Annual_Premium, ROW_NUMBER() OVER (ORDER BY Annual_Premium) AS rn,
 COUNT(*) OVER () AS n FROM insurance_customers
)
SELECT AVG(Annual_Premium) AS median_premium FROM ranked
WHERE rn IN (FLOOR((n+1)/2), FLOOR((n+2)/2));
'''
write('SQL/03_data_validation.sql',validation)
baseagg='COUNT(*) AS Total_Customers, SUM(Response) AS Interested_Customers, SUM(Response)/NULLIF(COUNT(*),0) AS Interest_Rate'
customer='USE policybazaar_db;\n-- Run 07_create_views.sql before this analysis.\n'
for c in ['Age_Group','Gender','Previous_Insurance_Status','Vehicle_Damage_Category','Vehicle_Age','Region_Code']:
    customer+=f'SELECT {c}, {baseagg} FROM vw_customer_analytics GROUP BY {c} ORDER BY '+('MIN(Age_Group_Sort)' if c=='Age_Group' else ('MIN(Vehicle_Age_Sort)' if c=='Vehicle_Age' else c))+';\n\n'
customer+='SELECT Age_Group, Gender, Previous_Insurance_Status, Vehicle_Damage_Category, '+baseagg+' FROM vw_customer_analytics GROUP BY Age_Group, Gender, Previous_Insurance_Status, Vehicle_Damage_Category ORDER BY Interest_Rate DESC;\n'
write('SQL/04_customer_analysis.sql',customer)
ps='USE policybazaar_db;\n'
for c in ['Age_Group','Vehicle_Age','Gender','Response']:
    ps+=f'SELECT {c}, COUNT(*) AS Total_Customers, SUM(Annual_Premium) AS Total_Recorded_Annual_Premium, AVG(Annual_Premium) AS Average_Annual_Premium, MIN(Annual_Premium) AS Minimum_Premium, MAX(Annual_Premium) AS Maximum_Premium FROM vw_customer_analytics GROUP BY {c};\n\n'
ps+='-- Median is calculated in 03_data_validation.sql. Premium total is not revenue.\n'
write('SQL/05_premium_analysis.sql',ps)
write('SQL/06_sales_channel_analysis.sql','''USE policybazaar_db;
-- Codes retained; no inferred channel names or online/offline labels.
SELECT * FROM vw_channel_performance ORDER BY Interested_Customers DESC, Policy_Sales_Channel LIMIT 10;
-- 1,000 is an analyst-selected exploratory size floor, not statistical significance.
SELECT * FROM vw_channel_performance WHERE Total_Customers >= 1000
ORDER BY Interest_Rate DESC, Total_Customers DESC, Policy_Sales_Channel LIMIT 10;
SELECT * FROM vw_channel_performance ORDER BY Policy_Sales_Channel;
''')
run=['01_create_database.sql','02_create_tables.sql','02b_import_training_data.sql','07_create_views.sql','03_data_validation.sql','04_customer_analysis.sql','05_premium_analysis.sql','06_sales_channel_analysis.sql']
write('SQL/00_run_all.sql','-- Use mysql CLI from the extracted project root; SOURCE is a client command.\n'+'\n'.join('SOURCE SQL/'+s+';' for s in run)+'\n')

measures=[
 ('Total Customers','COUNTROWS(Customers)','#,0'),
 ('Interested Customers','COALESCE(CALCULATE([Total Customers], KEEPFILTERS(Customers[Response] = 1)), 0)','#,0'),
 ('Not Interested Customers','COALESCE(CALCULATE([Total Customers], KEEPFILTERS(Customers[Response] = 0)), 0)','#,0'),
 ('Interest Rate %','DIVIDE([Interested Customers], [Total Customers])','0.00%'),
 ('Total Recorded Annual Premium','SUM(Customers[Annual_Premium])','#,0.00'),
 ('Average Annual Premium','AVERAGE(Customers[Annual_Premium])','#,0.00'),
 ('Average Customer Age','AVERAGE(Customers[Age])','0.00'),
 ('Previously Insured Customers','COALESCE(CALCULATE([Total Customers], KEEPFILTERS(Customers[Previously_Insured] = 1)), 0)','#,0'),
 ('Not Previously Insured Customers','COALESCE(CALCULATE([Total Customers], KEEPFILTERS(Customers[Previously_Insured] = 0)), 0)','#,0'),
 ('Median Annual Premium','MEDIAN(Customers[Annual_Premium])','#,0.00'),
 ('Not Interested Rate %','DIVIDE([Not Interested Customers], [Total Customers])','0.00%'),
 ('Channel Sample Eligible','IF([Total Customers] >= 1000, 1, 0)','0')]
write('PowerBI/DAX_Measures.txt','// Create each measure separately with Modeling > New measure. Table name: Customers.\n// Format strings are listed as comments, not part of each formula.\n// Empty denominator: BLANK; no automatic zero percent for an empty selection.\n// KEEPFILTERS makes contradictory Response/insurance selections return zero.\n\n'+'\n\n'.join(f'// Format: {fmt}\n{name} = {expr}' for name,expr,fmt in measures)+'\n')
types=[]
textcols=['Gender','Vehicle_Age','Vehicle_Damage','Age_Group','Previous_Insurance_Status','Vehicle_Damage_Category','Interest_Status']
for c in d.columns:
    types.append('{"'+c+'", '+('type text' if c in textcols else 'Currency.Type' if c=='Annual_Premium' else 'Int64.Type')+'}')
m='''let
    ServerName = "localhost:3306",
    DatabaseName = "policybazaar_db",
    Source = MySQL.Database(ServerName, DatabaseName, [ReturnSingleDatabase=true, TreatTinyAsBoolean=false]),
    View = Source{[Schema=DatabaseName, Item="vw_customer_analytics"]}[Data],
    Typed = Table.TransformColumnTypes(View, {
        '''+',\n        '.join(types)+'''})
in
    Typed
'''
write('PowerBI/Power_Query_Scripts.txt','// Paste the entire let...in expression below into one blank query.\n// Rename the query Customers. Authenticate through the connector prompt.\n'+m)
write('PowerBI/Customers.pq',m)
theme={'name':'Insurance Analytics Navy Blue','dataColors':['#1671F3','#8DBDFA','#0B2B55','#38A3D1','#567FC4','#BBD9FB'],'background':'#F3F8FE','foreground':'#0B2B55','tableAccent':'#1671F3','textClasses':{'label':{'fontFace':'Segoe UI','fontSize':11},'title':{'fontFace':'Segoe UI Semibold','fontSize':14},'callout':{'fontFace':'Segoe UI Semibold','fontSize':28}}}
write('PowerBI/Theme.json',json.dumps(theme,indent=2))

# SQL-independent verification: same analytical equations, run in SQLite, not MySQL.
con=sqlite3.connect(':memory:');original.to_sql('insurance_customers',con,index=False)
con.executescript(views.replace('USE policybazaar_db;','').replace('CREATE OR REPLACE VIEW','CREATE VIEW'))
checks=[]
def check(name,ok,detail): checks.append({'Check':name,'Status':'PASS' if ok else 'FAIL','Evidence':detail})
check('CSV full read',len(original)==381109 and len(cols)==12,f'{n} rows, {len(cols)} columns')
check('Unique and non-null IDs',original.id.notna().all() and original.id.is_unique,'0 duplicate or missing IDs')
check('No missing fields',not original.isna().any().any(),'All twelve columns examined')
roundtrip=sqlite3.connect(':memory:')
original.iloc[:0].to_sql('insurance_customers',roundtrip,index=False)
payload=(P/'SQL/02b_import_training_data.sql').read_text()
payload='\n'.join(line for line in payload.splitlines() if not line.startswith(('USE ','SET SESSION ')))
payload=payload.replace('START TRANSACTION;','BEGIN TRANSACTION;')
roundtrip.executescript(payload)
back=pd.read_sql_query('SELECT * FROM insurance_customers ORDER BY id',roundtrip)
pd.testing.assert_frame_equal(back,original.sort_values('id').reset_index(drop=True),check_dtype=False)
check('Generated SQL payload full round-trip',True,'All 381,109 rows and 12 fields equal original after INSERT execution in SQLite; MySQL runtime untested')
roundtrip.close()
for c in ['Response','Driving_License','Previously_Insured']:
    check(c+' domain',set(original[c]) <= {0,1},str(sorted(original[c].unique())))
for c in ['Region_Code','Policy_Sales_Channel']:
    check(c+' integer-valued',(original[c]%1==0).all(),'All rows examined')
actual=pd.read_sql_query('SELECT COUNT(*) n, SUM(Response) interested, SUM(Annual_Premium) premium, AVG(Age) age FROM insurance_customers',con).iloc[0]
check('SQLite import row reconciliation',int(actual['n'])==n,'CSV -> SQLite only; MySQL remains untested')
check('Independent SQL KPI reconciliation',int(actual.interested)==interested and abs(actual.premium-premium)<.005 and abs(actual.age-d.Age.mean())<1e-9,'Pandas compared with SQLite SQL; not DAX execution')
for col,expected in groups.items():
    got=pd.read_sql_query(f'SELECT {col}, COUNT(*) Total_Customers, SUM(Response) Interested_Customers, SUM(Annual_Premium) Total_Recorded_Annual_Premium, AVG(Annual_Premium) Average_Annual_Premium, SUM(Response)*1.0/COUNT(*) Interest_Rate FROM vw_customer_analytics GROUP BY {col}',con)
    merged=expected.merge(got,on=col,suffixes=('_pd','_sql'),validate='one_to_one')
    ok=len(merged)==len(expected)
    for c in ['Total_Customers','Interested_Customers','Total_Recorded_Annual_Premium','Average_Annual_Premium','Interest_Rate']:
        ok=ok and np.allclose(merged[c+'_pd'],merged[c+'_sql'],rtol=0,atol=1e-6)
    check('Segment reconciliation: '+col,ok,f'{len(expected)} groups; counts, premiums and rates')
    check('Chart totals: '+col,int(expected.Total_Customers.sum())==n and int(expected.Interested_Customers.sum())==interested,'Additive counts sum to dataset totals; rates use weighted denominator')
for label,mask in [('Female, damage, uninsured',(d.Gender=='Female')&(d.Vehicle_Damage=='Yes')&(d.Previously_Insured==0)),('25–34, vehicle under one year',(d.Age_Group=='25–34')&(d.Vehicle_Age=='< 1 Year'))]:
    sub=d[mask]
    where="Gender='Female' AND Vehicle_Damage='Yes' AND Previously_Insured=0" if label.startswith('Female') else "Age_Group='25–34' AND Vehicle_Age='< 1 Year'"
    got=con.execute('SELECT COUNT(*), SUM(Response), AVG(Annual_Premium) FROM vw_customer_analytics WHERE '+where).fetchone()
    check('Filtered arithmetic: '+label,got[0]==len(sub) and got[1]==sub.Response.sum() and abs(got[2]-sub.Annual_Premium.mean())<1e-6,'SQL/pandas equivalence only; slicer interaction requires Power BI')
pd.DataFrame(checks).to_csv(P/'Validation/Executed_Checks.csv',index=False)
assert all(x['Status']=='PASS' for x in checks)

byage=groups['Age_Group'].sort_values('Interest_Rate',ascending=False)
bychannel=groups['Policy_Sales_Channel']; eligible=bychannel[bychannel.Total_Customers>=1000].sort_values(['Interest_Rate','Total_Customers'],ascending=False)
top=bychannel.sort_values(['Interested_Customers','Policy_Sales_Channel'],ascending=[False,True]).head(10)
insights=[f'Overall interest: {interested:,} of {n:,} customers ({interested/n:.2%}).',f'Highest age-group interest rate: {byage.iloc[0].Age_Group} ({byage.iloc[0].Interest_Rate:.2%}, n={int(byage.iloc[0].Total_Customers):,}); lowest: {byage.iloc[-1].Age_Group} ({byage.iloc[-1].Interest_Rate:.2%}, n={int(byage.iloc[-1].Total_Customers):,}).']
for col in ['Gender','Previous_Insurance_Status','Vehicle_Damage_Category','Vehicle_Age']:
    insights.append(col.replace('_',' ')+': '+'; '.join(f'{r[0]} {r[-1]:.2%} (n={int(r[1]):,})' for r in groups[col].itertuples(index=False,name=None))+'.')
insights += [f'Channel {int(top.iloc[0].Policy_Sales_Channel)} has the most interested customers: {int(top.iloc[0].Interested_Customers):,}, from {int(top.iloc[0].Total_Customers):,} customers ({top.iloc[0].Interest_Rate:.2%}).',f'Among channels with at least 1,000 customers, channel {int(eligible.iloc[0].Policy_Sales_Channel)} has the highest interest rate: {eligible.iloc[0].Interest_Rate:.2%} (n={int(eligible.iloc[0].Total_Customers):,}).',f'Recorded annual premiums total {premium:,.0f}; average {d.Annual_Premium.mean():,.2f}, median {d.Annual_Premium.median():,.0f}, range {d.Annual_Premium.min():,.0f}–{d.Annual_Premium.max():,.0f}. This total is not company revenue.',f'Age-group average premiums range from {groups["Age_Group"].Average_Annual_Premium.min():,.2f} to {groups["Age_Group"].Average_Annual_Premium.max():,.2f}; see the full segment table below.']
report='# Verified business insights\n\n'+ '\n\n'.join(f'{i+1}. {s}' for i,s in enumerate(insights))
report+='\n\n## Recommendations\n\nPrioritize testing outreach to segments with higher observed interest, especially previously uninsured customers and customers reporting vehicle damage. Compare high-volume channels against high-rate channels before allocating effort. Use the 1,000-customer floor as an exploratory screen and show denominators; it does not prove significance or business profitability. Run controlled tests before attributing differences to a channel or customer attribute. Do not exclude people solely by gender; use this field for descriptive monitoring. Premium outliers should be reviewed and retained unless verified errors.\n\nThese are descriptive associations from the supplied training sample. No causal effect, current market representativeness, actual purchase, online purchase trend, or ROI is established. No transaction dates are available.\n'
for c,x in groups.items(): report+='\n## '+c.replace('_',' ')+'\n\n'+table(x)
report+='\n## Top channels by interested count\n\n'+table(top)+'\n## Highest rates with n ≥ 1,000\n\n'+table(eligible.head(10))
write('Documentation/Business_Insights.md',report)

# High-resolution, data-based design previews. These are not Power BI screenshots.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.labelcolor':'#0B2B55','text.color':'#0B2B55','xtick.color':'#0B2B55','ytick.color':'#0B2B55','axes.spines.top':False,'axes.spines.right':False})
BLUE='#1671F3'; NAVY='#0B2B55'; LIGHT='#8DBDFA'
def scaffold(title,active,kpiitems):
    fig=plt.figure(figsize=(19.2,12),facecolor='#F3F8FE')
    fig.patches.append(Rectangle((0,0),.135,1,transform=fig.transFigure,color=NAVY))
    fig.text(.016,.975,'INSURANCE\nANALYTICS',color='white',fontsize=18,weight='bold',linespacing=1.5,va='top')
    for i,t in enumerate(['Executive\nOverview','Customer\nAnalysis','Premium &\nSales Channels']):
        y=.76-i*.13
        if i==active: fig.patches.append(Rectangle((0,y-.025),.135,.09,transform=fig.transFigure,color=BLUE))
        fig.text(.016,y,t,color='white',fontsize=12,linespacing=1.5)
    fig.text(.016,.05,'Independent\nportfolio project',color=LIGHT,fontsize=10)
    fig.text(.16,.954,title,fontsize=23,weight='bold')
    fig.text(.16,.919,'Training sample • Vehicle-insurance interest • All customers • No date trend',fontsize=11)
    fig.text(.16,.014,'DATA-BASED DESIGN PREVIEW • Static rendering, not a Power BI report • Premium currency unspecified',fontsize=10)
    for i,(label,value) in enumerate(kpiitems):
        x=.16+i*.207
        fig.patches.append(Rectangle((x,.785),.191,.105,transform=fig.transFigure,facecolor='white',edgecolor='#D2E4FA',zorder=0))
        fig.text(x+.012,.858,label,fontsize=11)
        fig.text(x+.012,.809,value,fontsize=23,weight='bold')
    return fig
def axat(fig,x,y,w,h,title):
    a=fig.add_axes([x,y,w,h],facecolor='white');a.set_title(title,loc='left',pad=16,weight='bold');a.grid(axis='y',alpha=.15);a.set_axisbelow(True);return a
def bar(fig,pos,title,frame,col,metric='Total_Customers',percent=False,order=None):
    f=frame.set_index(col)
    if order is not None:f=f.reindex(order)
    a=axat(fig,*pos,title);vals=f[metric].to_numpy();xs=np.arange(len(f));a.bar(xs,vals,color=BLUE,width=.62)
    a.set_xticks(xs,[str(int(v)) if isinstance(v,(int,float,np.integer,np.floating)) else str(v).replace('Previously Insured','Previously\nInsured').replace('Not Previously','Not Previously') for v in f.index],fontsize=9)
    if percent:a.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:.0%}'))
    else:a.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v/1000:g}k' if abs(v)>=1000 else f'{v:g}'))
    if len(vals)<=6:
        for i,v in enumerate(vals):a.text(i,v+(max(vals)*.025),f'{v:.1%}' if percent else f'{v:,.0f}',ha='center',fontsize=9)
        a.set_ylim(0,max(vals)*1.2)
    return a
kpi=[('Total Customers',f'{n:,}'),('Interested Customers',f'{interested:,}'),('Interest Rate',f'{interested/n:.2%}'),('Average Annual Premium',f'{d.Annual_Premium.mean():,.2f}')]
fig=scaffold('Insurance & Vehicle Policy Interest',0,kpi)
pos=[(.18,.465,.235,.235),(.465,.465,.225,.235),(.74,.465,.235,.235),(.18,.105,.235,.24),(.465,.105,.225,.24),(.74,.105,.235,.24)]
a=axat(fig,*pos[0],'Interested vs Not Interested');a.pie([interested,n-interested],labels=['Interested','Not Interested'],colors=[BLUE,LIGHT],autopct='%.2f%%',startangle=90,wedgeprops={'width':.38},textprops={'fontsize':10});a.text(0,0,f'{n:,}\nCustomers',ha='center',va='center')
bar(fig,pos[1],'Interested Customers by Age',groups['Age_Group'],'Age_Group','Interested_Customers',order=age_labels).tick_params(axis='x',rotation=25)
bar(fig,pos[2],'Interest Rate by Damage',groups['Vehicle_Damage_Category'],'Vehicle_Damage_Category','Interest_Rate',True).set_xticklabels(['Damage\nReported','No Damage\nReported'])
bar(fig,pos[3],'Customer Distribution by Gender',groups['Gender'],'Gender')
bar(fig,pos[4],'Previous Insurance Status',groups['Previous_Insurance_Status'],'Previous_Insurance_Status')
bar(fig,pos[5],'Interest Rate by Vehicle Age',groups['Vehicle_Age'],'Vehicle_Age','Interest_Rate',True,order=['< 1 Year','1-2 Year','> 2 Years'])
fig.text(.16,.745,f'Key insight: {interested/n:.2%} express interest. Previously uninsured customers have much higher observed interest.',fontsize=12)
fig.savefig(P/'Dashboard_Screenshots/Executive_Overview.png',dpi=130);plt.close(fig)
fig=scaffold('Customer Analysis',1,kpi)
positions=[(.18,.49,.235,.21),(.465,.49,.225,.21),(.74,.49,.235,.21),(.18,.135,.235,.21),(.465,.135,.225,.21),(.74,.135,.235,.21)]
bar(fig,positions[0],'Customers by Age Group',groups['Age_Group'],'Age_Group',order=age_labels).tick_params(axis='x',rotation=25)
bar(fig,positions[1],'Interest Rate by Age Group',groups['Age_Group'],'Age_Group','Interest_Rate',True,age_labels).tick_params(axis='x',rotation=25)
bar(fig,positions[2],'Interest Rate by Gender',groups['Gender'],'Gender','Interest_Rate',True)
bar(fig,positions[3],'Interest by Previous Insurance',groups['Previous_Insurance_Status'],'Previous_Insurance_Status','Interest_Rate',True)
bar(fig,positions[4],'Customers by Reported Damage',groups['Vehicle_Damage_Category'],'Vehicle_Damage_Category').set_xticklabels(['Damage\nReported','No Damage\nReported'])
regions=groups['Region_Code'].nlargest(10,'Total_Customers');bar(fig,positions[5],'Top 10 Regions by Customers',regions,'Region_Code').tick_params(axis='x',rotation=30)
fig.text(.16,.755,'Full segmentation and all region codes are included in the analysis tables and report specification.',fontsize=11)
fig.savefig(P/'Dashboard_Screenshots/Customer_Analysis.png',dpi=130);plt.close(fig)
fig=scaffold('Premium & Sales Channel Analysis',2,[('Total Recorded Annual Premium',f'{premium/1e9:.3f} bn'),('Average Annual Premium',f'{d.Annual_Premium.mean():,.2f}'),('Median Annual Premium',f'{d.Annual_Premium.median():,.0f}'),('Channel Codes',str(d.Policy_Sales_Channel.nunique()))])
bar(fig,positions[0],'Average Premium by Age',groups['Age_Group'],'Age_Group','Average_Annual_Premium',order=age_labels).tick_params(axis='x',rotation=25)
bar(fig,positions[1],'Average Premium by Vehicle Age',groups['Vehicle_Age'],'Vehicle_Age','Average_Annual_Premium',order=['< 1 Year','1-2 Year','> 2 Years'])
bar(fig,positions[2],'Top 10 Channels by Interest Count',top,'Policy_Sales_Channel','Interested_Customers').tick_params(axis='x',rotation=30)
bar(fig,positions[3],'Top Channel Rates (n ≥ 1,000)',eligible.head(10),'Policy_Sales_Channel','Interest_Rate',True).tick_params(axis='x',rotation=30)
a=axat(fig,*positions[4],'Annual Premium Distribution');a.hist(d.Annual_Premium,bins=50,color=BLUE);a.set_yscale('log');a.set_xlabel('Recorded annual premium');a.set_ylabel('Customer count (log scale)')
a=axat(fig,*positions[5],'Channel Detail — Top 5');a.axis('off');small=top.head(5);rows=[[str(int(r.Policy_Sales_Channel)),f'{int(r.Total_Customers):,}',f'{int(r.Interested_Customers):,}',f'{r.Interest_Rate:.1%}'] for r in small.itertuples()];tab=a.table(cellText=rows,colLabels=['Code','Customers','Interested','Rate'],loc='center',cellLoc='center');tab.auto_set_font_size(False);tab.set_fontsize(9);tab.scale(1,2)
fig.text(.16,.755,'Channel codes have no verified names. Premium total is a sum of recorded values, not marketplace revenue.',fontsize=11)
fig.savefig(P/'Dashboard_Screenshots/Premium_Channel_Analysis.png',dpi=130);plt.close(fig)

meaning=['Customer record identifier','Customer gender','Customer age in years','Driving licence indicator (1=yes)','Anonymized region identifier','Previously insured indicator (1=yes)','Vehicle-age category from source','Reported vehicle damage (Yes/No)','Recorded annual premium; currency unspecified','Anonymized policy sales-channel identifier','Customer tenure in days; not a calendar date','Vehicle-insurance interest indicator (1=interested)']
dd=pd.DataFrame({'Column':cols,'MySQL type':sqltypes,'Power BI type':['Text' if c in ['Gender','Vehicle_Age','Vehicle_Damage'] else 'Fixed decimal number' if c=='Annual_Premium' else 'Whole number' for c in cols],'Meaning':meaning})
write('Documentation/Data_Dictionary.md','# Data dictionary\n\n'+table(dd)+'\nDerived fields in the SQL view: Age_Group (Under 25, 25–34, 35–44, 45–54, 55 and above); Age_Group_Sort (1–5); Previous_Insurance_Status; Vehicle_Damage_Category; Interest_Status; Vehicle_Age_Sort (1–3). All derived fields are deterministic labels, not additional observations. Set code columns and ID to Do not summarize.\n')
write('Documentation/Project_Architecture.md','''# Project architecture

Original train.csv → MySQL policybazaar_db.insurance_customers → vw_customer_analytics → Power Query Customers (Import) → single-table semantic model → DAX measures → three Power BI pages.

One row represents one customer in the training sample. One flat table is sufficient: all requested slices are customer attributes, and there are no independent transaction tables. No relationships are needed. This avoids unnecessary joins and double counting.

vw_channel_performance is for SQL analysis only. Do not join or load its totals into the customer table; aggregating precomputed channel rates would break slicer behavior. Dashboard measures aggregate Customers directly so gender/age/region slicers recalculate both numerators and denominators.

No date table is created because no calendar date exists. Vintage cannot support monthly/annual time series. Channel codes cannot establish online purchases. The portfolio title is retained as requested, while chart titles explicitly describe insurance interest.

Executed here: complete CSV profiling, independent pandas and SQLite reconciliation, generated SQL INSERT payload, static matplotlib previews, source and archive integrity checks. Not executed here: MySQL service import, MySQL query engine, Power Query evaluation, native DAX evaluation, Power BI UI interactions. SQLite is an independent arithmetic check, not a substitute claim for MySQL validation.
''')
write('PowerBI/Report_Specification.md','''# Three-page report construction specification

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
''')

write('Documentation/Run_Instructions.md',f'''# Open and run on Windows

## What is delivered

This package is a validated data analysis plus SQL/Power BI construction kit. It contains no native .pbix or .pbip and no functioning native report. Power BI Desktop and MySQL were unavailable in the execution environment. Do not rename the scripts or previews to .pbix. The nearest supported artifacts are executable SQL data import, reusable Power Query M, DAX, a theme, detailed visual field mappings, expected results, and three design previews.

## 1. Extract and open the files

Extract the ZIP into a simple path, for example C:\\InsuranceProject. Open the inner Policybazaar_Insurance_Analytics folder. Keep Dataset, SQL, PowerBI, Documentation and Validation together. Open README.md in a text editor or Markdown viewer. The SQL importer already contains the exact original training rows; it does not need LOAD DATA settings, CSV import wizards or a Python installation.

## 2. Start MySQL and confirm the connection

Start your installed MySQL service using Windows Services. Open Workbench and confirm you can connect to localhost:3306 with your own user and password. Resolve any existing “Access denied” error first; this package cannot reset your local root password. Never paste your password into these scripts or GitHub.

## 3. Import and validate

Recommended: open **Command Prompt**, change directory to the extracted project root (the folder containing SQL), and run:

```bat
cd /d C:\\InsuranceProject\\Policybazaar_Insurance_Analytics
mysql --default-character-set=utf8mb4 -h localhost -P 3306 -u root -p < SQL\\00_run_all.sql > mysql_validation_output.txt 2> mysql_errors.txt
```

The mysql client must be on PATH. Otherwise replace `mysql` with the quoted full path to mysql.exe inside your installed MySQL Server bin folder. The `-p` option prompts privately for your password. SOURCE paths are relative to the current directory. Do not use --force. Read mysql_errors.txt before accepting the output: an earlier error may leave later validation sections present. This command is for cmd.exe; PowerShell does not support this input-redirection syntax in the same way.

Workbench alternative: File → Open SQL Script. Run these files in order, using the lightning-bolt “execute all” action: 01, 02, 02b, 07, 03, 04, 05, 06. The 02b file is large; allow it to finish. 00_run_all.sql uses the CLI SOURCE command and is not the Workbench route. The table creation intentionally fails if the table already exists. On rerun, inspect the existing table; do not execute the importer twice. If the correct data is already loaded, run only 07,03,04,05,06. Any replace/delete of your existing data requires a deliberate local decision.

Expected full-sample controls:

- Rows: {n:,}; interested: {interested:,}; not interested: {n-interested:,}.
- Interest rate: {interested/n:.10%}.
- Total recorded annual premium: {premium:,.2f}.
- Average annual premium: {d.Annual_Premium.mean():,.8f}.
- Median annual premium: {d.Annual_Premium.median():,.2f}.
- Missing records/duplicate IDs: zero.

If a check differs, stop and inspect the import and error log before connecting Power BI. The data import uses strict SQL mode and an explicit transaction. The exact original CSV remains unchanged in Dataset/train.csv.

## 4. Load the view into Power BI

Use Power BI Desktop on Windows. Get Data → MySQL database → server localhost:3306, database policybazaar_db. Use Import mode and your database credentials. If Desktop requests a MySQL provider, install the provider/version specified by Microsoft's current connector documentation for your Desktop architecture, then restart Desktop. Do not guess a version based on this package.

Select vw_customer_analytics and Transform Data. Alternatively create a blank query, open Advanced Editor and paste the let...in expression in PowerBI/Customers.pq; update ServerName if necessary. In Navigator, the connector's item keys may vary; if direct view navigation errors, select the view through Navigator and retain the supplied type-conversion step. Rename the final query **Customers**. Use only this customer-grain view for reporting; do not load channel summary rows into the same model. Close & Apply.

In Data/Model view: set ID, region and channel codes plus all 0/1 flags to Do not summarize. Set Annual_Premium to fixed decimal. Set Age_Group to Sort by column Age_Group_Sort and Vehicle_Age to Vehicle_Age_Sort; hide the sort columns from report view. These sorts are safe because each category maps to exactly one sort value. No relationships are required.

## 5. Add DAX and design the three pages

Open PowerBI/DAX_Measures.txt. Modeling → New measure; paste **one** measure at a time into Customers, using the specified format. Rate measures are fractions formatted as percentages, not multiplied by 100. Import PowerBI/Theme.json through the theme import command (Design → Import theme in current builds; older builds may expose this under View → Themes).

Build the three pages following PowerBI/Report_Specification.md. Its field mappings include the full set of visuals, seven synced slicers, tooltips and page navigation. The PNGs give style guidance; they are not imported visuals and do not implement filters. Compare unfiltered cards against Expected_KPIs.json and groups against the expected CSVs. Complete the local acceptance checklist, then File → Save As → Policybazaar_Insurance_Analytics.pbix. Reopen that file and refresh to confirm the MySQL connection works. Export real report screenshots after validation.

## 6. Optional reproducibility

Scripts/reproduce_analysis.py recreates the Python outputs if pandas, numpy and matplotlib are available. From the extracted project root: `python Scripts/reproduce_analysis.py`. It does not start MySQL, run DAX or build a native Power BI report. The builder outputs SQL, data checks, documents and static previews. Keep the source archive as the original input, and do not modify train.csv to force expected results.

## 7. Portfolio publishing

Use README.md and Documentation/Interview_Explanation.md. Keep dataset attribution. Review Kaggle's source terms before redistributing the raw dataset in a public GitHub repository; a private working copy is included here. Add your tested .pbix and actual report screenshots only after local completion. Describe this as a project in progress until the native report and integrations are validated. No claim of confirmed purchases, real Policybazaar revenue or time trends is supported.
''')

qa='# Validation report\n\n'+table(pd.DataFrame(checks))
qa+='\n## Not executed / local acceptance required\n\n| Check | Status | Reason / next action |\n| --- | --- | --- |\n| MySQL import and row count | NOT TESTED | No MySQL server; run SQL/00_run_all.sql locally and inspect logs |\n| MySQL syntax/runtime and constraints | NOT TESTED | MySQL SQL supplied; independent SQLite checks do not validate MySQL runtime |\n| Power Query MySQL connector | NOT TESTED | Requires your Windows provider and credentials |\n| Native DAX evaluation | NOT TESTED | Arithmetic definitions reconciled with SQL/pandas; no DAX engine available |\n| Native report visuals and totals | NOT TESTED | Build from specification; compare Expected_KPIs.json and expected CSVs |\n| Slicers, cross-filtering and navigator | NOT TESTED | Power BI UI required |\n| Theme import | NOT TESTED | Valid JSON, but native import still needed |\n| Native .pbix/.pbip open/refresh | NOT CREATED | No supported native authoring/runtime available here |\n\nPreviews are rendered from real full-sample data. They are not native report screenshots and cover representative charts rather than every specified visual. Static insights do not change with filters; their full-sample scope must remain labelled.\n'
write('Documentation/Validation_Report.md',qa)

questions=[('Why use MySQL with Power BI?','MySQL stores the source records and views standardize reusable labels. Power BI imports the view, calculates filter-aware measures and presents the analysis.'),('Why a view?','It saves a reusable SELECT definition, such as age grouping. A regular view does not separately store a refreshed copy of the results.'),('Why not call Response a conversion?','It records expressed interest in vehicle insurance. It does not confirm a completed purchase.'),('Why a single table?','Each row represents one customer and all slices are attributes of that customer. Extra fact tables or relationships would add complexity without new information.'),('How is the interest rate calculated?','Interested customers divided by all customers in the same filter context. The grand total is the ratio of totals, not the average of segment percentages.'),('What do CALCULATE and KEEPFILTERS do?','CALCULATE changes filter context. KEEPFILTERS intersects the interested-customer condition with existing selections instead of replacing a selection on the same column.'),('Why use DIVIDE?','It safely returns blank for an empty denominator unless an alternate result is specified.'),('What is Power Query versus DAX?','Power Query prepares and types data at refresh. DAX measures calculate results when report filters change.'),('Why not show monthly sales?','There is no transaction date or confirmed sale. Vintage is tenure in days, so it cannot establish calendar trends.'),('How did you handle missing values and outliers?','The supplied training file has no missing fields. Premium extremes and repeated low premiums are documented and retained because no evidence establishes they are errors.'),('What does a high channel rate mean?','A high share of customers in that coded channel expressed interest. Sample size and customer mix matter; the result is descriptive and does not prove channel causation or profitability.'),('What was actually tested here?','All training records were profiled. Counts, premiums and group rates were cross-checked in pandas and SQLite. MySQL, native DAX and report interactions still require local validation.')]
interview='''# Interview and portfolio preparation

## Short summary

An independent insurance cross-sell analytics project using a Kaggle training dataset, MySQL SQL views, Power Query and DAX. It examines customer profiles, recorded annual premiums and vehicle-insurance interest by anonymized channel code. The source is not verified Policybazaar internal data.

## 60-second explanation — use after completing the local report

“My project is Policybazaar – Insurance & Online Policy Purchase Trends. It is an independent portfolio project inspired by an insurance marketplace. I used a public insurance cross-sell dataset with 381,109 customer records. I stored the records in MySQL, checked data quality and created SQL views for customer segments. I connected those views to Power BI, used Power Query to set data types, and created DAX measures for customer counts, interest rate and premiums. The report has three pages covering customer profiles, premiums and sales-channel codes. Around 12.26% of customers expressed interest in vehicle insurance. I was careful to describe this as interest because the data does not confirm a purchase. I also compared the report totals with SQL to check accuracy.”

Do not use the completed-report claims above until you have connected MySQL, built and validated the native Power BI report. Until then say “I have completed the analysis and prepared the SQL and report setup files; I am implementing the native report locally.”

## Detailed technical explanation

The raw CSV is preserved. Each record has a unique customer ID. SQL stores binary indicators as integers, premium as DECIMAL and region/channel values as identifiers. A reusable SQL view adds fixed age groups, clear labels and sort keys. Power Query imports this view as Customers. The model uses one customer-grain table with no unnecessary relationships. Measures use COUNTROWS, CALCULATE, KEEPFILTERS, DIVIDE, SUM, AVERAGE and MEDIAN. Slicers filter the same customer table, so the rate uses the selected population as its denominator. Separate SQL summary queries audit the values. Premium totals represent recorded annual-premium amounts and not revenue.

## SQL concepts demonstrated

Database/table creation, primary keys, NOT NULL, CHECK constraints, fixed decimal types, transactional bulk INSERT, CASE, GROUP BY, conditional labels, aggregates, NULLIF, reusable views, ordering, LIMIT, a median calculation using ROW_NUMBER and COUNT window functions, and independent reconciliation.

## DAX concepts demonstrated

Filter context, measures versus source columns, CALCULATE, KEEPFILTERS, COUNTROWS, COALESCE, DIVIDE, SUM, AVERAGE, MEDIAN, conditional sample-size filtering, and ratio-of-totals aggregation.

## Common interview questions

'''
interview+='\n\n'.join('**'+q+'**\n\n'+a for q,a in questions)
interview+='\n\n## Resume bullets — use after local implementation and validation\n\n- Built a three-page insurance analytics report using MySQL and Power BI to analyze 381,109 customer records, annual premiums and vehicle-insurance interest.\n- Created reusable SQL views and DAX measures to compare customer segments and coded sales channels, and checked report totals against SQL results.\n\nCurrent truthful alternative: “Profiled 381,109 insurance customer records and prepared reusable MySQL scripts, DAX measures and a three-page Power BI report specification.”\n\nFor verified findings, use Business_Insights.md. Avoid unsupported improvement percentages or claims that the project increased sales.\n'
write('Documentation/Interview_Explanation.md',interview)
readme=f'''# Policybazaar – Insurance & Online Policy Purchase Trends

Independent portfolio project by Gayatri Deshmukh. This project is inspired by an insurance marketplace and uses a public insurance cross-sell training dataset, not verified internal Policybazaar data.

**Delivery status:** data analysis, SQL data-loading scripts, Power Query, DAX, theme, report specifications and static previews are supplied. MySQL integration and a native Power BI report require local execution. No .pbix/.pbip is included or claimed functional.

## What the data supports

Vehicle-insurance interest by customer profile, recorded annual-premium distributions and anonymized sales-channel codes. It does not establish actual purchases, online/offline channel names, Policybazaar revenue, ROI or calendar trends.

| Metric | Full training sample |
| --- | ---: |
| Customers | {n:,} |
| Interested customers | {interested:,} |
| Interest rate | {interested/n:.2%} |
| Average recorded annual premium | {d.Annual_Premium.mean():,.2f} |
| Median recorded annual premium | {d.Annual_Premium.median():,.0f} |

Premium currency is unspecified. Response=1 means expressed interest, not sale.

## Architecture

CSV → MySQL → SQL views → Power Query → customer-grain model → DAX → three report pages.

## Start here

1. Read [Run instructions](Documentation/Run_Instructions.md).
2. Import the data and run checks using SQL/00_run_all.sql in the MySQL command-line client, or run its component scripts in Workbench.
3. Load PowerBI/Customers.pq into Desktop as Customers and add the individual measures in PowerBI/DAX_Measures.txt.
4. Import PowerBI/Theme.json; build the visuals using PowerBI/Report_Specification.md.
5. Complete the [Validation report](Documentation/Validation_Report.md) local acceptance checks, save the .pbix and export actual screenshots.

## Contents

- Dataset/train.csv: unchanged original training file.
- SQL/: schema, executable INSERT data, validation, analysis and views.
- PowerBI/: Power Query M, DAX definitions, theme and exact report construction specification.
- Dashboard_Screenshots/: three data-based design previews, not native Power BI screenshots.
- Documentation/: complete profile, dictionary, architecture, verified business findings, run instructions, validation and interview preparation.
- Validation/: expected KPIs, category results and executed check evidence.
- Scripts/reproduce_analysis.py: reproducible analysis and artifact builder.

## Preview — static, not an interactive report

![Executive overview design preview](Dashboard_Screenshots/Executive_Overview.png)
![Customer analysis design preview](Dashboard_Screenshots/Customer_Analysis.png)
![Premium and channel analysis design preview](Dashboard_Screenshots/Premium_Channel_Analysis.png)

## Findings and quality assurance

See [Business insights](Documentation/Business_Insights.md). All supplied rows were read; there are no missing fields or duplicate IDs. Independent pandas/SQLite checks reconcile KPI values and segment calculations. This is not evidence that native MySQL, DAX or report UI tests passed; those remain explicitly untested.

## Sources

- Dataset source provided by the user: https://www.kaggle.com/datasets/anmolkumar/health-insurance-cross-sell-prediction
- Microsoft MySQL Power Query connector: https://learn.microsoft.com/en-us/power-query/connectors/mysql-database
- Microsoft MySQL.Database M reference: https://learn.microsoft.com/en-us/powerquery-m/mysql-database
- Microsoft report themes: https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-report-themes
- MySQL LOAD DATA reference (not required by the supplied INSERT importer): https://dev.mysql.com/doc/refman/8.0/en/load-data.html

The user-supplied ZIP is the analysis input. The Kaggle page supplied no readable body in this environment, so a specific source currency or redistribution licence is not asserted. Check source terms before publicly redistributing the raw dataset.
'''
write('README.md',readme)

# Keep the exact source of this build with the output for reproducibility.
this=Path(__file__).resolve()
dest=P/'Scripts/reproduce_analysis.py'
if this!=dest:
    source=this.read_text().replace("ROOT=Path(__file__).resolve().parent\nP=ROOT/'Policybazaar_Insurance_Analytics'","P=Path(__file__).resolve().parents[1]\nROOT=P.parent")
    dest.write_text(source,encoding='utf-8')

manifest=[]
for f in sorted(P.rglob('*')):
    if f.is_file() and f.name!='MANIFEST_SHA256.txt':
        manifest.append(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(P).as_posix())
write('MANIFEST_SHA256.txt','\n'.join(manifest)+'\n')
archive=ROOT/'Policybazaar_Insurance_Analytics.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in sorted(P.rglob('*')):
        if f.is_file():z.write(f,f.relative_to(ROOT))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read('Policybazaar_Insurance_Analytics/Dataset/train.csv')).hexdigest()==sha
print(json.dumps({'KPIs':kpis,'executed_checks':len(checks),'all_checks_pass':all(x['Status']=='PASS' for x in checks),'files':len(list(P.rglob('*'))),'zip_bytes':archive.stat().st_size,'insights':insights},indent=2))
