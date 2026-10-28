-- SchemaFlow Sample: School Academic Management System
-- Features 1:N relations and M:N composite junction table for student class enrolments.

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20) UNIQUE NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    standard INT NOT NULL,
    guardian_phone VARCHAR(15)
);

CREATE TABLE classes (
    class_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(15) NOT NULL,
    subject_title VARCHAR(100) NOT NULL,
    teacher_name VARCHAR(100) NOT NULL,
    academic_year VARCHAR(10) NOT NULL
);

CREATE TABLE enrolments (
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    enrolled_date DATE NOT NULL,
    grade_letter VARCHAR(2),
    PRIMARY KEY (student_id, class_id),
    CONSTRAINT fk_enrol_student FOREIGN KEY (student_id) REFERENCES students(student_id),
    CONSTRAINT fk_enrol_class FOREIGN KEY (class_id) REFERENCES classes(class_id)
);
