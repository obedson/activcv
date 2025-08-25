-- Job Processing System
-- This migration adds support for real-time job processing with progress tracking

-- Job processing queue table
CREATE TABLE job_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  job_type text NOT NULL CHECK (job_type IN ('cv_generation', 'cover_letter_generation', 'job_analysis', 'bulk_generation')),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
  priority integer DEFAULT 5 CHECK (priority BETWEEN 1 AND 10), -- 1 = highest priority
  input_data jsonb NOT NULL DEFAULT '{}',
  output_data jsonb DEFAULT '{}',
  progress_percentage integer DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
  current_step text,
  total_steps integer DEFAULT 1,
  error_message text,
  retry_count integer DEFAULT 0,
  max_retries integer DEFAULT 3,
  scheduled_at timestamptz DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Job processing steps for detailed progress tracking
CREATE TABLE job_processing_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_queue_id uuid REFERENCES job_queue(id) ON DELETE CASCADE,
  step_name text NOT NULL,
  step_order integer NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
  progress_percentage integer DEFAULT 0 CHECK (progress_percentage BETWEEN 0 AND 100),
  step_data jsonb DEFAULT '{}',
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Job processing logs for detailed tracking
CREATE TABLE job_processing_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_queue_id uuid REFERENCES job_queue(id) ON DELETE CASCADE,
  log_level text NOT NULL CHECK (log_level IN ('debug', 'info', 'warning', 'error')),
  message text NOT NULL,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Job processing metrics for monitoring
CREATE TABLE job_processing_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type text NOT NULL,
  status text NOT NULL,
  processing_time_ms integer,
  queue_wait_time_ms integer,
  retry_count integer DEFAULT 0,
  error_category text,
  created_date date DEFAULT CURRENT_DATE,
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE job_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_processing_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_processing_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_processing_metrics ENABLE ROW LEVEL SECURITY;

-- RLS Policies for job_queue
CREATE POLICY "Users can view own jobs" ON job_queue FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own jobs" ON job_queue FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own jobs" ON job_queue FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own jobs" ON job_queue FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for job_processing_steps
CREATE POLICY "Users can view own job steps" ON job_processing_steps FOR SELECT 
  USING (EXISTS (SELECT 1 FROM job_queue WHERE job_queue.id = job_processing_steps.job_queue_id AND job_queue.user_id = auth.uid()));
CREATE POLICY "System can manage job steps" ON job_processing_steps FOR ALL 
  USING (EXISTS (SELECT 1 FROM job_queue WHERE job_queue.id = job_processing_steps.job_queue_id));

-- RLS Policies for job_processing_logs
CREATE POLICY "Users can view own job logs" ON job_processing_logs FOR SELECT 
  USING (EXISTS (SELECT 1 FROM job_queue WHERE job_queue.id = job_processing_logs.job_queue_id AND job_queue.user_id = auth.uid()));
CREATE POLICY "System can create job logs" ON job_processing_logs FOR INSERT WITH CHECK (true);

-- RLS Policies for job_processing_metrics (admin only)
CREATE POLICY "Admin can view metrics" ON job_processing_metrics FOR SELECT USING (auth.jwt() ->> 'role' = 'admin');
CREATE POLICY "System can create metrics" ON job_processing_metrics FOR INSERT WITH CHECK (true);

-- Indexes for performance
CREATE INDEX idx_job_queue_user_id ON job_queue(user_id);
CREATE INDEX idx_job_queue_status ON job_queue(status);
CREATE INDEX idx_job_queue_job_type ON job_queue(job_type);
CREATE INDEX idx_job_queue_priority_scheduled ON job_queue(priority, scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_job_queue_created_at ON job_queue(created_at DESC);

CREATE INDEX idx_job_processing_steps_job_queue_id ON job_processing_steps(job_queue_id);
CREATE INDEX idx_job_processing_steps_order ON job_processing_steps(job_queue_id, step_order);

CREATE INDEX idx_job_processing_logs_job_queue_id ON job_processing_logs(job_queue_id);
CREATE INDEX idx_job_processing_logs_created_at ON job_processing_logs(created_at DESC);

CREATE INDEX idx_job_processing_metrics_date ON job_processing_metrics(created_date);
CREATE INDEX idx_job_processing_metrics_type_status ON job_processing_metrics(job_type, status);

-- Triggers for updating timestamps
CREATE TRIGGER update_job_queue_updated_at 
    BEFORE UPDATE ON job_queue 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_processing_steps_updated_at 
    BEFORE UPDATE ON job_processing_steps 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate overall job progress
CREATE OR REPLACE FUNCTION calculate_job_progress(job_id uuid)
RETURNS integer AS $$
DECLARE
    total_steps integer;
    completed_steps integer;
    progress integer;
BEGIN
    SELECT COUNT(*) INTO total_steps 
    FROM job_processing_steps 
    WHERE job_queue_id = job_id;
    
    IF total_steps = 0 THEN
        RETURN 0;
    END IF;
    
    SELECT COUNT(*) INTO completed_steps 
    FROM job_processing_steps 
    WHERE job_queue_id = job_id AND status = 'completed';
    
    progress := (completed_steps * 100) / total_steps;
    
    -- Update the job queue progress
    UPDATE job_queue 
    SET progress_percentage = progress,
        updated_at = now()
    WHERE id = job_id;
    
    RETURN progress;
END;
$$ LANGUAGE plpgsql;

-- Function to get next job from queue
CREATE OR REPLACE FUNCTION get_next_job_from_queue()
RETURNS TABLE(
    job_id uuid,
    user_id uuid,
    job_type text,
    input_data jsonb,
    priority integer
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        jq.id,
        jq.user_id,
        jq.job_type,
        jq.input_data,
        jq.priority
    FROM job_queue jq
    WHERE jq.status = 'pending'
      AND jq.scheduled_at <= now()
      AND jq.retry_count < jq.max_retries
    ORDER BY jq.priority ASC, jq.scheduled_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;
END;
$$ LANGUAGE plpgsql;

-- Function to mark job as processing
CREATE OR REPLACE FUNCTION start_job_processing(job_id uuid)
RETURNS boolean AS $$
BEGIN
    UPDATE job_queue 
    SET status = 'processing',
        started_at = now(),
        updated_at = now()
    WHERE id = job_id AND status = 'pending';
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to complete job
CREATE OR REPLACE FUNCTION complete_job_processing(
    job_id uuid,
    output_data jsonb DEFAULT '{}'::jsonb,
    success boolean DEFAULT true
)
RETURNS boolean AS $$
BEGIN
    IF success THEN
        UPDATE job_queue 
        SET status = 'completed',
            output_data = complete_job_processing.output_data,
            progress_percentage = 100,
            completed_at = now(),
            updated_at = now()
        WHERE id = job_id;
    ELSE
        UPDATE job_queue 
        SET status = 'failed',
            retry_count = retry_count + 1,
            updated_at = now()
        WHERE id = job_id;
    END IF;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Create view for job queue dashboard
CREATE VIEW job_queue_dashboard AS
SELECT 
    jq.id,
    jq.user_id,
    jq.job_type,
    jq.status,
    jq.priority,
    jq.progress_percentage,
    jq.current_step,
    jq.total_steps,
    jq.error_message,
    jq.retry_count,
    jq.created_at,
    jq.started_at,
    jq.completed_at,
    EXTRACT(EPOCH FROM (COALESCE(jq.completed_at, now()) - jq.created_at)) * 1000 as total_time_ms,
    EXTRACT(EPOCH FROM (COALESCE(jq.started_at, now()) - jq.created_at)) * 1000 as queue_wait_time_ms,
    CASE 
        WHEN jq.started_at IS NOT NULL AND jq.completed_at IS NOT NULL THEN
            EXTRACT(EPOCH FROM (jq.completed_at - jq.started_at)) * 1000
        WHEN jq.started_at IS NOT NULL THEN
            EXTRACT(EPOCH FROM (now() - jq.started_at)) * 1000
        ELSE NULL
    END as processing_time_ms
FROM job_queue jq;

-- Grant access to the view
GRANT SELECT ON job_queue_dashboard TO authenticated;

-- Enable realtime for job queue updates
ALTER PUBLICATION supabase_realtime ADD TABLE job_queue;
ALTER PUBLICATION supabase_realtime ADD TABLE job_processing_steps;
ALTER PUBLICATION supabase_realtime ADD TABLE job_processing_logs;