import logging

import httpx

logger = logging.getLogger("bioaf.package_search")


class PackageSearchService:
    @staticmethod
    async def search_packages(
        query: str,
        sources: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search for packages across multiple registries."""
        if sources is None:
            sources = ["conda", "pip", "cran", "bioconductor"]

        results = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            if "conda" in sources:
                try:
                    conda_results = await PackageSearchService._search_conda(client, query, limit)
                    results.extend(conda_results)
                except Exception as e:
                    logger.warning("Conda search failed: %s", e)

            if "pip" in sources:
                try:
                    pip_results = await PackageSearchService._search_pip(client, query, limit)
                    results.extend(pip_results)
                except Exception as e:
                    logger.warning("PyPI search failed: %s", e)

            if "cran" in sources:
                try:
                    cran_results = await PackageSearchService._search_cran(client, query, limit)
                    results.extend(cran_results)
                except Exception as e:
                    logger.warning("CRAN search failed: %s", e)

            if "bioconductor" in sources:
                try:
                    bioc_results = await PackageSearchService._search_bioconductor(client, query, limit)
                    results.extend(bioc_results)
                except Exception as e:
                    logger.warning("Bioconductor search failed: %s", e)

        return results[:limit]

    @staticmethod
    async def _search_conda(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
        resp = await client.get(
            "https://api.anaconda.org/search",
            params={"name": query, "type": "conda"},
        )
        if resp.status_code != 200:
            return []

        results = []
        for item in resp.json()[:limit]:
            channel = None
            if item.get("owner"):
                channel = item["owner"]
            results.append({
                "name": item.get("name", ""),
                "version": item.get("version", item.get("latest_version", "")),
                "description": item.get("summary", ""),
                "source": "conda",
                "channel": channel,
                "homepage": None,
            })
        return results

    @staticmethod
    async def _search_pip(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
        # Try exact match first
        resp = await client.get(f"https://pypi.org/pypi/{query}/json")
        if resp.status_code == 200:
            data = resp.json()
            info = data.get("info", {})
            return [{
                "name": info.get("name", query),
                "version": info.get("version", ""),
                "description": info.get("summary", ""),
                "source": "pip",
                "channel": None,
                "homepage": info.get("home_page") or info.get("project_url"),
            }]

        # Fall back to search via Simple API — limited, so return empty
        return []

    @staticmethod
    async def _search_cran(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
        # Try exact match via crandb
        resp = await client.get(f"https://crandb.r-pkg.org/{query}")
        if resp.status_code == 200:
            data = resp.json()
            return [{
                "name": data.get("Package", query),
                "version": data.get("Version", ""),
                "description": data.get("Title", ""),
                "source": "cran",
                "channel": None,
                "homepage": data.get("URL"),
            }]
        return []

    @staticmethod
    async def _search_bioconductor(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
        # Search bioconductor package list
        resp = await client.get(
            "https://bioconductor.org/packages/json/3.19/bioc/packages.json"
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []
        query_lower = query.lower()
        for pkg_name, pkg_info in data.items():
            if query_lower in pkg_name.lower():
                results.append({
                    "name": pkg_name,
                    "version": pkg_info.get("Version", ""),
                    "description": pkg_info.get("Title", ""),
                    "source": "bioconductor",
                    "channel": None,
                    "homepage": None,
                })
                if len(results) >= limit:
                    break
        return results

    @staticmethod
    async def get_dependency_tree(
        package_name: str,
        source: str,
        environment_name: str,
    ) -> dict:
        """Get dependency tree for a package. Returns simplified info."""
        # In production, this would run conda install --dry-run or pip install --dry-run
        # For now, return a simplified structure
        return {
            "package": package_name,
            "version": "latest",
            "dependencies": [],
            "total_new_packages": 0,
            "estimated_disk_bytes": None,
        }
