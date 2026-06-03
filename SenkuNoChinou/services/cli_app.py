import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from SenkuNoChinou.core.workflow import build_workflow, respond

_THREAD_ID = str(uuid.uuid4())


async def main() -> None:
    print("Booting Senku (千空の知能)... ", end="", flush=True)
    async with build_workflow() as app:
        print("online.\n")
        print("Type 'exit' or 'quit' to shut down.\n")

        while True:
            try:
                query = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nShutting down.")
                break

            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                print("Shutting down.")
                break

            try:
                response = await respond(app, query, _THREAD_ID)
                print(f"\nSenku: {response}\n")
            except Exception as e:
                print(f"\n[Error] {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
