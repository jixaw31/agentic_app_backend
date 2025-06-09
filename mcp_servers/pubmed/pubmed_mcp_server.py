from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional
import asyncio
import logging
from mcp.server.fastmcp import FastMCP
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





if __name__ == "__main__":
    logging.info("Starting medRxiv MCP server")

    mcp.run(transport='streamable_http')
    # mcp.run(transport='stdio')
    
