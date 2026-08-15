-- Supabase Database Migration for Teacher Management System
-- Run this SQL in Supabase SQL Editor

-- Drop tables if they exist
DROP TABLE IF EXISTS activity_logs CASCADE;
DROP TABLE IF EXISTS teacher_documents CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- USERS table: id is UUID primary key
CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(100) NOT NULL,
    father_name VARCHAR(100),
    husband_name VARCHAR(100),
    gender VARCHAR(20),
    cnic VARCHAR(20) UNIQUE NOT NULL,
    personal_number VARCHAR(20),
    school_name VARCHAR(150),
    semis_code VARCHAR(50),
    taluka VARCHAR(100),
    district VARCHAR(100),
    union_council VARCHAR(100),
    domicile_taluka VARCHAR(100),
    date_of_birth VARCHAR(20),
    date_of_joining_school VARCHAR(20),
    current_address TEXT,
    permanent_address TEXT,
    contact_number VARCHAR(20),
    father_number VARCHAR(20),
    husband_number VARCHAR(20),
    iba_seat_number VARCHAR(50),
    drc_number VARCHAR(50),
    iba_first_merit_number VARCHAR(50),
    iba_obtained_marks VARCHAR(20),
    designation VARCHAR(100),
    bps VARCHAR(20),
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    password_hash VARCHAR(200) NOT NULL,
    role VARCHAR(20) DEFAULT 'teacher' CHECK (role IN ('teacher', 'admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- TEACHER DOCUMENTS table
CREATE TABLE teacher_documents (
    id SERIAL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    description TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- ACTIVITY LOGS table
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    user_id uuid REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_cnic ON users(cnic);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_documents_user_id ON teacher_documents(user_id);
CREATE INDEX idx_documents_type ON teacher_documents(document_type);
CREATE INDEX idx_activity_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_created_at ON activity_logs(created_at);

-- Insert default admin user (password: admin123)
INSERT INTO users (id, full_name, cnic, email, password_hash, role, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'System Administrator',
    '0000000000000',
    'admin@deo.gov.pk',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yXKBPGJz8W8a',
    'admin',
    TRUE
) ON CONFLICT (cnic) DO NOTHING;

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE teacher_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Admins can view all users" ON users FOR SELECT USING (role = 'admin');
CREATE POLICY "Teachers can view own profile" ON users FOR SELECT USING (id = auth.uid());

CREATE POLICY "Admins can view all documents" ON teacher_documents FOR SELECT USING (
    user_id IN (SELECT id FROM users WHERE role = 'admin')
);
CREATE POLICY "Teachers can view own documents" ON teacher_documents FOR SELECT USING (
    user_id = auth.uid()
);

CREATE POLICY "Admins can view activity logs" ON activity_logs FOR SELECT USING (
    user_id IN (SELECT id FROM users WHERE role = 'admin')
);
