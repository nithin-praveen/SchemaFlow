-- SchemaFlow Sample: District Blood Bank Management
-- Features 1:N donor donations and 1:1 transfusion unit verification.

CREATE TABLE donors (
    donor_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    last_donated_date DATE
);

CREATE TABLE recipients (
    recipient_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    hospital_name VARCHAR(100) NOT NULL,
    required_blood_group VARCHAR(5) NOT NULL,
    urgency_level VARCHAR(20) NOT NULL
);

CREATE TABLE donations (
    donation_id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    units_ml INT NOT NULL,
    collected_date DATE NOT NULL,
    CONSTRAINT fk_donations_donor FOREIGN KEY (donor_id) REFERENCES donors(donor_id)
);

CREATE TABLE transfusions (
    transfusion_id INT AUTO_INCREMENT PRIMARY KEY,
    donation_id INT UNIQUE NOT NULL,
    recipient_id INT NOT NULL,
    transfusion_date DATE NOT NULL,
    CONSTRAINT fk_transfusion_donation FOREIGN KEY (donation_id) REFERENCES donations(donation_id),
    CONSTRAINT fk_transfusion_recipient FOREIGN KEY (recipient_id) REFERENCES recipients(recipient_id)
);
