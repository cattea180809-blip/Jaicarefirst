import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://moubjbxzopdqwoufpont.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vdWJqYnh6b3BkcXdvdWZwb250Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUxMzQxMTEsImV4cCI6MjEwMDcxMDExMX0.pmcJWr2yamp--6Zo1Sf2QGfdzBL2Rwri1a70ExlE1U4'

export const supabase = createClient(supabaseUrl, supabaseKey) 