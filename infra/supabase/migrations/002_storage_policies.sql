-- Storage policies and bucket configuration
-- This migration sets up secure storage access for documents and uploads

-- Create storage buckets (if not already created via config)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
  ('documents', 'documents', false, 52428800, ARRAY['application/pdf']),
  ('uploads', 'uploads', false, 52428800, ARRAY['application/pdf'])
ON CONFLICT (id) DO NOTHING;

-- Storage policies for documents bucket
CREATE POLICY "Users can view own documents" ON storage.objects 
FOR SELECT USING (
  bucket_id = 'documents' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can upload own documents" ON storage.objects 
FOR INSERT WITH CHECK (
  bucket_id = 'documents' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can update own documents" ON storage.objects 
FOR UPDATE USING (
  bucket_id = 'documents' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can delete own documents" ON storage.objects 
FOR DELETE USING (
  bucket_id = 'documents' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

-- Storage policies for uploads bucket
CREATE POLICY "Users can view own uploads" ON storage.objects 
FOR SELECT USING (
  bucket_id = 'uploads' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can upload files" ON storage.objects 
FOR INSERT WITH CHECK (
  bucket_id = 'uploads' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can update own uploads" ON storage.objects 
FOR UPDATE USING (
  bucket_id = 'uploads' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can delete own uploads" ON storage.objects 
FOR DELETE USING (
  bucket_id = 'uploads' AND 
  auth.uid()::text = (storage.foldername(name))[1]
);

-- Function to generate signed URLs with 24-hour expiration
CREATE OR REPLACE FUNCTION generate_signed_url(bucket_name text, object_path text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  signed_url text;
BEGIN
  -- Verify user owns the object
  IF NOT EXISTS (
    SELECT 1 FROM storage.objects 
    WHERE bucket_id = bucket_name 
    AND name = object_path 
    AND auth.uid()::text = (storage.foldername(name))[1]
  ) THEN
    RAISE EXCEPTION 'Access denied to object';
  END IF;
  
  -- Generate signed URL (24 hour expiration)
  SELECT storage.create_signed_url(bucket_name, object_path, 86400) INTO signed_url;
  
  RETURN signed_url;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION generate_signed_url TO authenticated;