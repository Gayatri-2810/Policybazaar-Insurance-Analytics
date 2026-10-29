USE policybazaar_db;
-- Deliberately fails if this table exists: avoid silently appending or overwriting.
CREATE TABLE insurance_customers (
  `id` INT UNSIGNED NOT NULL PRIMARY KEY,
  `Gender` VARCHAR(10) NOT NULL,
  `Age` TINYINT UNSIGNED NOT NULL,
  `Driving_License` TINYINT UNSIGNED NOT NULL,
  `Region_Code` SMALLINT UNSIGNED NOT NULL,
  `Previously_Insured` TINYINT UNSIGNED NOT NULL,
  `Vehicle_Age` VARCHAR(15) NOT NULL,
  `Vehicle_Damage` VARCHAR(3) NOT NULL,
  `Annual_Premium` DECIMAL(12,2) NOT NULL,
  `Policy_Sales_Channel` SMALLINT UNSIGNED NOT NULL,
  `Vintage` SMALLINT UNSIGNED NOT NULL,
  `Response` TINYINT UNSIGNED NOT NULL,
  CHECK (`Response` IN (0,1)),
  CHECK (`Driving_License` IN (0,1)),
  CHECK (`Previously_Insured` IN (0,1)),
  CHECK (`Gender` IN ('Female','Male')),
  CHECK (`Vehicle_Age` IN ('< 1 Year','1-2 Year','> 2 Years')),
  CHECK (`Vehicle_Damage` IN ('Yes','No')),
  CHECK (`Age` BETWEEN 1 AND 120),
  CHECK (`Annual_Premium` >= 0)
) ENGINE=InnoDB;
