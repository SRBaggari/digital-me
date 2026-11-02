"""Command line: digital-me init <name> | list | serve [--instance <name>]."""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from .config import (
    InstanceError,
    ProfileError,
    ServerSettings,
    SettingsError,
    create,
    list_instances,
    resolve,
)
from .db import InstanceMismatchError


def _pick_instance(name: str | None) -> str:
    if name:
        return name
    names = list_instances()
    if len(names) == 1:
        return names[0]
    if not names:
        raise InstanceError("No instances yet. Create one with: digital-me init <name>")
    raise InstanceError(f"Several instances exist ({', '.join(names)}). Choose one with --instance.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="digital-me", description="Personal local AI digital human")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a new private instance")
    init.add_argument("name")
    commands.add_parser("list", help="list instances")
    serve = commands.add_parser("serve", help="start the local server")
    serve.add_argument("--instance", "-i")
    serve.add_argument("--port", type=int)
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            instance = create(args.name)
            print(f"Created {instance.root}")
            print(f"Now edit {instance.profile_path} with the person's details.")
        elif args.command == "list":
            for name in list_instances():
                print(name)
        elif args.command == "serve":
            return _serve(_pick_instance(args.instance), args.port)
    except (InstanceError, ProfileError, SettingsError, InstanceMismatchError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _serve(name: str, port: int | None) -> int:
    import uvicorn

    from .server import build_context, create_app

    context = build_context(resolve(name))
    server = context.settings.server
    if port is not None:
        server = ServerSettings(host=server.host, port=port)  # re-validates the range
        context.settings = context.settings.model_copy(update={"server": server})
    app = create_app(context)
    print(f"Digital Me ({name}) on http://{server.host}:{server.port}")
    uvicorn.run(app, host=server.host, port=server.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
