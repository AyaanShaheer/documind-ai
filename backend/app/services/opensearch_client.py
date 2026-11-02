
import logging

from functools import lru_cache

from opensearchpy import OpenSearch

from app.core.config import settings


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_opensearch_client() -> OpenSearch:
    """
    Create and reuse an OpenSearch connection.

    Floci local domain:
        HTTP, without authentication.

    Production:
        Authentication and TLS will be configured
        separately for Amazon OpenSearch Service.
    """

    client = OpenSearch(
        hosts=[
            {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
            }
        ],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )

    return client


