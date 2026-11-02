
from app.services.opensearch_client import (
    get_opensearch_client,
)


def main():

    client = get_opensearch_client()

    info = client.info()

    health = client.cluster.health()

    print("\nOpenSearch connection successful")

    print("\nCluster information:")

    print("Name:", info.get("cluster_name"))
    print("Version:", info["version"]["number"])

    print("\nCluster health:")

    print("Status:", health["status"])
    print("Nodes:", health["number_of_nodes"])
    print(
        "Active primary shards:",
        health["active_primary_shards"],
    )


if __name__ == "__main__":
    main()
