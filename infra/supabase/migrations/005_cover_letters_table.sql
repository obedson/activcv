-- Cover Letters table for AI-generated cover letters
-- This migration adds support for cover letter generation and management

CREATE TABLE cover_letters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id uuid REFERENCES jobs(id) ON DELETE CASCADE,
  template_used text NOT NULL DEFAULT 'professional_standard',
  tone text DEFAULT 'professional' CHECK (tone IN ('professional','modern','formal','casual','academic','persuasive')),
  status text DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
  pdf_url text,
  file_path text,
  file_size bigint,
  word_count integer,
  customizations jsonb DEFAULT '{}',
  generation_metadata jsonb DEFAULT '{}',
  content_data jsonb DEFAULT '{}',
  error_message text,
  email_sent boolean DEFAULT false,
  email_sent_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE cover_letters ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view own cover letters" ON cover_letters FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own cover letters" ON cover_letters FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own cover letters" ON cover_letters FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own cover letters" ON cover_letters FOR DELETE USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX idx_cover_letters_user_id ON cover_letters(user_id);
CREATE INDEX idx_cover_letters_job_id ON cover_letters(job_id);
CREATE INDEX idx_cover_letters_status ON cover_letters(status);
CREATE INDEX idx_cover_letters_created_at ON cover_letters(created_at DESC);
CREATE INDEX idx_cover_letters_template ON cover_letters(template_used);

-- Create trigger for updating timestamps
CREATE TRIGGER update_cover_letters_updated_at 
    BEFORE UPDATE ON cover_letters 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add cover letter templates reference table
CREATE TABLE cover_letter_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key text UNIQUE NOT NULL,
  name text NOT NULL,
  description text,
  tone text NOT NULL,
  category text DEFAULT 'business',
  suitable_for text[] DEFAULT '{}',
  is_active boolean DEFAULT true,
  preview_url text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Insert default templates
INSERT INTO cover_letter_templates (template_key, name, description, tone, category, suitable_for) VALUES
('professional_standard', 'Professional Standard', 'Classic professional format suitable for most industries', 'professional', 'business', ARRAY['corporate', 'finance', 'consulting', 'healthcare']),
('modern_creative', 'Modern Creative', 'Contemporary design for creative and tech industries', 'modern', 'creative', ARRAY['tech', 'design', 'marketing', 'startup']),
('executive_formal', 'Executive Formal', 'Formal executive style for senior positions', 'formal', 'executive', ARRAY['executive', 'c-level', 'board', 'senior-management']),
('startup_casual', 'Startup Casual', 'Casual, personable tone for startup environments', 'casual', 'startup', ARRAY['startup', 'tech', 'remote', 'small-business']),
('academic_research', 'Academic Research', 'Academic format emphasizing research and publications', 'academic', 'academic', ARRAY['academia', 'research', 'education', 'non-profit']),
('sales_persuasive', 'Sales Persuasive', 'Persuasive style highlighting achievements and results', 'persuasive', 'sales', ARRAY['sales', 'business-development', 'account-management', 'retail']);

-- Enable RLS on templates table
ALTER TABLE cover_letter_templates ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read templates
CREATE POLICY "All users can view cover letter templates" ON cover_letter_templates FOR SELECT TO authenticated USING (true);

-- Create indexes for templates
CREATE INDEX idx_cover_letter_templates_key ON cover_letter_templates(template_key);
CREATE INDEX idx_cover_letter_templates_active ON cover_letter_templates(is_active) WHERE is_active = true;

-- Add trigger for templates updated_at
CREATE TRIGGER update_cover_letter_templates_updated_at 
    BEFORE UPDATE ON cover_letter_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create cover letter statistics table for analytics
CREATE TABLE cover_letter_stats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  template_id text NOT NULL,
  job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  generation_time_ms integer,
  word_count integer,
  success boolean DEFAULT true,
  error_message text,
  created_at timestamptz DEFAULT now()
);

-- Enable RLS on stats table
ALTER TABLE cover_letter_stats ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for stats
CREATE POLICY "Users can view own cover letter stats" ON cover_letter_stats FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own cover letter stats" ON cover_letter_stats FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Create indexes for stats
CREATE INDEX idx_cover_letter_stats_user_id ON cover_letter_stats(user_id);
CREATE INDEX idx_cover_letter_stats_template ON cover_letter_stats(template_id);
CREATE INDEX idx_cover_letter_stats_created_at ON cover_letter_stats(created_at DESC);