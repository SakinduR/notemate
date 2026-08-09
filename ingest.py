from app.ingest_pipeline import run_ingestion


def main():
    node_count = run_ingestion()
    print(f"Ingestion complete. Embedded and saved {node_count} nodes to database.")


if __name__ == "__main__":
    main()
