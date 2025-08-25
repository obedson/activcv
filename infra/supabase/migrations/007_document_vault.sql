-- Document Vault System
-- This migration adds comprehensive document management capabilities

-- Document folders for organization (create first)
CREATE TABLE document_folders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  parent_folder_id uuid REFERENCES document_folders(id) ON DELETE CASCADE,
  color text DEFAULT '#3B82F6', -- Hex color for UI
  icon text DEFAULT 'folder', -- Icon identifier
  is_system_folder boolean DEFAULT false, -- System-created folders
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  
  UNIQUE(user_id, name, parent_folder_id)
);

-- Document vault table for managing all generated documents
CREATE TABLE document_vault (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  document_type text NOT NULL CHECK (document_type IN ('cv', 'cover_letter', 'portfolio', 'certificate', 'other')),
  title text NOT NULL,
  description text,
  file_name text NOT NULL,
  file_path text NOT NULL,
  file_url text,
  file_size bigint,
  mime_type text,
  file_hash text, -- For duplicate detection
  
  -- Document metadata
  template_used text,
  job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  generation_metadata jsonb DEFAULT '{}',
  
  -- Organization
  folder_id uuid REFERENCES document_folders(id) ON DELETE SET NULL,
  tags text[] DEFAULT '{}',
  
  -- Access and sharing
  is_public boolean DEFAULT false,
  share_token text UNIQUE,
  share_expires_at timestamptz,
  download_count integer DEFAULT 0,
  
  -- Version control
  version_number integer DEFAULT 1,
  parent_document_id uuid REFERENCES document_vault(id) ON DELETE SET NULL,
  is_latest_version boolean DEFAULT true,
  
  -- Status
  status text DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
  
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Document access logs for tracking
CREATE TABLE document_access_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES document_vault(id) ON DELETE CASCADE,
  user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  access_type text NOT NULL CHECK (access_type IN ('view', 'download', 'share', 'edit', 'delete')),
  ip_address inet,
  user_agent text,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Document sharing permissions
CREATE TABLE document_shares (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES document_vault(id) ON DELETE CASCADE,
  shared_by_user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  shared_with_email text,
  share_token text NOT NULL UNIQUE,
  permissions text[] DEFAULT '{"view"}' CHECK (permissions <@ ARRAY['view', 'download', 'comment']),
  expires_at timestamptz,
  is_active boolean DEFAULT true,
  access_count integer DEFAULT 0,
  last_accessed_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Document templates for quick creation
CREATE TABLE document_templates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  document_type text NOT NULL,
  template_data jsonb NOT NULL DEFAULT '{}',
  preview_url text,
  is_system_template boolean DEFAULT false,
  is_active boolean DEFAULT true,
  usage_count integer DEFAULT 0,
  created_by_user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE document_vault ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies for document_vault
CREATE POLICY "Users can view own documents" ON document_vault FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own documents" ON document_vault FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own documents" ON document_vault FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own documents" ON document_vault FOR DELETE USING (auth.uid() = user_id);

-- Allow access to shared documents
CREATE POLICY "Allow access to shared documents" ON document_vault FOR SELECT 
  USING (
    is_public = true OR 
    EXISTS (
      SELECT 1 FROM document_shares ds 
      WHERE ds.document_id = document_vault.id 
      AND ds.is_active = true 
      AND (ds.expires_at IS NULL OR ds.expires_at > now())
    )
  );

-- RLS Policies for document_folders
CREATE POLICY "Users can manage own folders" ON document_folders FOR ALL USING (auth.uid() = user_id);

-- RLS Policies for document_access_logs
CREATE POLICY "Users can view own document access logs" ON document_access_logs FOR SELECT 
  USING (EXISTS (SELECT 1 FROM document_vault dv WHERE dv.id = document_access_logs.document_id AND dv.user_id = auth.uid()));
CREATE POLICY "System can create access logs" ON document_access_logs FOR INSERT WITH CHECK (true);

-- RLS Policies for document_shares
CREATE POLICY "Users can manage own document shares" ON document_shares FOR ALL USING (auth.uid() = shared_by_user_id);

-- RLS Policies for document_templates
CREATE POLICY "All users can view active templates" ON document_templates FOR SELECT USING (is_active = true);
CREATE POLICY "Users can create custom templates" ON document_templates FOR INSERT WITH CHECK (auth.uid() = created_by_user_id);
CREATE POLICY "Users can update own templates" ON document_templates FOR UPDATE USING (auth.uid() = created_by_user_id);

-- Indexes for performance
CREATE INDEX idx_document_vault_user_id ON document_vault(user_id);
CREATE INDEX idx_document_vault_type ON document_vault(document_type);
CREATE INDEX idx_document_vault_status ON document_vault(status);
CREATE INDEX idx_document_vault_folder_id ON document_vault(folder_id);
CREATE INDEX idx_document_vault_job_id ON document_vault(job_id);
CREATE INDEX idx_document_vault_created_at ON document_vault(created_at DESC);
CREATE INDEX idx_document_vault_file_hash ON document_vault(file_hash);
CREATE INDEX idx_document_vault_share_token ON document_vault(share_token) WHERE share_token IS NOT NULL;

CREATE INDEX idx_document_folders_user_id ON document_folders(user_id);
CREATE INDEX idx_document_folders_parent ON document_folders(parent_folder_id);

CREATE INDEX idx_document_access_logs_document_id ON document_access_logs(document_id);
CREATE INDEX idx_document_access_logs_created_at ON document_access_logs(created_at DESC);

CREATE INDEX idx_document_shares_token ON document_shares(share_token);
CREATE INDEX idx_document_shares_document_id ON document_shares(document_id);
CREATE INDEX idx_document_shares_expires_at ON document_shares(expires_at) WHERE expires_at IS NOT NULL;

-- Triggers for updating timestamps
CREATE TRIGGER update_document_vault_updated_at 
    BEFORE UPDATE ON document_vault 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_folders_updated_at 
    BEFORE UPDATE ON document_folders 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_templates_updated_at 
    BEFORE UPDATE ON document_templates 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to generate share token
CREATE OR REPLACE FUNCTION generate_share_token()
RETURNS text AS $$
BEGIN
    RETURN encode(gen_random_bytes(32), 'base64url');
END;
$$ LANGUAGE plpgsql;

-- Function to create system folders for new users
CREATE OR REPLACE FUNCTION create_system_folders_for_user(user_id uuid)
RETURNS void AS $$
BEGIN
    INSERT INTO document_folders (user_id, name, description, is_system_folder, icon, color) VALUES
    (user_id, 'CVs', 'Generated CV documents', true, 'document-text', '#10B981'),
    (user_id, 'Cover Letters', 'Generated cover letters', true, 'mail', '#3B82F6'),
    (user_id, 'Certificates', 'Certificates and credentials', true, 'academic-cap', '#F59E0B'),
    (user_id, 'Portfolio', 'Portfolio documents', true, 'briefcase', '#8B5CF6'),
    (user_id, 'Archive', 'Archived documents', true, 'archive', '#6B7280');
END;
$$ LANGUAGE plpgsql;

-- Function to log document access
CREATE OR REPLACE FUNCTION log_document_access(
    doc_id uuid,
    access_type text,
    user_id uuid DEFAULT NULL,
    ip_addr inet DEFAULT NULL,
    user_agent_str text DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    INSERT INTO document_access_logs (document_id, user_id, access_type, ip_address, user_agent)
    VALUES (doc_id, user_id, access_type, ip_addr, user_agent_str);
    
    -- Update download count if it's a download
    IF access_type = 'download' THEN
        UPDATE document_vault 
        SET download_count = download_count + 1 
        WHERE id = doc_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired shares
CREATE OR REPLACE FUNCTION cleanup_expired_shares()
RETURNS void AS $$
BEGIN
    UPDATE document_shares 
    SET is_active = false 
    WHERE expires_at < now() AND is_active = true;
END;
$$ LANGUAGE plpgsql;

-- Function to get document storage stats
CREATE OR REPLACE FUNCTION get_user_storage_stats(user_id uuid)
RETURNS TABLE(
    total_documents integer,
    total_size_bytes bigint,
    documents_by_type jsonb,
    storage_used_mb numeric
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::integer as total_documents,
        COALESCE(SUM(file_size), 0) as total_size_bytes,
        jsonb_object_agg(document_type, type_count) as documents_by_type,
        ROUND(COALESCE(SUM(file_size), 0) / 1024.0 / 1024.0, 2) as storage_used_mb
    FROM (
        SELECT 
            document_type,
            file_size,
            COUNT(*) OVER (PARTITION BY document_type) as type_count
        FROM document_vault 
        WHERE document_vault.user_id = get_user_storage_stats.user_id 
        AND status = 'active'
    ) stats;
END;
$$ LANGUAGE plpgsql;

-- Create view for document vault dashboard
CREATE VIEW document_vault_dashboard AS
SELECT 
    dv.id,
    dv.user_id,
    dv.document_type,
    dv.title,
    dv.description,
    dv.file_name,
    dv.file_size,
    dv.template_used,
    dv.download_count,
    dv.version_number,
    dv.is_latest_version,
    dv.status,
    dv.created_at,
    dv.updated_at,
    df.name as folder_name,
    df.color as folder_color,
    j.title as job_title,
    j.company as job_company,
    CASE 
        WHEN dv.share_token IS NOT NULL THEN true 
        ELSE false 
    END as is_shared,
    COALESCE(share_stats.share_count, 0) as share_count,
    COALESCE(access_stats.recent_access_count, 0) as recent_access_count
FROM document_vault dv
LEFT JOIN document_folders df ON dv.folder_id = df.id
LEFT JOIN jobs j ON dv.job_id = j.id
LEFT JOIN (
    SELECT document_id, COUNT(*) as share_count
    FROM document_shares 
    WHERE is_active = true
    GROUP BY document_id
) share_stats ON dv.id = share_stats.document_id
LEFT JOIN (
    SELECT document_id, COUNT(*) as recent_access_count
    FROM document_access_logs 
    WHERE created_at > now() - interval '7 days'
    GROUP BY document_id
) access_stats ON dv.id = access_stats.document_id;

-- Grant access to the view
GRANT SELECT ON document_vault_dashboard TO authenticated;

-- Insert default document templates
INSERT INTO document_templates (name, description, document_type, template_data, is_system_template) VALUES
('Modern CV', 'Clean and modern CV template', 'cv', '{"style": "modern", "sections": ["summary", "experience", "education", "skills"]}', true),
('Professional Cover Letter', 'Standard professional cover letter', 'cover_letter', '{"style": "professional", "tone": "formal"}', true),
('Creative Portfolio', 'Creative portfolio template', 'portfolio', '{"style": "creative", "layout": "grid"}', true);

-- Enable realtime for document updates
ALTER PUBLICATION supabase_realtime ADD TABLE document_vault;
ALTER PUBLICATION supabase_realtime ADD TABLE document_folders;