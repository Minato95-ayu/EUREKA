from app.agents.base_agent import BaseAgent
from typing import Dict, Any, List
import logging
import httpx
import json
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class ResearchIntegratorAgent(BaseAgent):
    """Integrates research knowledge from global sources"""
    
    def __init__(self, ollama_service):
        super().__init__(ollama_service, "ResearchIntegrator")
        self.arxiv_base = "http://export.arxiv.org/api/query?"
        self.http_client = httpx.AsyncClient()
    
    def _get_system_prompt(self) -> str:
        return """You are the EUREKA Research Integrator Agent. Your role is to 
connect experiments with global research knowledge.

Your expertise:
- Research paper discovery
- Literature review
- Citation management
- Trend analysis
- Knowledge synthesis
- Gap identification

When integrating research:
1. Search relevant databases (ArXiv, PubMed)
2. Find similar experiments
3. Compare results with literature
4. Provide relevant citations
5. Identify research gaps
6. Suggest future directions
7. Highlight contradictions/confirmations

Always:
- Provide paper titles and links
- Include publication dates
- Note relevance scores
- Suggest related work
- Identify emerging trends"""
    
    async def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search ArXiv for relevant papers"""
        try:
            # Clean query for URL safety
            clean_query = query.replace('"', '').replace("'", "").strip()
            search_query = f"search_query=all:{clean_query}&max_results={max_results}"
            response = await self.http_client.get(self.arxiv_base + search_query)
            
            papers = []
            if response.status_code == 200:
                # ArXiv returns response in Atom XML format
                root = ET.fromstring(response.text)
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
                    # Remove extra whitespace/newlines from XML text
                    title = " ".join(title.split())
                    
                    abstract = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
                    abstract = " ".join(abstract.split())
                    
                    published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""
                    url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
                    
                    papers.append({
                        "title": title,
                        "authors": authors,
                        "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                        "url": url,
                        "published": published
                    })
                
                logger.info(f"Found {len(papers)} papers for query: '{query}'")
            else:
                logger.error(f"ArXiv API error: {response.status_code}")
            
            return papers
        except Exception as e:
            logger.error(f"ArXiv search error: {str(e)}")
            return []
    
    async def process(self, request: Dict[str, Any]) -> str:
        """Process research integration request"""
        
        query = request.get("query", "")
        molecule = request.get("molecule", "")
        context = request.get("context", {})
        
        context_str = self._build_context(context)
        
        # Search for relevant papers
        search_term = query or molecule or "chemistry simulation"
        papers = await self.search_arxiv(search_term, max_results=5)
        papers_str = json.dumps(papers, indent=2)
        
        prompt = f"""{context_str}

Research Query: {search_term}

Related Papers Found:
{papers_str}

Provide:
1. Summary of relevant research
2. Key findings from literature
3. How current experiment relates to existing work
4. Research gaps identified
5. Suggested citations
6. Emerging trends in this area
7. Recommendations for further research"""
        
        response = await self.generate_response(prompt)
        logger.info(f"Research Integrator processed: {search_term[:50]}...")
        
        return response

async def integrate_research(ollama_service, query: str):
    agent = ResearchIntegratorAgent(ollama_service)
    request = {
        "query": query,
        "molecule": query
    }
    return await agent.process(request)
