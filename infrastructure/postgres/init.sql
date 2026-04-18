-- PostgreSQL initialization script for QuantumWealth

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- fast LIKE searches
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- GIN index support

-- Create dedicated role if needed (in case user doesn't exist from env)
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'qwuser') THEN
    CREATE ROLE qwuser LOGIN PASSWORD 'qwpassword';
  END IF;
END $$;

GRANT ALL PRIVILEGES ON DATABASE quantumwealth TO qwuser;
