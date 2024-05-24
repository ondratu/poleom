"""Generate bcrypt hash."""

from argparse import ArgumentParser
from hashlib import sha3_512

from bcrypt import gensalt, hashpw

if __name__ == "__main__":
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
    args = parser.parse_args()

    hs = hashpw(
        sha3_512(args.password.encode("utf-8")).digest(),
        gensalt(int(args.rounds))).decode("utf-8")
    # ruff: noqa: T201,S608
    print("-- First setup")
    print(f"UPDATE users SET password='{hs}', email='your@login' WHERE "
          "email='admin@poleom';")
    print("-- Password reset --")
    print(f"UPDATE users SET password='{hs}' WHERE email='your@login';")
