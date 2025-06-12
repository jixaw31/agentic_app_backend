import httpx, json, os, asyncio, logging
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional, Literal

from medrxiv.medrxiv_web_search import search_key_words,\
      search_advanced, doi_get_medrxiv_metadata

# Create an MCP server
mcp = FastMCP("PubMedMCP",
              host="127.0.0.1", 
              port=8001,     
)

class SearchAbstractsRequest(BaseModel):
    """
    Request parameters for NCBI ESearch API for searching abstracts on the PubMed database.

    Functions:
        - Provides a list of abstracts matching a text query

    Examples:
        >>> # Basic search in PubMed for 'asthma' articles abstracts
        >>> SearchAbstractsRequest(term="asthma")

        >>> # Search with publication date range
        >>> ESearchRequest(
        ...     term="asthma",
        ...     mindate="2020/01/01",
        ...     maxdate="2020/12/31",
        ...     datetype="pdat"
        ... )

        >>> # Search with field restriction
        >>> ESearchRequest(term="asthma[title]")
        >>> # Or equivalently:
        >>> ESearchRequest(term="asthma", field="title")

        >>> # Search with proximity operator
        >>> ESearchRequest(term='"asthma treatment"[Title:~3]')

        >>> # Sort results by publication date
        >>> ESearchRequest(
        ...     term="asthma",
        ...     sort="pub_date"
        ... )
    """

    term: str = Field(
        ...,
        description="""Entrez text query. All special characters must be URL encoded. 
        Spaces may be replaced by '+' signs. For very long queries (more than several 
        hundred characters), consider using an HTTP POST call. See PubMed or Entrez 
        help for information about search field descriptions and tags. Search fields 
        and tags are database specific.""",
    )

    retmax: Optional[int] = Field(
        None,
        description="""Number of UIDs to return (default=20, max=10000).""",
    )

    sort: Optional[str] = Field(
        "relevance",
        description="""Sort method for results. PubMed values:
        - pub_date: descending sort by publication date
        - Author: ascending sort by first author
        - JournalName: ascending sort by journal name
        - relevance: default sort order ("Best Match")""",
    )
    field: Optional[str] = Field(
        None,
        description="""Search field to limit entire search. Equivalent to adding [field] 
        to term.""",
    )
    datetype: Optional[Literal["mdat", "pdat", "edat"]] = Field(
        None,
        description="""Type of date used to limit search:
        - mdat: modification date
        - pdat: publication date
        - edat: Entrez date
        Generally databases have only two allowed values.""",
    )
    reldate: Optional[int] = Field(
        None,
        description="""When set to n, returns items with datetype within the last n 
        days.""",
    )
    mindate: Optional[str] = Field(
        None,
        description="""Start date for date range. Format: YYYY/MM/DD, YYYY/MM, or YYYY. 
        Must be used with maxdate.""",
    )
    maxdate: Optional[str] = Field(
        None,
        description="""End date for date range. Format: YYYY/MM/DD, YYYY/MM, or YYYY. 
        Must be used with mindate.""",
    )


@mcp.tool()
async def search_abstracts(
    term: str,
    mindate: Optional[str] = None,
    maxdate: Optional[str] = None,
    retmax: int = 7,
    sort: str = "relevance",
) -> dict:
    """Optimized: Search PubMed and return key info from top abstracts."""
    request = SearchAbstractsRequest(term=term, mindate=mindate, maxdate=maxdate, retmax=retmax,
                                     sort=sort)


    async with pubmedclient_client() as client:
        search = await esearch(client, ESearchRequest(db=Db.PUBMED, **request.model_dump()))
        ids = search.esearchresult.idlist

        if not ids:
            return {"results": []}

        fetch = await efetch(
            client,
            EFetchRequest(db=Db.PUBMED, id=",".join(ids), retmode="xml", rettype="abstract")
        )

        # Parse and compress abstracts
        from xml.etree import ElementTree as ET
        root = ET.fromstring(fetch)
        articles = []

        for article in root.findall(".//PubmedArticle"):
            try:
                title = article.findtext(".//ArticleTitle")
                abstract = article.findtext(".//AbstractText")
                abstract = abstract.strip()
                if len(abstract) > 500:
                    abstract = abstract[:500] + "..."
                pmid = article.findtext(".//PMID")
                if title and abstract:
                    articles.append({
                        "title": title.strip(),
                        "abstract": abstract.strip(),
                        "pmid": pmid
                    })
            except Exception:
                continue
        print(f"number of articles: {len(articles)}")
        return {"results": articles}



# command to run this mcp server:
# python mcp_servers\pubmed_mcp_server.py



# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@mcp.tool()
async def search_medrxiv_key_words(key_words: str, num_results: int = 10) -> List[Dict[str, Any]]:
    logging.info(f"Searching for articles with key words: {key_words}, num_results: {num_results}")
    """
    Search for articles on medRxiv using key words.

    Args:
        key_words: Search query string
        num_results: Number of results to return (default: 10)

    Returns:
        List of dictionaries containing article information
    """
    try:
        results = await asyncio.to_thread(search_key_words, key_words, num_results)
        return results
    except Exception as e:
        return [{"error": f"An error occurred while searching: {str(e)}"}]

@mcp.tool()
async def search_medrxiv_advanced(
    term: Optional[str] = None,
    title: Optional[str] = None,
    author1: Optional[str] = None,
    author2: Optional[str] = None,
    abstract_title: Optional[str] = None,
    text_abstract_title: Optional[str] = None,
    section: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    num_results: int = 10
) -> List[Dict[str, Any]]:
    logging.info(f"Performing advanced search with parameters: {locals()}")
    """
    Perform an advanced search for articles on medRxiv.

    Args:
        term: General search term
        title: Search in title
        author1: First author
        author2: Second author
        abstract_title: Search in abstract and title
        text_abstract_title: Search in full text, abstract, and title
        section: Section of medRxiv
        start_date: Start date for search range (format: YYYY-MM-DD)
        end_date: End date for search range (format: YYYY-MM-DD)
        num_results: Number of results to return (default: 10)

    Returns:
        List of dictionaries containing article information
    """
    try:
        results = await asyncio.to_thread(
            search_advanced,
            term, title, author1, author2, abstract_title, text_abstract_title,
            section, start_date, end_date, num_results
        )
        return results
    except Exception as e:
        return [{"error": f"An error occurred while performing advanced search: {str(e)}"}]

@mcp.tool()
async def get_medrxiv_metadata(doi: str) -> Dict[str, Any]:
    logging.info(f"Fetching metadata for DOI: {doi}")
    """
    Fetch metadata for a medRxiv article using its DOI.

    Args:
        doi: DOI of the article

    Returns:
        Dictionary containing article metadata
    """
    try:
        metadata = await asyncio.to_thread(doi_get_medrxiv_metadata, doi)
        return metadata if metadata else {"error": f"No metadata found for DOI: {doi}"}
    except Exception as e:
        return {"error": f"An error occurred while fetching metadata: {str(e)}"}




load_dotenv()

SERPER_URL = "https://google.serper.dev/search"

urls = {
    "NICE": "www.nice.org.uk/"
}



async def search_web(query: str) -> dict | None:
    payload = json.dumps({"q": query, "num": 3})
    
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SERPER_URL, headers=headers, data=payload, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"organic": []}


async def fetch_url(url: str) -> str:
   async with httpx.AsyncClient() as client:
       try:
           response = await client.get(url, timeout=30.0)
           soup = BeautifulSoup(response.text, "html.parser")
           text = soup.get_text()
           return text
       except httpx.TimeoutException:
           return "Timeout error"


@mcp.tool()
async def get_nice_guidance(query: str) -> str:
    """
    Get guidance for a given topic from NICE.

    Args:
        query (str): The topic to get guidance for (eg. "high blood pressure")

    Returns:
        str: The guidance for the given topic.
    """

    # expand this to other guidance sources, using urls dict above

    query = f"site:{urls['NICE']} {query}"
    results = await search_web(query)
    if len(results["organic"]) == 0:
        return "No results found"
       
    text = ""
    for result in results["organic"]:
        text += await fetch_url(result["link"])
    return text



if __name__ == "__main__":
    logging.info("Starting medRxiv MCP server")
    
    # mcp.run(transport='stdio')
    mcp.run(transport='streamable_http')






