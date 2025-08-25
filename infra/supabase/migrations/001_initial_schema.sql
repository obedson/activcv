-- Initial database schema for AI CV Agent
-- This migration creates the core tables and security policies

-- Create custom schemas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS gen;

-- Enable Row Level Security
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- Core user profiles table
CREATE TABLE core.profiles (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  headline text,
  summary text,
  linkedin_url text,
  website_url text,
  additional_details text,
  last_updated timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

-- Personal information
CREATE TABLE core.personal_info (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name text NOT NULL,
  last_name text NOT NULL,
  email text NOT NULL,
  phone text,
  address text,
  city text,
  country text,
  postal_code text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Education records
CREATE TABLE core.education (
  id bigserial PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  institution text NOT NULL,
  degree text,
  field_of_study text,
  start_date date,
  end_date date,
  currently_enrolled boolean DEFAULT false,
  gpa text,
  description text,
  created_at timestamptz DEFAULT now()
);

-- Work experience
CREATE TABLE core.experience (
  id bigserial PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  title text NOT NULL,
  company text,
  location text,
  start_date date,
  end_date date,
  currently_employed boolean DEFAULT false,
  achievements text[],
  description text,
  additional_notes text,
  created_at timestamptz DEFAULT now()
);

-- Skills
CREATE TABLE core.skills (
  id bigserial PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  level text CHECK (level IN ('beginner','intermediate','advanced','expert')),
  category text,
  years_experience integer,
  context text,
  created_at timestamptz DEFAULT now()
);

-- Certifications
CREATE TABLE core.certifications (
  id bigserial PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  issuing_organization text,
  issue_date date,
  expiration_date date,
  credential_id text,
  credential_url text,
  created_at timestamptz DEFAULT now()
);

-- References
CREATE TABLE core.referees (
  id bigserial PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  title text,
  company text,
  email text,
  phone text,
  relationship text,
  created_at timestamptz DEFAULT now()
);

-- Job processing
CREATE TABLE gen.jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  type text CHECK (type IN ('build_cv','tailor_cv')) NOT NULL,
  jd_text text,
  jd_url text,
  additional_quals text,
  template_key text DEFAULT 'modern_one_page',
  status text DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed')),
  progress integer DEFAULT 0,
  current_step text,
  error text,
  metadata jsonb,
  created_at timestamptz DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz
);

-- Generated documents
CREATE TABLE gen.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id uuid REFERENCES gen.jobs(id) ON DELETE CASCADE,
  filename text NOT NULL,
  file_path text NOT NULL,
  file_size bigint,
  mime_type text DEFAULT 'application/pdf',
  template_used text,
  is_tailored boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security on all tables
ALTER TABLE core.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.personal_info ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.education ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.experience ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.certifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.referees ENABLE ROW LEVEL SECURITY;
ALTER TABLE gen.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE gen.documents ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for core tables
CREATE POLICY "Users can view own profile" ON core.profiles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own profile" ON core.profiles FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own profile" ON core.profiles FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own personal info" ON core.personal_info FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can update own personal info" ON core.personal_info FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own personal info" ON core.personal_info FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own education" ON core.education FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own education" ON core.education FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own experience" ON core.experience FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own experience" ON core.experience FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own skills" ON core.skills FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own skills" ON core.skills FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own certifications" ON core.certifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own certifications" ON core.certifications FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own referees" ON core.referees FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own referees" ON core.referees FOR ALL USING (auth.uid() = user_id);

-- Create RLS policies for generation tables
CREATE POLICY "Users can view own jobs" ON gen.jobs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own jobs" ON gen.jobs FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own jobs" ON gen.jobs FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own documents" ON gen.documents FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own documents" ON gen.documents FOR ALL USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX idx_profiles_user_id ON core.profiles(user_id);
CREATE INDEX idx_education_user_id ON core.education(user_id);
CREATE INDEX idx_experience_user_id ON core.experience(user_id);
CREATE INDEX idx_skills_user_id ON core.skills(user_id);
CREATE INDEX idx_certifications_user_id ON core.certifications(user_id);
CREATE INDEX idx_referees_user_id ON core.referees(user_id);
CREATE INDEX idx_jobs_user_id ON gen.jobs(user_id);
CREATE INDEX idx_jobs_status ON gen.jobs(status);
CREATE INDEX idx_documents_user_id ON gen.documents(user_id);
CREATE INDEX idx_documents_job_id ON gen.documents(job_id);