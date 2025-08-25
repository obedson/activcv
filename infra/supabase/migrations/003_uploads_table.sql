-- Create uploads table for file upload tracking
-- This migration adds support for CV file uploads and parsing

CREATE TABLE uploads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  filename text NOT NULL,
  file_path text NOT NULL,
  file_size bigint NOT NULL,
  mime_type text DEFAULT 'application/pdf',
  status text DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
  parsed_data jsonb,
  error_message text,
  created_at timestamptz DEFAULT now(),
  processed_at timestamptz
);

-- Enable Row Level Security
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view own uploads" ON uploads FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own uploads" ON uploads FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own uploads" ON uploads FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own uploads" ON uploads FOR DELETE USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX idx_uploads_user_id ON uploads(user_id);
CREATE INDEX idx_uploads_status ON uploads(status);
CREATE INDEX idx_uploads_created_at ON uploads(created_at DESC);