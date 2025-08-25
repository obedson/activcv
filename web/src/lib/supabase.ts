import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export type Database = {
  core: {
    Tables: {
      profiles: {
        Row: {
          user_id: string
          headline: string | null
          summary: string | null
          linkedin_url: string | null
          website_url: string | null
          additional_details: string | null
          last_updated: string
          created_at: string
        }
        Insert: {
          user_id: string
          headline?: string | null
          summary?: string | null
          linkedin_url?: string | null
          website_url?: string | null
          additional_details?: string | null
          last_updated?: string
          created_at?: string
        }
        Update: {
          user_id?: string
          headline?: string | null
          summary?: string | null
          linkedin_url?: string | null
          website_url?: string | null
          additional_details?: string | null
          last_updated?: string
          created_at?: string
        }
      }
      // Add other table types as needed
    }
  }
}