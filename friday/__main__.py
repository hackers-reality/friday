"""FRIDAY CLI entry point — `python -m friday` or `friday`."""
import sys
import asyncio


def main():
    """Launch FRIDAY interactive session."""
    try:
        from friday.live import friday_live_engine
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
