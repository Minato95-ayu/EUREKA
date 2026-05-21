from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json
import httpx
import uuid
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, Column, String, Text, DateTime, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class ResearchPaper(Base):
    """Research paper model"""
    __tablename__ = "research_papers"
    
    id = Column(String, primary_key=True)
    arxiv_id = Column(String, unique=True, nullable=True)
    pubmed_id = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=False)
    authors = Column(JSON, nullable=True)
    abstract = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    keywords = Column(JSON, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    relevance_score = Column(String, default="0.0")
    cached_at = Column(DateTime, default=datetime.utcnow)
    # Using 'metadata' as the DB column but mapping to 'paper_metadata' in Python to avoid SQLAlchemy naming conflict
    paper_metadata = Column("metadata", JSON, nullable=True)

class ResearchDatabaseService:
    """Manages research paper database and semantic search"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.arxiv_base = "http://export.arxiv.org/api/query?"
        self.http_client = httpx.AsyncClient()
        self.is_offline = False
        
        try:
            self.engine = create_engine(db_url)
            self.Session = sessionmaker(bind=self.engine)
            # Verify connectivity
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("ResearchDatabaseService connected to PostgreSQL successfully.")
        except Exception as e:
            logger.warning(f"ResearchDatabaseService database connection failed: {e}. Running in offline fallback mode.")
            self.is_offline = True
            self.Session = None
            self.engine = None
            
        # In-memory fallback cache
        self._fallback_cache: Dict[str, Dict] = {}
    
    async def search_arxiv(
        self, 
        query: str, 
        max_results: int = 10,
        sort_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """Search ArXiv for papers"""
        try:
            clean_query = query.replace('"', '').replace("'", "").strip()
            search_query = f"search_query=all:{clean_query}&max_results={max_results}&sortBy={sort_by}"
            
            response = await self.http_client.get(self.arxiv_base + search_query)
            
            if response.status_code == 200:
                papers = self._parse_arxiv_response(response.text)
                
                # Cache papers
                for paper in papers:
                    await self._cache_paper(paper)
                
                logger.info(f"Found {len(papers)} papers on ArXiv for: {query}")
                return papers
            else:
                logger.error(f"ArXiv API returned status code: {response.status_code}")
                return []
            
        except Exception as e:
            logger.error(f"ArXiv search error: {str(e)}")
            return []
    
    async def search_pubmed(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search PubMed for papers"""
        try:
            # Step 1: Search for PubMed IDs
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }
            
            response = await self.http_client.get(search_url, params=params)
            if response.status_code != 200:
                logger.error(f"PubMed Search API returned status: {response.status_code}")
                return []
                
            esearch_data = response.json()
            id_list = esearch_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                logger.info(f"No papers found on PubMed for query: {query}")
                return []
                
            # Step 2: Fetch Summary Details for PubMed IDs
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            summary_response = await self.http_client.get(summary_url, params=summary_params)
            if summary_response.status_code != 200:
                logger.error(f"PubMed Summary API returned status: {summary_response.status_code}")
                return []
                
            papers = self._parse_pubmed_response(summary_response.json())
            
            # Cache papers
            for paper in papers:
                await self._cache_paper(paper)
            
            logger.info(f"Found {len(papers)} papers on PubMed for: {query}")
            return papers
            
        except Exception as e:
            logger.error(f"PubMed search error: {str(e)}")
            return []
    
    async def semantic_search(
        self, 
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic search using embeddings"""
        try:
            if self.is_offline or not self.Session:
                # Offline fallback: return in-memory cache values
                papers = list(self._fallback_cache.values())[:top_k]
            else:
                session = self.Session()
                try:
                    # In production, use pgvector cosine distance: ORDER BY embedding <=> :emb
                    # Here we fetch papers and simulate or use pgvector if available
                    has_vector = False
                    try:
                        session.execute(text("SELECT 'vector'::regclass"))
                        has_vector = True
                    except Exception:
                        pass
                        
                    if has_vector and query_embedding:
                        # pgvector query
                        vector_str = f"[{','.join(map(str, query_embedding))}]"
                        raw_query = text("""
                            SELECT id, arxiv_id, pubmed_id, title, authors, abstract, url, keywords, 
                                   (1 - (embedding <=> :emb))::text as relevance_score 
                            FROM research_papers 
                            ORDER BY embedding <=> :emb 
                            LIMIT :limit
                        """)
                        db_result = session.execute(raw_query, {"emb": vector_str, "limit": top_k}).fetchall()
                        result = [
                            {
                                "id": r[0],
                                "title": r[3],
                                "authors": r[4],
                                "abstract": r[5],
                                "url": r[6],
                                "relevance_score": r[8] or "0.0"
                            }
                            for r in db_result
                        ]
                        return result
                    else:
                        db_papers = session.query(ResearchPaper).limit(top_k).all()
                        result = [
                            {
                                "id": p.id,
                                "title": p.title,
                                "authors": p.authors,
                                "abstract": p.abstract,
                                "url": p.url,
                                "relevance_score": p.relevance_score
                            }
                            for p in db_papers
                        ]
                        return result
                finally:
                    session.close()
            
            return [
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "authors": p.get("authors"),
                    "abstract": p.get("abstract"),
                    "url": p.get("url"),
                    "relevance_score": p.get("relevance_score", "0.0")
                }
                for p in papers
            ]
            
        except Exception as e:
            logger.error(f"Semantic search error: {str(e)}")
            return []
    
    async def _cache_paper(self, paper: Dict[str, Any]):
        """Cache paper in database or in-memory fallback"""
        # Always store in memory fallback
        self._fallback_cache[paper.get("id")] = paper
        
        if self.is_offline or not self.Session:
            return
            
        try:
            session = self.Session()
            try:
                existing = None
                if paper.get("arxiv_id"):
                    existing = session.query(ResearchPaper).filter_by(arxiv_id=paper.get("arxiv_id")).first()
                elif paper.get("pubmed_id"):
                    existing = session.query(ResearchPaper).filter_by(pubmed_id=paper.get("pubmed_id")).first()
                
                if not existing:
                    new_paper = ResearchPaper(
                        id=paper.get("id", str(uuid.uuid4())),
                        arxiv_id=paper.get("arxiv_id"),
                        pubmed_id=paper.get("pubmed_id"),
                        title=paper.get("title", ""),
                        authors=paper.get("authors", []),
                        abstract=paper.get("abstract", ""),
                        url=paper.get("url", ""),
                        keywords=paper.get("keywords", []),
                        publication_date=paper.get("publication_date"),
                        paper_metadata=paper.get("metadata", {})
                    )
                    session.add(new_paper)
                    session.commit()
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Cache paper error: {str(e)}")
    
    def _parse_arxiv_response(self, xml_response: str) -> List[Dict]:
        """Parse ArXiv XML response using ET"""
        papers = []
        try:
            root = ET.fromstring(xml_response)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                published_elem = entry.find('atom:published', ns)
                id_elem = entry.find('atom:id', ns)
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name_elem = author.find('atom:name', ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())
                
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Untitled"
                title = " ".join(title.split())
                
                abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
                abstract = " ".join(abstract.split())
                
                published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
                url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                
                # Extract clean arxiv ID
                arxiv_id = url.split("/abs/")[-1].split("v")[0] if "/abs/" in url else str(uuid.uuid4())
                
                # Simple keyword generation based on title words
                keywords = [word.lower() for word in title.split() if len(word) > 4][:5]
                
                pub_date = None
                if published:
                    try:
                        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    except Exception:
                        pass
                
                papers.append({
                    "id": arxiv_id,
                    "arxiv_id": arxiv_id,
                    "pubmed_id": None,
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "url": url,
                    "keywords": keywords,
                    "publication_date": pub_date,
                    "metadata": {}
                })
        except Exception as e:
            logger.error(f"Error parsing ArXiv XML: {e}")
        return papers
    
    def _parse_pubmed_response(self, json_response: Dict) -> List[Dict]:
        """Parse PubMed JSON response"""
        papers = []
        try:
            result = json_response.get("result", {})
            uids = result.get("uids", [])
            
            for uid in uids:
                paper_info = result.get(uid, {})
                title = paper_info.get("title", "Untitled")
                
                authors = []
                for author in paper_info.get("authors", []):
                    name = author.get("name")
                    if name:
                        authors.append(name)
                
                pubdate_str = paper_info.get("pubdate", "")
                pub_date = None
                if pubdate_str:
                    try:
                        year = pubdate_str.split()[0]
                        pub_date = datetime(int(year), 1, 1)
                    except Exception:
                        pass
                
                doi = ""
                for articleid in paper_info.get("articleids", []):
                    if articleid.get("idtype") == "doi":
                        doi = articleid.get("value", "")
                        
                url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                
                keywords = [word.lower() for word in title.split() if len(word) > 4][:5]
                
                papers.append({
                    "id": uid,
                    "arxiv_id": None,
                    "pubmed_id": uid,
                    "title": title,
                    "authors": authors,
                    "abstract": paper_info.get("source", "") + " " + pubdate_str,
                    "url": url,
                    "keywords": keywords,
                    "publication_date": pub_date,
                    "metadata": {"doi": doi, "source": paper_info.get("source")}
                })
        except Exception as e:
            logger.error(f"Error parsing PubMed JSON: {e}")
        return papers
    
    async def get_related_papers(
        self, 
        paper_id: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Get papers related to a given paper based on keyword overlaps in Python"""
        try:
            # 1. Fetch paper keywords
            paper_keywords = []
            
            if self.is_offline or not self.Session:
                paper = self._fallback_cache.get(paper_id)
                if paper:
                    paper_keywords = paper.get("keywords", [])
            else:
                session = self.Session()
                try:
                    paper = session.query(ResearchPaper).filter_by(id=paper_id).first()
                    if paper:
                        paper_keywords = paper.keywords or []
                finally:
                    session.close()
            
            if not paper_keywords:
                return []
                
            # 2. Get all papers to compare overlaps
            all_papers = []
            if self.is_offline or not self.Session:
                all_papers = list(self._fallback_cache.values())
            else:
                session = self.Session()
                try:
                    db_papers = session.query(ResearchPaper).all()
                    all_papers = [
                        {
                            "id": p.id,
                            "title": p.title,
                            "authors": p.authors,
                            "url": p.url,
                            "keywords": p.keywords or []
                        }
                        for p in db_papers
                    ]
                finally:
                    session.close()
                    
            # 3. Filter by overlapping keywords (in Python to avoid SQL-dialect failures)
            related = []
            target_set = set(paper_keywords)
            
            for p in all_papers:
                if p["id"] == paper_id:
                    continue
                overlap = target_set.intersection(set(p.get("keywords", [])))
                if overlap:
                    related.append((len(overlap), p))
                    
            # Sort by overlap size descending
            related.sort(key=lambda x: x[0], reverse=True)
            
            result = [
                {
                    "id": p[1]["id"],
                    "title": p[1]["title"],
                    "authors": p[1]["authors"],
                    "url": p[1]["url"]
                }
                for p in related[:max_results]
            ]
            
            return result
            
        except Exception as e:
            logger.error(f"Get related papers error: {str(e)}")
            return []
            
    async def close(self):
        """Close connection client"""
        try:
            await self.http_client.aclose()
        except Exception:
            pass
