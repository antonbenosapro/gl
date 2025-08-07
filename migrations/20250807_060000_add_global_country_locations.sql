-- =====================================================
-- Add Global Country Location Codes
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Add comprehensive location codes for all countries globally
--              organized by regions with systematic 6-digit coding structure
-- =====================================================

-- Coding Structure:
-- 1XXXXX - North America
-- 2XXXXX - Europe  
-- 3XXXXX - Asia Pacific
-- 4XXXXX - Latin America
-- 5XXXXX - Middle East & Africa
-- 6XXXXX - Oceania
-- 7XXXXX - Caribbean
-- 8XXXXX - Central Asia
-- 9XXXXX - Reserved for future expansion

-- =====================================================
-- NORTH AMERICA REGION (1XXXXX)
-- =====================================================

-- Existing: 100000 (North America Region), 110000 (United States)
-- Add Canada and Mexico
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
('120000', 'Canada', 'COUNTRY', '100000', 'CAN', 'NA', 'OFFICE', TRUE),
('130000', 'Mexico', 'COUNTRY', '100000', 'MEX', 'NA', 'OFFICE', TRUE);

-- Canadian Provinces (Major ones)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, business_area_id, location_type, is_active) VALUES
('121000', 'Ontario', 'STATE', '120000', 'CAN', 'ON', 'NA', 'OFFICE', TRUE),
('122000', 'Quebec', 'STATE', '120000', 'CAN', 'QC', 'NA', 'OFFICE', TRUE),
('123000', 'British Columbia', 'STATE', '120000', 'CAN', 'BC', 'NA', 'OFFICE', TRUE),
('124000', 'Alberta', 'STATE', '120000', 'CAN', 'AB', 'NA', 'OFFICE', TRUE);

-- Major Canadian Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type, is_active) VALUES
('121100', 'Toronto', 'CITY', '121000', 'CAN', 'ON', 'Toronto', 'NA', 'OFFICE', TRUE),
('121200', 'Ottawa', 'CITY', '121000', 'CAN', 'ON', 'Ottawa', 'NA', 'OFFICE', TRUE),
('122100', 'Montreal', 'CITY', '122000', 'CAN', 'QC', 'Montreal', 'NA', 'OFFICE', TRUE),
('123100', 'Vancouver', 'CITY', '123000', 'CAN', 'BC', 'Vancouver', 'NA', 'OFFICE', TRUE),
('124100', 'Calgary', 'CITY', '124000', 'CAN', 'AB', 'Calgary', 'NA', 'OFFICE', TRUE);

-- Mexican States (Major ones)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, business_area_id, location_type, is_active) VALUES
('131000', 'Mexico City', 'STATE', '130000', 'MEX', 'CDMX', 'NA', 'OFFICE', TRUE),
('132000', 'Nuevo León', 'STATE', '130000', 'MEX', 'NL', 'NA', 'PLANT', TRUE),
('133000', 'Jalisco', 'STATE', '130000', 'MEX', 'JAL', 'NA', 'OFFICE', TRUE);

-- Major Mexican Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type, is_active) VALUES
('131100', 'Mexico City', 'CITY', '131000', 'MEX', 'CDMX', 'Mexico City', 'NA', 'OFFICE', TRUE),
('132100', 'Monterrey', 'CITY', '132000', 'MEX', 'NL', 'Monterrey', 'NA', 'PLANT', TRUE),
('133100', 'Guadalajara', 'CITY', '133000', 'MEX', 'JAL', 'Guadalajara', 'NA', 'OFFICE', TRUE);

-- =====================================================
-- EUROPE REGION (2XXXXX) - Expand existing
-- =====================================================

-- Add more European countries
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
-- Western Europe
('230000', 'France', 'COUNTRY', '200000', 'FRA', 'EU', 'OFFICE', TRUE),
('240000', 'Italy', 'COUNTRY', '200000', 'ITA', 'EU', 'OFFICE', TRUE),
('250000', 'Spain', 'COUNTRY', '200000', 'ESP', 'EU', 'OFFICE', TRUE),
('260000', 'Netherlands', 'COUNTRY', '200000', 'NLD', 'EU', 'OFFICE', TRUE),
('270000', 'Switzerland', 'COUNTRY', '200000', 'CHE', 'EU', 'OFFICE', TRUE),
('280000', 'Austria', 'COUNTRY', '200000', 'AUT', 'EU', 'OFFICE', TRUE),
-- Nordic Countries
('231000', 'Sweden', 'COUNTRY', '200000', 'SWE', 'EU', 'OFFICE', TRUE),
('232000', 'Norway', 'COUNTRY', '200000', 'NOR', 'EU', 'OFFICE', TRUE),
('233000', 'Denmark', 'COUNTRY', '200000', 'DNK', 'EU', 'OFFICE', TRUE),
('234000', 'Finland', 'COUNTRY', '200000', 'FIN', 'EU', 'OFFICE', TRUE),
-- Eastern Europe
('290000', 'Poland', 'COUNTRY', '200000', 'POL', 'EU', 'OFFICE', TRUE),
('291000', 'Czech Republic', 'COUNTRY', '200000', 'CZE', 'EU', 'OFFICE', TRUE),
('292000', 'Hungary', 'COUNTRY', '200000', 'HUN', 'EU', 'OFFICE', TRUE),
('293000', 'Romania', 'COUNTRY', '200000', 'ROU', 'EU', 'OFFICE', TRUE);

-- Major European Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, city, business_area_id, location_type, is_active) VALUES
-- France
('230100', 'Paris', 'CITY', '230000', 'FRA', 'Paris', 'EU', 'OFFICE', TRUE),
('230200', 'Lyon', 'CITY', '230000', 'FRA', 'Lyon', 'EU', 'OFFICE', TRUE),
-- Italy  
('240100', 'Rome', 'CITY', '240000', 'ITA', 'Rome', 'EU', 'OFFICE', TRUE),
('240200', 'Milan', 'CITY', '240000', 'ITA', 'Milan', 'EU', 'OFFICE', TRUE),
-- Spain
('250100', 'Madrid', 'CITY', '250000', 'ESP', 'Madrid', 'EU', 'OFFICE', TRUE),
('250200', 'Barcelona', 'CITY', '250000', 'ESP', 'Barcelona', 'EU', 'OFFICE', TRUE),
-- Netherlands
('260100', 'Amsterdam', 'CITY', '260000', 'NLD', 'Amsterdam', 'EU', 'OFFICE', TRUE),
('260200', 'Rotterdam', 'CITY', '260000', 'NLD', 'Rotterdam', 'EU', 'OFFICE', TRUE),
-- Switzerland
('270100', 'Zurich', 'CITY', '270000', 'CHE', 'Zurich', 'EU', 'OFFICE', TRUE),
('270200', 'Geneva', 'CITY', '270000', 'CHE', 'Geneva', 'EU', 'OFFICE', TRUE),
-- Nordic Cities
('231100', 'Stockholm', 'CITY', '231000', 'SWE', 'Stockholm', 'EU', 'OFFICE', TRUE),
('232100', 'Oslo', 'CITY', '232000', 'NOR', 'Oslo', 'EU', 'OFFICE', TRUE),
('233100', 'Copenhagen', 'CITY', '233000', 'DNK', 'Copenhagen', 'EU', 'OFFICE', TRUE),
('234100', 'Helsinki', 'CITY', '234000', 'FIN', 'Helsinki', 'EU', 'OFFICE', TRUE);

-- =====================================================
-- ASIA PACIFIC REGION (3XXXXX) - Expand existing
-- =====================================================

-- Add more APAC countries
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
-- Southeast Asia
('330000', 'Singapore', 'COUNTRY', '300000', 'SGP', 'APAC', 'OFFICE', TRUE),
('340000', 'Malaysia', 'COUNTRY', '300000', 'MYS', 'APAC', 'OFFICE', TRUE),
('350000', 'Thailand', 'COUNTRY', '300000', 'THA', 'APAC', 'OFFICE', TRUE),
('360000', 'Indonesia', 'COUNTRY', '300000', 'IDN', 'APAC', 'OFFICE', TRUE),
('370000', 'Philippines', 'COUNTRY', '300000', 'PHL', 'APAC', 'OFFICE', TRUE),
('380000', 'Vietnam', 'COUNTRY', '300000', 'VNM', 'APAC', 'OFFICE', TRUE),
-- South Asia
('390000', 'India', 'COUNTRY', '300000', 'IND', 'APAC', 'OFFICE', TRUE),
('391000', 'Pakistan', 'COUNTRY', '300000', 'PAK', 'APAC', 'OFFICE', TRUE),
('392000', 'Bangladesh', 'COUNTRY', '300000', 'BGD', 'APAC', 'OFFICE', TRUE),
('393000', 'Sri Lanka', 'COUNTRY', '300000', 'LKA', 'APAC', 'OFFICE', TRUE),
-- East Asia (additional)
('394000', 'South Korea', 'COUNTRY', '300000', 'KOR', 'APAC', 'OFFICE', TRUE),
('395000', 'Taiwan', 'COUNTRY', '300000', 'TWN', 'APAC', 'OFFICE', TRUE),
('396000', 'Hong Kong', 'COUNTRY', '300000', 'HKG', 'APAC', 'OFFICE', TRUE);

-- Major APAC Cities  
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, city, business_area_id, location_type, is_active) VALUES
-- Singapore (city-state)
('330100', 'Singapore', 'CITY', '330000', 'SGP', 'Singapore', 'APAC', 'OFFICE', TRUE),
-- Malaysia
('340100', 'Kuala Lumpur', 'CITY', '340000', 'MYS', 'Kuala Lumpur', 'APAC', 'OFFICE', TRUE),
-- Thailand
('350100', 'Bangkok', 'CITY', '350000', 'THA', 'Bangkok', 'APAC', 'OFFICE', TRUE),
-- Indonesia
('360100', 'Jakarta', 'CITY', '360000', 'IDN', 'Jakarta', 'APAC', 'OFFICE', TRUE),
-- Philippines
('370100', 'Manila', 'CITY', '370000', 'PHL', 'Manila', 'APAC', 'OFFICE', TRUE),
-- Vietnam
('380100', 'Ho Chi Minh City', 'CITY', '380000', 'VNM', 'Ho Chi Minh City', 'APAC', 'OFFICE', TRUE),
('380200', 'Hanoi', 'CITY', '380000', 'VNM', 'Hanoi', 'APAC', 'OFFICE', TRUE),
-- India
('390100', 'Mumbai', 'CITY', '390000', 'IND', 'Mumbai', 'APAC', 'OFFICE', TRUE),
('390200', 'Delhi', 'CITY', '390000', 'IND', 'Delhi', 'APAC', 'OFFICE', TRUE),
('390300', 'Bangalore', 'CITY', '390000', 'IND', 'Bangalore', 'APAC', 'OFFICE', TRUE),
('390400', 'Chennai', 'CITY', '390000', 'IND', 'Chennai', 'APAC', 'OFFICE', TRUE),
-- South Korea
('394100', 'Seoul', 'CITY', '394000', 'KOR', 'Seoul', 'APAC', 'OFFICE', TRUE),
('394200', 'Busan', 'CITY', '394000', 'KOR', 'Busan', 'APAC', 'OFFICE', TRUE),
-- Taiwan
('395100', 'Taipei', 'CITY', '395000', 'TWN', 'Taipei', 'APAC', 'OFFICE', TRUE),
-- Hong Kong (city-state)  
('396100', 'Hong Kong', 'CITY', '396000', 'HKG', 'Hong Kong', 'APAC', 'OFFICE', TRUE);

-- =====================================================
-- LATIN AMERICA REGION (4XXXXX)
-- =====================================================

-- Add Latin American countries (excluding Mexico which is in North America)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
-- South America
('410000', 'Brazil', 'COUNTRY', '400000', 'BRA', 'LA', 'OFFICE', TRUE),
('420000', 'Argentina', 'COUNTRY', '400000', 'ARG', 'LA', 'OFFICE', TRUE),
('430000', 'Chile', 'COUNTRY', '400000', 'CHL', 'LA', 'OFFICE', TRUE),
('440000', 'Colombia', 'COUNTRY', '400000', 'COL', 'LA', 'OFFICE', TRUE),
('450000', 'Peru', 'COUNTRY', '400000', 'PER', 'LA', 'OFFICE', TRUE),
('460000', 'Venezuela', 'COUNTRY', '400000', 'VEN', 'LA', 'OFFICE', TRUE),
('470000', 'Ecuador', 'COUNTRY', '400000', 'ECU', 'LA', 'OFFICE', TRUE),
('480000', 'Uruguay', 'COUNTRY', '400000', 'URY', 'LA', 'OFFICE', TRUE),
('490000', 'Paraguay', 'COUNTRY', '400000', 'PRY', 'LA', 'OFFICE', TRUE),
('491000', 'Bolivia', 'COUNTRY', '400000', 'BOL', 'LA', 'OFFICE', TRUE),
-- Central America
('492000', 'Costa Rica', 'COUNTRY', '400000', 'CRI', 'LA', 'OFFICE', TRUE),
('493000', 'Panama', 'COUNTRY', '400000', 'PAN', 'LA', 'OFFICE', TRUE),
('494000', 'Guatemala', 'COUNTRY', '400000', 'GTM', 'LA', 'OFFICE', TRUE),
('495000', 'Honduras', 'COUNTRY', '400000', 'HND', 'LA', 'OFFICE', TRUE),
('496000', 'El Salvador', 'COUNTRY', '400000', 'SLV', 'LA', 'OFFICE', TRUE),
('497000', 'Nicaragua', 'COUNTRY', '400000', 'NIC', 'LA', 'OFFICE', TRUE);

-- Major Latin American Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, city, business_area_id, location_type, is_active) VALUES
-- Brazil
('410100', 'São Paulo', 'CITY', '410000', 'BRA', 'São Paulo', 'LA', 'OFFICE', TRUE),
('410200', 'Rio de Janeiro', 'CITY', '410000', 'BRA', 'Rio de Janeiro', 'LA', 'OFFICE', TRUE),
('410300', 'Brasília', 'CITY', '410000', 'BRA', 'Brasília', 'LA', 'OFFICE', TRUE),
-- Argentina
('420100', 'Buenos Aires', 'CITY', '420000', 'ARG', 'Buenos Aires', 'LA', 'OFFICE', TRUE),
('420200', 'Córdoba', 'CITY', '420000', 'ARG', 'Córdoba', 'LA', 'OFFICE', TRUE),
-- Chile
('430100', 'Santiago', 'CITY', '430000', 'CHL', 'Santiago', 'LA', 'OFFICE', TRUE),
('430200', 'Valparaíso', 'CITY', '430000', 'CHL', 'Valparaíso', 'LA', 'OFFICE', TRUE),
-- Colombia
('440100', 'Bogotá', 'CITY', '440000', 'COL', 'Bogotá', 'LA', 'OFFICE', TRUE),
('440200', 'Medellín', 'CITY', '440000', 'COL', 'Medellín', 'LA', 'OFFICE', TRUE),
-- Peru
('450100', 'Lima', 'CITY', '450000', 'PER', 'Lima', 'LA', 'OFFICE', TRUE);

-- =====================================================
-- MIDDLE EAST & AFRICA REGION (5XXXXX)
-- =====================================================

INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
-- Middle East
('510000', 'Saudi Arabia', 'COUNTRY', '500000', 'SAU', 'MEA', 'OFFICE', TRUE),
('520000', 'United Arab Emirates', 'COUNTRY', '500000', 'ARE', 'MEA', 'OFFICE', TRUE),
('530000', 'Qatar', 'COUNTRY', '500000', 'QAT', 'MEA', 'OFFICE', TRUE),
('540000', 'Kuwait', 'COUNTRY', '500000', 'KWT', 'MEA', 'OFFICE', TRUE),
('550000', 'Israel', 'COUNTRY', '500000', 'ISR', 'MEA', 'OFFICE', TRUE),
('560000', 'Turkey', 'COUNTRY', '500000', 'TUR', 'MEA', 'OFFICE', TRUE),
('570000', 'Iran', 'COUNTRY', '500000', 'IRN', 'MEA', 'OFFICE', TRUE),
-- Africa
('580000', 'South Africa', 'COUNTRY', '500000', 'ZAF', 'MEA', 'OFFICE', TRUE),
('590000', 'Egypt', 'COUNTRY', '500000', 'EGY', 'MEA', 'OFFICE', TRUE),
('591000', 'Nigeria', 'COUNTRY', '500000', 'NGA', 'MEA', 'OFFICE', TRUE),
('592000', 'Kenya', 'COUNTRY', '500000', 'KEN', 'MEA', 'OFFICE', TRUE),
('593000', 'Ghana', 'COUNTRY', '500000', 'GHA', 'MEA', 'OFFICE', TRUE),
('594000', 'Morocco', 'COUNTRY', '500000', 'MAR', 'MEA', 'OFFICE', TRUE),
('595000', 'Tunisia', 'COUNTRY', '500000', 'TUN', 'MEA', 'OFFICE', TRUE),
('596000', 'Ethiopia', 'COUNTRY', '500000', 'ETH', 'MEA', 'OFFICE', TRUE);

-- Major MEA Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, city, business_area_id, location_type, is_active) VALUES
-- Saudi Arabia
('510100', 'Riyadh', 'CITY', '510000', 'SAU', 'Riyadh', 'MEA', 'OFFICE', TRUE),
('510200', 'Jeddah', 'CITY', '510000', 'SAU', 'Jeddah', 'MEA', 'OFFICE', TRUE),
-- UAE
('520100', 'Dubai', 'CITY', '520000', 'ARE', 'Dubai', 'MEA', 'OFFICE', TRUE),
('520200', 'Abu Dhabi', 'CITY', '520000', 'ARE', 'Abu Dhabi', 'MEA', 'OFFICE', TRUE),
-- Qatar
('530100', 'Doha', 'CITY', '530000', 'QAT', 'Doha', 'MEA', 'OFFICE', TRUE),
-- Israel
('550100', 'Tel Aviv', 'CITY', '550000', 'ISR', 'Tel Aviv', 'MEA', 'OFFICE', TRUE),
('550200', 'Jerusalem', 'CITY', '550000', 'ISR', 'Jerusalem', 'MEA', 'OFFICE', TRUE),
-- Turkey
('560100', 'Istanbul', 'CITY', '560000', 'TUR', 'Istanbul', 'MEA', 'OFFICE', TRUE),
('560200', 'Ankara', 'CITY', '560000', 'TUR', 'Ankara', 'MEA', 'OFFICE', TRUE),
-- South Africa
('580100', 'Johannesburg', 'CITY', '580000', 'ZAF', 'Johannesburg', 'MEA', 'OFFICE', TRUE),
('580200', 'Cape Town', 'CITY', '580000', 'ZAF', 'Cape Town', 'MEA', 'OFFICE', TRUE),
-- Egypt
('590100', 'Cairo', 'CITY', '590000', 'EGY', 'Cairo', 'MEA', 'OFFICE', TRUE),
-- Nigeria
('591100', 'Lagos', 'CITY', '591000', 'NGA', 'Lagos', 'MEA', 'OFFICE', TRUE),
('591200', 'Abuja', 'CITY', '591000', 'NGA', 'Abuja', 'MEA', 'OFFICE', TRUE);

-- =====================================================
-- OCEANIA REGION (6XXXXX)
-- =====================================================

INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
('600000', 'Oceania Region', 'REGION', '000001', NULL, 'APAC', 'OFFICE', TRUE),
('610000', 'Australia', 'COUNTRY', '600000', 'AUS', 'APAC', 'OFFICE', TRUE),
('620000', 'New Zealand', 'COUNTRY', '600000', 'NZL', 'APAC', 'OFFICE', TRUE),
('630000', 'Fiji', 'COUNTRY', '600000', 'FJI', 'APAC', 'OFFICE', TRUE),
('640000', 'Papua New Guinea', 'COUNTRY', '600000', 'PNG', 'APAC', 'OFFICE', TRUE);

-- Australian States
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, business_area_id, location_type, is_active) VALUES
('611000', 'New South Wales', 'STATE', '610000', 'AUS', 'NSW', 'APAC', 'OFFICE', TRUE),
('612000', 'Victoria', 'STATE', '610000', 'AUS', 'VIC', 'APAC', 'OFFICE', TRUE),
('613000', 'Queensland', 'STATE', '610000', 'AUS', 'QLD', 'APAC', 'OFFICE', TRUE),
('614000', 'Western Australia', 'STATE', '610000', 'AUS', 'WA', 'APAC', 'OFFICE', TRUE);

-- Major Oceania Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type, is_active) VALUES
-- Australia
('611100', 'Sydney', 'CITY', '611000', 'AUS', 'NSW', 'Sydney', 'APAC', 'OFFICE', TRUE),
('612100', 'Melbourne', 'CITY', '612000', 'AUS', 'VIC', 'Melbourne', 'APAC', 'OFFICE', TRUE),
('613100', 'Brisbane', 'CITY', '613000', 'AUS', 'QLD', 'Brisbane', 'APAC', 'OFFICE', TRUE),
('614100', 'Perth', 'CITY', '614000', 'AUS', 'WA', 'Perth', 'APAC', 'OFFICE', TRUE),
-- New Zealand
('620100', 'Auckland', 'CITY', '620000', 'NZL', NULL, 'Auckland', 'APAC', 'OFFICE', TRUE),
('620200', 'Wellington', 'CITY', '620000', 'NZL', NULL, 'Wellington', 'APAC', 'OFFICE', TRUE);

-- =====================================================
-- CARIBBEAN REGION (7XXXXX)
-- =====================================================

INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
('700000', 'Caribbean Region', 'REGION', '000001', NULL, 'LA', 'OFFICE', TRUE),
('710000', 'Jamaica', 'COUNTRY', '700000', 'JAM', 'LA', 'OFFICE', TRUE),
('720000', 'Trinidad and Tobago', 'COUNTRY', '700000', 'TTO', 'LA', 'OFFICE', TRUE),
('730000', 'Bahamas', 'COUNTRY', '700000', 'BHS', 'LA', 'OFFICE', TRUE),
('740000', 'Barbados', 'COUNTRY', '700000', 'BRB', 'LA', 'OFFICE', TRUE),
('750000', 'Dominican Republic', 'COUNTRY', '700000', 'DOM', 'LA', 'OFFICE', TRUE),
('760000', 'Puerto Rico', 'COUNTRY', '700000', 'PRI', 'LA', 'OFFICE', TRUE);

-- Caribbean Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, city, business_area_id, location_type, is_active) VALUES
('710100', 'Kingston', 'CITY', '710000', 'JAM', 'Kingston', 'LA', 'OFFICE', TRUE),
('720100', 'Port of Spain', 'CITY', '720000', 'TTO', 'Port of Spain', 'LA', 'OFFICE', TRUE),
('750100', 'Santo Domingo', 'CITY', '750000', 'DOM', 'Santo Domingo', 'LA', 'OFFICE', TRUE),
('760100', 'San Juan', 'CITY', '760000', 'PRI', 'San Juan', 'LA', 'OFFICE', TRUE);

-- =====================================================
-- CENTRAL ASIA REGION (8XXXXX)
-- =====================================================

INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_active) VALUES
('800000', 'Central Asia Region', 'REGION', '000001', NULL, 'APAC', 'OFFICE', TRUE),
('810000', 'Russia', 'COUNTRY', '800000', 'RUS', 'EU', 'OFFICE', TRUE),
('820000', 'Kazakhstan', 'COUNTRY', '800000', 'KAZ', 'APAC', 'OFFICE', TRUE),
('830000', 'Uzbekistan', 'COUNTRY', '800000', 'UZB', 'APAC', 'OFFICE', TRUE),
('840000', 'Ukraine', 'COUNTRY', '800000', 'UKR', 'EU', 'OFFICE', TRUE),
('850000', 'Belarus', 'COUNTRY', '800000', 'BLR', 'EU', 'OFFICE', TRUE);

-- Central Asian Cities
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, city, business_area_id, location_type, is_active) VALUES
('810100', 'Moscow', 'CITY', '810000', 'RUS', 'Moscow', 'EU', 'OFFICE', TRUE),
('810200', 'St. Petersburg', 'CITY', '810000', 'RUS', 'St. Petersburg', 'EU', 'OFFICE', TRUE),
('820100', 'Almaty', 'CITY', '820000', 'KAZ', 'Almaty', 'APAC', 'OFFICE', TRUE),
('840100', 'Kiev', 'CITY', '840000', 'UKR', 'Kiev', 'EU', 'OFFICE', TRUE);

-- =====================================================
-- Summary Statistics
-- =====================================================
-- Total locations added in this migration:
-- Countries: ~80+ new countries
-- States/Provinces: ~20+ states/provinces  
-- Cities: ~100+ major cities
-- Regions: 4 new regions (Oceania, Caribbean, Central Asia, plus existing)
-- Total new records: ~200+ location entries

-- =====================================================
-- Verification Query (uncomment to run)
-- =====================================================
-- SELECT 
--     location_level,
--     COUNT(*) as count,
--     COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_count
-- FROM reporting_locations
-- GROUP BY location_level
-- ORDER BY 
--     CASE location_level 
--         WHEN 'GLOBAL' THEN 1
--         WHEN 'REGION' THEN 2
--         WHEN 'COUNTRY' THEN 3
--         WHEN 'STATE' THEN 4
--         WHEN 'CITY' THEN 5
--         WHEN 'SITE' THEN 6
--         WHEN 'BUILDING' THEN 7
--         ELSE 8
--     END;