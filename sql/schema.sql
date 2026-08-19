-- ============================================================================
-- NYC Public Grocery Store Initiative — Analytics & Business Modeling
-- MySQL schema
--
-- Covers: borough demographics, income distribution, physical store rollout
-- (CapEx/OpEx + hidden municipal subsidies), price baskets, and competing
-- subsidy-policy scenarios (physical store / tax credit / voucher) with
-- means-testing friction and simulated coverage outcomes.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS nyc_grocery_initiative
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE nyc_grocery_initiative;

SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- 1. boroughs — reference dimension, one row per NYC borough
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS boroughs;
CREATE TABLE boroughs (
    borough_id          INT AUTO_INCREMENT PRIMARY KEY,
    borough_name         VARCHAR(50)  NOT NULL UNIQUE,
    total_population     INT          NOT NULL,
    land_area_sq_miles   DECIMAL(6,2) NOT NULL,
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 2. population_demographics — yearly borough-level demographic snapshot
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS population_demographics;
CREATE TABLE population_demographics (
    demographic_id           INT AUTO_INCREMENT PRIMARY KEY,
    borough_id                INT      NOT NULL,
    year                      YEAR     NOT NULL,
    total_households          INT      NOT NULL,
    median_household_income   DECIMAL(12,2) NOT NULL,
    poverty_rate_pct           DECIMAL(5,2)  NOT NULL,
    snap_enrollment_pct        DECIMAL(5,2)  NOT NULL,
    food_insecurity_rate_pct   DECIMAL(5,2)  NOT NULL,
    pct_households_low_income  DECIMAL(5,2)  NOT NULL COMMENT 'Share of households under the eligibility income threshold (e.g. <=200% AMI)',
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_demo_borough FOREIGN KEY (borough_id) REFERENCES boroughs(borough_id) ON DELETE CASCADE,
    UNIQUE KEY uq_borough_year (borough_id, year)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 3. income_distribution — household counts by income bracket, per borough/year
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS income_distribution;
CREATE TABLE income_distribution (
    income_bracket_id     INT AUTO_INCREMENT PRIMARY KEY,
    borough_id             INT NOT NULL,
    year                   YEAR NOT NULL,
    income_bracket_label   VARCHAR(50)  NOT NULL COMMENT 'e.g. "<$25,000", "$25,000-$49,999"',
    bracket_min             DECIMAL(12,2) NOT NULL,
    bracket_max             DECIMAL(12,2) NULL COMMENT 'NULL = open-ended top bracket',
    household_count         INT NOT NULL,
    pct_of_total_households  DECIMAL(5,2) NOT NULL,
    CONSTRAINT fk_income_borough FOREIGN KEY (borough_id) REFERENCES boroughs(borough_id) ON DELETE CASCADE,
    INDEX idx_income_borough_year (borough_id, year)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 4. store_locations — proposed/rolled-out physical store sites
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS store_locations;
CREATE TABLE store_locations (
    store_id                  INT AUTO_INCREMENT PRIMARY KEY,
    borough_id                 INT NOT NULL,
    store_name                  VARCHAR(100) NOT NULL,
    address                     VARCHAR(255),
    latitude                    DECIMAL(9,6),
    longitude                   DECIMAL(9,6),
    service_radius_miles         DECIMAL(5,2) NOT NULL COMMENT 'Realistic walkable/service catchment radius',
    population_within_radius      INT NOT NULL COMMENT 'Est. residents actually reachable by this single site',
    planned_open_date            DATE,
    status                      ENUM('planned','under_construction','open','delayed','cancelled') NOT NULL DEFAULT 'planned',
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_store_borough FOREIGN KEY (borough_id) REFERENCES boroughs(borough_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 5. store_costs — CapEx/OpEx simulation per store, planned vs realistic,
--    including hidden municipal subsidies (foregone property tax, free rent)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS store_costs;
CREATE TABLE store_costs (
    cost_id                          INT AUTO_INCREMENT PRIMARY KEY,
    store_id                          INT NOT NULL,
    cost_scenario                     ENUM('planned','realistic') NOT NULL COMMENT 'planned = official $12M figure, realistic = modeled $30M+ figure',
    capex_construction                 DECIMAL(14,2) NOT NULL,
    capex_equipment                    DECIMAL(14,2) NOT NULL DEFAULT 0,
    opex_annual_labor                  DECIMAL(14,2) NOT NULL DEFAULT 0,
    opex_annual_utilities                DECIMAL(14,2) NOT NULL DEFAULT 0,
    opex_annual_inventory_subsidy        DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT 'Cost of selling goods below market/at cost',
    foregone_property_tax_annual         DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT 'Hidden subsidy: property tax the city forgoes',
    rent_subsidy_annual                 DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT 'Hidden subsidy: market rent value given at zero/below-market rent',
    notes                             VARCHAR(255),
    created_at                        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cost_store FOREIGN KEY (store_id) REFERENCES store_locations(store_id) ON DELETE CASCADE,
    UNIQUE KEY uq_store_scenario (store_id, cost_scenario)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 6. price_basket_items — grocery pricing catalogue, market vs subsidized
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS price_basket_items;
CREATE TABLE price_basket_items (
    item_id            INT AUTO_INCREMENT PRIMARY KEY,
    item_name           VARCHAR(100) NOT NULL,
    category            VARCHAR(50)  NOT NULL COMMENT 'e.g. produce, dairy, grains, protein, pantry',
    unit                VARCHAR(20)  NOT NULL COMMENT 'e.g. lb, each, gallon, dozen',
    market_price         DECIMAL(8,2) NOT NULL,
    subsidized_price      DECIMAL(8,2) NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 7. subsidy_scenarios — competing policy designs being compared
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS subsidy_scenarios;
CREATE TABLE subsidy_scenarios (
    scenario_id                   INT AUTO_INCREMENT PRIMARY KEY,
    scenario_name                  VARCHAR(100) NOT NULL,
    scenario_type                  ENUM('physical_store','tax_credit','digital_voucher','hybrid') NOT NULL,
    eligibility_model               ENUM('universal','means_tested') NOT NULL,
    eligibility_threshold_pct_ami     DECIMAL(6,2) NULL COMMENT 'e.g. 200 = eligible up to 200% of Area Median Income, NULL if universal',
    description                    TEXT,
    created_at                     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 8. means_testing_overhead — administrative friction cost per scenario
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS means_testing_overhead;
CREATE TABLE means_testing_overhead (
    overhead_id                        INT AUTO_INCREMENT PRIMARY KEY,
    scenario_id                         INT NOT NULL,
    admin_staff_cost_annual              DECIMAL(14,2) NOT NULL DEFAULT 0,
    verification_system_cost_annual        DECIMAL(14,2) NOT NULL DEFAULT 0 COMMENT 'e.g. income-verification tech/checkout integration',
    estimated_stigma_dropout_pct           DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT 'Eligible households who skip the benefit due to stigma/friction',
    estimated_leakage_pct                DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT 'Benefit captured by non-eligible households (relevant when universal/loosely gated)',
    avg_processing_time_days              DECIMAL(6,2) NOT NULL DEFAULT 0,
    CONSTRAINT fk_overhead_scenario FOREIGN KEY (scenario_id) REFERENCES subsidy_scenarios(scenario_id) ON DELETE CASCADE,
    UNIQUE KEY uq_overhead_scenario (scenario_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 9. scenario_outputs — simulated results per scenario / borough / year;
--    this is the primary table exported to Tableau
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS scenario_outputs;
CREATE TABLE scenario_outputs (
    output_id                  INT AUTO_INCREMENT PRIMARY KEY,
    scenario_id                 INT NOT NULL,
    borough_id                  INT NOT NULL,
    year                        YEAR NOT NULL,
    eligible_households           INT NOT NULL,
    households_reached           INT NOT NULL,
    total_program_cost           DECIMAL(16,2) NOT NULL COMMENT 'CapEx (amortized) + OpEx + admin overhead for the period',
    admin_overhead_cost          DECIMAL(14,2) NOT NULL DEFAULT 0,
    cost_per_household_reached     DECIMAL(12,2) NOT NULL COMMENT 'total_program_cost / households_reached',
    coverage_pct                DECIMAL(5,2) NOT NULL COMMENT 'households_reached / eligible_households * 100',
    coverage_gap_pct             DECIMAL(5,2) NOT NULL COMMENT '100 - coverage_pct',
    roi_estimate                DECIMAL(8,4) NULL COMMENT 'Modeled public-benefit-per-dollar-spent ratio',
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_output_scenario FOREIGN KEY (scenario_id) REFERENCES subsidy_scenarios(scenario_id) ON DELETE CASCADE,
    CONSTRAINT fk_output_borough  FOREIGN KEY (borough_id)  REFERENCES boroughs(borough_id) ON DELETE CASCADE,
    INDEX idx_output_scenario_year (scenario_id, year),
    INDEX idx_output_borough_year (borough_id, year)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;
