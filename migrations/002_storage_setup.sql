# Supabase Storage Setup for Teacher Documents

## Create Bucket
1. In Supabase dashboard, go to **Storage**
2. Click **"Create a new bucket"**
3. Name: `teacher-documents`
4. Public bucket: **OFF**
5. File size limit: `50MB`
6. Allowed MIME types: `application/pdf`
7. Click **"Create bucket"**

## Storage Policies
Run these in Supabase SQL Editor after creating the bucket:

```sql
-- Allow authenticated teachers and admins to upload
CREATE POLICY "Allow uploads for authenticated users"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'teacher-documents' AND
  auth.uid() IN (SELECT id FROM users WHERE role IN ('teacher', 'admin'))
);

-- Allow authenticated teachers and admins to view
CREATE POLICY "Allow view for authenticated users"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'teacher-documents' AND
  auth.uid() IN (SELECT id FROM users WHERE role IN ('teacher', 'admin'))
);

-- Allow admins to delete
CREATE POLICY "Allow delete for admins"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'teacher-documents' AND
  auth.uid() IN (SELECT id FROM users WHERE role = 'admin')
);
```
