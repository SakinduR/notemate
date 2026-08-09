import argparse

from app.query_pipeline import answer_query


def main():
    parser = argparse.ArgumentParser(description="Ask a question against the ingested course materials.")
    parser.add_argument(
        "query",
        nargs="?",
        default="What is Constructive Cost Model?",
        help="Question to ask (defaults to a sample question if omitted)",
    )
    args = parser.parse_args()

    _, response = answer_query(args.query)
    print(f"CourseLens Answer:\n{response}\n")


if __name__ == "__main__":
    main()
