-- ============================================================================
-- Supabase Database Schema for Piano Transcription App
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================================
-- TRANSCRIPTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    audio_url TEXT NOT NULL,
    sheet_music_url TEXT,
    transcription_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;

-- Users table policies
-- Users can read their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT
    USING (auth.uid() = id);

-- Users can update their own data
CREATE POLICY "Users can update own data" ON users
    FOR UPDATE
    USING (auth.uid() = id);

-- Transcriptions table policies
-- Users can view their own transcriptions
CREATE POLICY "Users can view own transcriptions" ON transcriptions
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own transcriptions
CREATE POLICY "Users can create own transcriptions" ON transcriptions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own transcriptions
CREATE POLICY "Users can update own transcriptions" ON transcriptions
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own transcriptions
CREATE POLICY "Users can delete own transcriptions" ON transcriptions
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- UPDATED_AT TRIGGER
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for transcriptions table
CREATE TRIGGER update_transcriptions_updated_at BEFORE UPDATE ON transcriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STORAGE BUCKETS (Run in Supabase Dashboard > Storage)
-- ============================================================================

-- Create storage bucket for transcriptions
-- Run this in the Supabase Dashboard SQL Editor:
/*
INSERT INTO storage.buckets (id, name, public)
VALUES ('transcriptions', 'transcriptions', true);
*/

-- Storage policies (allow authenticated users to upload/delete their own files)
/*
-- Policy to allow users to upload files to their own folder
CREATE POLICY "Users can upload own files" ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'transcriptions' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- Policy to allow users to view files
CREATE POLICY "Users can view files" ON storage.objects
    FOR SELECT
    USING (bucket_id = 'transcriptions');

-- Policy to allow users to delete their own files
CREATE POLICY "Users can delete own files" ON storage.objects
    FOR DELETE
    USING (
        bucket_id = 'transcriptions' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );
*/

-- ============================================================================
-- SAMPLE QUERIES (for testing)
-- ============================================================================

-- Get all users (admin only)
-- SELECT * FROM users;

-- Get all transcriptions for a specific user
-- SELECT * FROM transcriptions WHERE user_id = 'user-uuid-here';

-- Get transcription count per user
-- SELECT user_id, COUNT(*) as transcription_count
-- FROM transcriptions
-- GROUP BY user_id;

-- Get total storage used per user
-- SELECT user_id, SUM(LENGTH(transcription_data::text)) as total_data_size
-- FROM transcriptions
-- GROUP BY user_id;