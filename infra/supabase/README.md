# Supabase Configuration

This directory contains Supabase configuration files for the AI CV Agent project.

## Setup Instructions

1. Create a new Supabase project at https://supabase.com
2. Copy your project URL and API keys to the `.env` file in the agent directory
3. Run the SQL migrations in the `migrations/` directory
4. Configure authentication settings in the Supabase dashboard
5. Set up storage buckets for document storage

## Database Schema

The database schema includes:
- User authentication (handled by Supabase Auth)
- User profiles with comprehensive career information
- Job processing and status tracking
- Document storage metadata
- Row-level security policies for data isolation

## Authentication

- Email/password authentication
- Magic link support
- JWT token-based API authentication
- Row-level security for data isolation