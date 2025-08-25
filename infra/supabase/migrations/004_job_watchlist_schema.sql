-- Job Sites Watchlist & AI CV Generator Schema
-- This migration adds support for job site monitoring and automated CV generation

-- Job sites watchlist table
CREATE TABLE job_sites_watchlist (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  site_url text NOT NULL,
  site_name text,
  filters jsonb DEFAULT '{}',
  is_active boolean DEFAULT true,
  last_crawled_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Jobs table
CREATE TABLE jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid REFERENCES job_sites_watchlist(id) ON DELETE CASCADE,
  external_id text, -- Job ID from the source site
  title text NOT NULL,
  company text,
  location text,
  work_mode text CHECK (work_mode IN ('remote', 'hybrid', 'onsite')),
  job_type text CHECK (job_type IN ('full-time', 'part-time', 'contract', 'internship')),
  description text,
  requirements text,
  compensation text,
  job_url text,
  posted_date timestamptz,
  expires_at timestamptz,
  raw_data jsonb, -- Store original scraped data
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(site_id, external_id) -- Prevent duplicate jobs from same site
);

-- Suggested jobs table (job-to-user matching)
CREATE TABLE suggested_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs(id) ON DELETE CASCADE,
  match_score float CHECK (match_score >= 0 AND match_score <= 1),
  match_reasons jsonb, -- Store why this job was matched
  is_viewed boolean DEFAULT false,
  is_dismissed boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, job_id) -- One suggestion per user per job
);

-- Generated CVs table
CREATE TABLE generated_cvs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs(id) ON DELETE CASCADE,
  template_used text DEFAULT 'modern_one_page',
  pdf_url text,
  file_path text,
  file_size bigint,
  generation_metadata jsonb, -- Store AI generation details
  email_sent boolean DEFAULT false,
  email_sent_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Crawling logs table for monitoring
CREATE TABLE crawling_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id uuid REFERENCES job_sites_watchlist(id) ON DELETE CASCADE,
  status text CHECK (status IN ('started', 'completed', 'failed')),
  jobs_found integer DEFAULT 0,
  jobs_new integer DEFAULT 0,
  jobs_updated integer DEFAULT 0,
  error_message text,
  execution_time_ms integer,
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Enable Row Level Security
ALTER TABLE job_sites_watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggested_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_cvs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawling_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for job_sites_watchlist
CREATE POLICY "Users can view own watchlist" ON job_sites_watchlist FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own watchlist" ON job_sites_watchlist FOR ALL USING (auth.uid() = user_id);

-- RLS Policies for jobs (users can only see jobs from their watchlist sites)
CREATE POLICY "Users can view jobs from their watchlist" ON jobs FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM job_sites_watchlist 
    WHERE job_sites_watchlist.id = jobs.site_id 
    AND job_sites_watchlist.user_id = auth.uid()
  )
);

-- RLS Policies for suggested_jobs
CREATE POLICY "Users can view own suggested jobs" ON suggested_jobs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own suggested jobs" ON suggested_jobs FOR ALL USING (auth.uid() = user_id);

-- RLS Policies for generated_cvs
CREATE POLICY "Users can view own generated CVs" ON generated_cvs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own generated CVs" ON generated_cvs FOR ALL USING (auth.uid() = user_id);

-- RLS Policies for crawling_logs (users can see logs for their watchlist sites)
CREATE POLICY "Users can view logs for their sites" ON crawling_logs FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM job_sites_watchlist 
    WHERE job_sites_watchlist.id = crawling_logs.site_id 
    AND job_sites_watchlist.user_id = auth.uid()
  )
);

-- Indexes for performance
CREATE INDEX idx_job_sites_watchlist_user_id ON job_sites_watchlist(user_id);
CREATE INDEX idx_job_sites_watchlist_active ON job_sites_watchlist(is_active) WHERE is_active = true;

CREATE INDEX idx_jobs_site_id ON jobs(site_id);
CREATE INDEX idx_jobs_posted_date ON jobs(posted_date DESC);
CREATE INDEX idx_jobs_work_mode ON jobs(work_mode);
CREATE INDEX idx_jobs_job_type ON jobs(job_type);
CREATE INDEX idx_jobs_location ON jobs(location);

CREATE INDEX idx_suggested_jobs_user_id ON suggested_jobs(user_id);
CREATE INDEX idx_suggested_jobs_match_score ON suggested_jobs(match_score DESC);
CREATE INDEX idx_suggested_jobs_created_at ON suggested_jobs(created_at DESC);
CREATE INDEX idx_suggested_jobs_viewed ON suggested_jobs(is_viewed) WHERE is_viewed = false;

CREATE INDEX idx_generated_cvs_user_id ON generated_cvs(user_id);
CREATE INDEX idx_generated_cvs_job_id ON generated_cvs(job_id);
CREATE INDEX idx_generated_cvs_created_at ON generated_cvs(created_at DESC);

CREATE INDEX idx_crawling_logs_site_id ON crawling_logs(site_id);
CREATE INDEX idx_crawling_logs_started_at ON crawling_logs(started_at DESC);

-- Functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
CREATE TRIGGER update_job_sites_watchlist_updated_at BEFORE UPDATE ON job_sites_watchlist FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();