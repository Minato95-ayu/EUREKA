-- EUREKA Database Initialization Script
-- Creates all tables from Phase 3-5 migrations

-- Try to enable pgvector extension if available
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pgvector extension not available. Skipping vector support.';
END
$$;

-- 1. Agent Conversations (Phase 3)
CREATE TABLE IF NOT EXISTS agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR,
    user_id UUID,
    user_message TEXT NOT NULL,
    agent_used VARCHAR[],
    agent_responses JSONB,
    unified_response TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_experiment ON agent_conversations(experiment_id);

-- 2. Research Papers (Phase 3)
-- Create with embedding column if pgvector is available, otherwise without
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE TABLE IF NOT EXISTS research_papers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            arxiv_id VARCHAR UNIQUE,
            pubmed_id VARCHAR UNIQUE,
            title VARCHAR NOT NULL,
            authors TEXT[],
            abstract TEXT,
            url VARCHAR,
            keywords TEXT[],
            embedding VECTOR(1536),
            cached_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ELSE
        CREATE TABLE IF NOT EXISTS research_papers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            arxiv_id VARCHAR UNIQUE,
            pubmed_id VARCHAR UNIQUE,
            title VARCHAR NOT NULL,
            authors TEXT[],
            abstract TEXT,
            url VARCHAR,
            keywords TEXT[],
            cached_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    END IF;
END
$$;

-- GIN index on keywords for efficient array lookups
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_research_papers_keywords ON research_papers USING GIN(keywords);
EXCEPTION
    WHEN OTHERS THEN
        CREATE INDEX IF NOT EXISTS idx_research_papers_keywords ON research_papers(keywords);
END
$$;

-- 3. Agent Metrics (Phase 3)
CREATE TABLE IF NOT EXISTS agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR NOT NULL,
    request_type VARCHAR,
    response_time_ms INT,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent ON agent_metrics(agent_name);

-- 4. Simulations (Phase 4)
CREATE TABLE IF NOT EXISTS simulations (
    id VARCHAR PRIMARY KEY,
    experiment_id VARCHAR,
    name VARCHAR NOT NULL,
    description TEXT,
    type VARCHAR,
    status VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_simulations_experiment ON simulations(experiment_id);

-- 5. Simulation Particles (Phase 4)
CREATE TABLE IF NOT EXISTS simulation_particles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id VARCHAR REFERENCES simulations(id) ON DELETE CASCADE,
    particle_type VARCHAR,
    position FLOAT8[],
    velocity FLOAT8[],
    mass FLOAT8,
    charge FLOAT8,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_simulation_particles_simulation ON simulation_particles(simulation_id);

-- 6. Simulation Results (Phase 4)
CREATE TABLE IF NOT EXISTS simulation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id VARCHAR REFERENCES simulations(id) ON DELETE CASCADE,
    trajectory JSONB,
    energies FLOAT8[],
    final_energy FLOAT8,
    simulation_time FLOAT8,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_simulation_results_simulation ON simulation_results(simulation_id);

-- 7. Simulation Reactions (Phase 4)
CREATE TABLE IF NOT EXISTS simulation_reactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id VARCHAR REFERENCES simulations(id) ON DELETE CASCADE,
    reactants TEXT[],
    products TEXT[],
    energy_change FLOAT8,
    feasible BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_simulation_reactions_simulation ON simulation_reactions(simulation_id);

-- 8. Collaborations (Phase 5)
CREATE TABLE IF NOT EXISTS collaborations (
    id VARCHAR PRIMARY KEY,
    experiment_id VARCHAR,
    owner_id VARCHAR,
    title VARCHAR NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_collaborations_experiment ON collaborations(experiment_id);

-- 9. Collaboration Members (Phase 5)
CREATE TABLE IF NOT EXISTS collaboration_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collaboration_id VARCHAR REFERENCES collaborations(id) ON DELETE CASCADE,
    user_id VARCHAR,
    role VARCHAR,
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(collaboration_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_collaboration_members_user ON collaboration_members(user_id);

-- 10. Comments (Phase 5)
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collaboration_id VARCHAR REFERENCES collaborations(id) ON DELETE CASCADE,
    user_id VARCHAR,
    text TEXT NOT NULL,
    line_number INT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comments_collaboration ON comments(collaboration_id);

-- 11. Experiment Versions (Phase 5)
CREATE TABLE IF NOT EXISTS experiment_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collaboration_id VARCHAR REFERENCES collaborations(id) ON DELETE CASCADE,
    user_id VARCHAR,
    data JSONB,
    message VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_experiment_versions_collaboration ON experiment_versions(collaboration_id);
