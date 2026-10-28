-- SchemaFlow Sample: Public Distribution System (Ration Shop)
-- Features 1:N family shop registration and M:N composite junction table for ration quota distribution.

CREATE TABLE ration_shops (
    shop_id INT AUTO_INCREMENT PRIMARY KEY,
    license_number VARCHAR(30) UNIQUE NOT NULL,
    dealer_name VARCHAR(100) NOT NULL,
    ward_number INT NOT NULL
);

CREATE TABLE families (
    family_id INT AUTO_INCREMENT PRIMARY KEY,
    ration_card_number VARCHAR(25) UNIQUE NOT NULL,
    head_of_family VARCHAR(100) NOT NULL,
    card_category VARCHAR(10) NOT NULL,
    shop_id INT NOT NULL,
    CONSTRAINT fk_family_shop FOREIGN KEY (shop_id) REFERENCES ration_shops(shop_id)
);

CREATE TABLE items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(50) NOT NULL,
    subsidy_rate DECIMAL(8,2) NOT NULL,
    unit VARCHAR(10) NOT NULL
);

CREATE TABLE ration_entries (
    family_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity_allocated DECIMAL(6,2) NOT NULL,
    disbursed_date DATE NOT NULL,
    PRIMARY KEY (family_id, item_id),
    CONSTRAINT fk_entry_family FOREIGN KEY (family_id) REFERENCES families(family_id),
    CONSTRAINT fk_entry_item FOREIGN KEY (item_id) REFERENCES items(item_id)
);
