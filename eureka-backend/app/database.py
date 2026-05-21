from sqlalchemy import create_engine, text
from app.config import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.is_connected = False
        self._init_db()
        
    def _init_db(self):
        try:
            # Try connecting to PostgreSQL using configured DATABASE_URL
            self.engine = create_engine(
                self.settings.DATABASE_URL,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully.")
            self.is_connected = True
            
            # Run table migrations
            self._run_migrations()
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Running in offline database mode.")
            self.is_connected = False
            
    def _run_migrations(self):
        if not self.is_connected or not self.engine:
            return
        
        try:
            with self.engine.begin() as conn:
                # 1. Create agent_conversations
                conn.execute(text("""
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
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_conversations_experiment ON agent_conversations(experiment_id)"))
                
                # 2. Try to enable vector extension if possible
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    has_vector = True
                except Exception:
                    logger.warning("pgvector extension not available. Skipping embedding vector database column.")
                    has_vector = False
                
                # 3. Create research_papers
                if has_vector:
                    conn.execute(text("""
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
                        )
                    """))
                else:
                    conn.execute(text("""
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
                        )
                    """))
                
                # GIN index on keywords (using standard indexing if GIN is not supported or falls back)
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_research_papers_keywords ON research_papers USING GIN(keywords)"))
                except Exception:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_research_papers_keywords ON research_papers(keywords)"))
                
                # 4. Create agent_metrics
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS agent_metrics (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      agent_name VARCHAR NOT NULL,
                      request_type VARCHAR,
                      response_time_ms INT,
                      success BOOLEAN,
                      error_message TEXT,
                      created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent ON agent_metrics(agent_name)"))
                
                # 5. Create simulations (Phase 4)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS simulations (
                      id VARCHAR PRIMARY KEY,
                      experiment_id VARCHAR,
                      name VARCHAR NOT NULL,
                      description TEXT,
                      type VARCHAR,
                      status VARCHAR,
                      created_at TIMESTAMP DEFAULT NOW(),
                      updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simulations_experiment ON simulations(experiment_id)"))
                
                # 6. Create simulation_particles (Phase 4)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS simulation_particles (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      simulation_id VARCHAR REFERENCES simulations(id) ON DELETE CASCADE,
                      particle_type VARCHAR,
                      position FLOAT8[],
                      velocity FLOAT8[],
                      mass FLOAT8,
                      charge FLOAT8,
                      created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simulation_particles_simulation ON simulation_particles(simulation_id)"))
                
                # 7. Create simulation_results (Phase 4)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS simulation_results (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      simulation_id VARCHAR REFERENCES simulations(id) ON DELETE CASCADE,
                      trajectory JSONB,
                      energies FLOAT8[],
                      final_energy FLOAT8,
                      simulation_time FLOAT8,
                      created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simulation_results_simulation ON simulation_results(simulation_id)"))
                
                # 8. Create simulation_reactions (Phase 4)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS simulation_reactions (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      simulation_id VARCHAR REFERENCES simulations(id) ON DELETE CASCADE,
                      reactants TEXT[],
                      products TEXT[],
                      energy_change FLOAT8,
                      feasible BOOLEAN,
                      created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_simulation_reactions_simulation ON simulation_reactions(simulation_id)"))
                
                # 9. Create collaborations (Phase 5)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS collaborations (
                      id VARCHAR PRIMARY KEY,
                      experiment_id VARCHAR,
                      owner_id VARCHAR,
                      title VARCHAR NOT NULL,
                      description TEXT,
                      is_public BOOLEAN DEFAULT FALSE,
                      created_at TIMESTAMP DEFAULT NOW(),
                      updated_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_collaborations_experiment ON collaborations(experiment_id)"))

                # 10. Create collaboration_members (Phase 5)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS collaboration_members (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      collaboration_id VARCHAR REFERENCES collaborations(id) ON DELETE CASCADE,
                      user_id VARCHAR,
                      role VARCHAR,
                      joined_at TIMESTAMP DEFAULT NOW(),
                      UNIQUE(collaboration_id, user_id)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_collaboration_members_user ON collaboration_members(user_id)"))

                # 11. Create comments (Phase 5)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comments (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      collaboration_id VARCHAR REFERENCES collaborations(id) ON DELETE CASCADE,
                      user_id VARCHAR,
                      text TEXT NOT NULL,
                      line_number INT,
                      created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_comments_collaboration ON comments(collaboration_id)"))

                # 12. Create experiment_versions (Phase 5)
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS experiment_versions (
                      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      collaboration_id VARCHAR REFERENCES collaborations(id) ON DELETE CASCADE,
                      user_id VARCHAR,
                      data JSONB,
                      message VARCHAR,
                      created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_experiment_versions_collaboration ON experiment_versions(collaboration_id)"))
                
            logger.info("Database migrations applied successfully.")
        except Exception as e:
            logger.error(f"Error running database migrations: {e}")
            
    async def execute(self, query: str, *args):
        """Execute query in threadpool to remain non-blocking"""
        if not self.is_connected or not self.engine:
            logger.warning(f"Database offline. Skipping query: '{query.strip().splitlines()[0]}...'")
            return None
        try:
            def run_query():
                with self.engine.begin() as conn:
                    # Convert PostgreSQL param placeholders ($1, $2...) to SQLAlchemy (:p1, :p2...)
                    formatted_query = query
                    params = {}
                    for idx, val in enumerate(args):
                        placeholder = f"${idx+1}"
                        param_name = f"p{idx+1}"
                        formatted_query = formatted_query.replace(placeholder, f":{param_name}")
                        params[param_name] = val
                    conn.execute(text(formatted_query), params)
            await asyncio.to_thread(run_query)
        except Exception as e:
            logger.error(f"Database query error: {e}")
            
db = Database()
