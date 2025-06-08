import logging
import argparse
from protocol_manager import ProtocolManager, Config


def main():
    loglevels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    parser = argparse.ArgumentParser(description="Run Yao protocol.")
    parser.add_argument("party",
                        choices=["alice", "bob"],
                        help="the yao party to run")
    parser.add_argument("-c",
                        "--circuit",
                        metavar="circuit.json",
                        default="circuits/cmp-32bit-signed_generated.json",
                        help=("the JSON circuit file"))
    parser.add_argument("--no-oblivious-transfer",
                        action="store_true",
                        help="disable oblivious transfer")
    parser.add_argument("-v", "--verify",
                        action="store_true",
                        help="additionally verify the result without oblivious transfer")
    parser.add_argument("-l",
                        "--loglevel",
                        metavar="level",
                        choices=loglevels.keys(),
                        default="info",
                        help="the log level (default 'info')")

    args = parser.parse_args()
    config = Config(args.party, args.circuit, not args.no_oblivious_transfer, args.verify)

    logging.basicConfig(format="[%(levelname)s] %(message)s",
                        level=loglevels[args.loglevel])

    protocol_manager = ProtocolManager(config)
    protocol_manager.compute_protocol()
    protocol_manager.print_protocol_result()

    # verify result without Yao protocol
    if config.verify:
        protocol_manager.verify_result()


if __name__ == '__main__':
    main()
