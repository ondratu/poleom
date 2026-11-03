"""Generate bcrypt hash."""

from argparse import ArgumentParser
from hashlib import sha3_512

from bcrypt import gensalt, hashpw


def password_hash(password: str, rounds: int = 12) -> str:
    """Return password hash in the format used by the application."""
    return hashpw(
        sha3_512(password.encode("utf-8")).digest(),
        gensalt(rounds)).decode("utf-8")


def main(argv: list[str] | None = None):
    """Print SQL statements which set the password."""
    parser = ArgumentParser(description=__doc__,
                            usage="%(prog)s [options] PASSWORD [ROUNDS]")
    parser.add_argument("password",
                        type=str,
                        metavar="PASSWORD",
                        help="Password from which you want to generate hash.")
    parser.add_argument("rounds",
                        default=12,
                        type=int,
                        nargs="?",
                        metavar="ROUNDS",
                        help="How many rounds to create hash. (Default 12)")
    args = parser.parse_args(argv)

    hs = password_hash(args.password, args.rounds)
    # ruff: noqa: T201,S608
    print("-- First setup")
    print(f"UPDATE users SET password='{hs}', email='your@login' WHERE "
          "email='root@localhost';")
    print("-- Password reset --")
    print(f"UPDATE users SET password='{hs}' WHERE email='your@login';")


if __name__ == "__main__":
    main()
