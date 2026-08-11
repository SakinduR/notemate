from app.ingest_pipeline import run_ingestion


def main():
    node_count, source_types = run_ingestion()
    print(f"Ingestion complete. Embedded and saved {node_count} nodes to database.")
    for file_name, source_type in source_types.items():
        print(f"  {file_name}: {source_type}")


if __name__ == "__main__":
    main()
