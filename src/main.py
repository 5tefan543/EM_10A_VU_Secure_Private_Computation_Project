import logging
import argparse
from garbled_circuit import main, util, ot

class Alice(main.YaoGarbler):
    """Alice is the creator of the Yao circuit.

    Alice creates a Yao circuit and sends it to the evaluator along with her
    encrypted inputs. 
    
    TODO: Refactor
    Alice will finally print the truth table of the circuit
    for all combination of Alice-Bob inputs.

    Alice does not know Bob's inputs but for the purpose
    of printing the truth table only, Alice assumes that Bob's inputs follow
    a specific order.

    Attributes:
        circuits: the JSON file containing circuits
        oblivious_transfer: Optional; enable the Oblivious Transfer protocol
            (True by default).
    """
    def __init__(self, circuit_path, input_bits: list[int], oblivious_transfer=True):
        super().__init__(circuit_path)
        self.input_bits = input_bits
        self.socket = util.GarblerSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def start(self):
        """Start Yao protocol."""
        result = None
        if len(self.circuits) != 1:
            raise ValueError("Multiple circuits found in json config. Current implementation only supports one circuit at a time.")

        circuit = self.circuits[0]
        to_send = {
            "circuit": circuit["circuit"],
            "garbled_tables": circuit["garbled_tables"],
            "pbits_out": circuit["pbits_out"],
        }
        logging.debug(f"Sending {circuit['circuit']['id']}")
        self.socket.send_wait(to_send)
        result = self.evaluate(circuit)
        return result

    def evaluate(self, entry):
        """
        TODO: Refactor
        Print circuit evaluation for all Bob and Alice inputs.

        Args:
            entry: A dict representing the circuit to evaluate.
        """
        circuit, pbits, keys = entry["circuit"], entry["pbits"], entry["keys"]
        outputs = circuit["out"]
        a_wires = circuit.get("alice", [])  # Alice's wires
        a_inputs = {}  # map from Alice's wires to (key, encr_bit) inputs
        b_wires = circuit.get("bob", [])  # Bob's wires
        b_keys = {  # map from Bob's wires to a pair (key, encr_bit)
            w: self._get_encr_bits(pbits[w], key0, key1)
            for w, (key0, key1) in keys.items() if w in b_wires
        }

        print(f"======== {circuit['id']} ========")

        # Map Alice's wires to (key, encr_bit)
        for i in range(len(a_wires)):
            a_inputs[a_wires[i]] = (keys[a_wires[i]][self.input_bits[i]],
                                    pbits[a_wires[i]] ^ self.input_bits[i])
            
        # Send Alice's encrypted inputs and keys to Bob
        result = self.ot.get_result(a_inputs, b_keys)

        # Format output
        str_bits_a = ' '.join(str(b) for b in self.input_bits)
        str_result = ' '.join([str(result[w]) for w in outputs])

        output = (f"Alice{a_wires} = {str_bits_a}, Outputs{outputs} = {str_result}")
        return output

    def _get_encr_bits(self, pbit, key0, key1):
        return ((key0, 0 ^ pbit), (key1, 1 ^ pbit))
    
class Bob:
    """Bob is the receiver and evaluator of the Yao circuit.

    Bob receives the Yao circuit from Alice, computes the results and sends
    them back.

    Args:
        oblivious_transfer: Optional; enable the Oblivious Transfer protocol
            (True by default).
    """
    def __init__(self, input_bits: list[int], oblivious_transfer=True):
        self.input_bits = input_bits
        self.socket = util.EvaluatorSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def listen(self):
        """Start listening for Alice messages."""
        logging.info("Start listening")
        result = None
        try:
            for entry in self.socket.poll_socket():
                self.socket.send(True)
                result = self.send_evaluation(entry)
                break  # Only process one circuit at a time
        except KeyboardInterrupt:
            logging.info("Stop listening")
        # close the socket after processing
        self.socket.close()
        return result

    def send_evaluation(self, entry):
        """Evaluate yao circuit for all Bob and Alice's inputs and
        send back the results.

        Args:
            entry: A dict representing the circuit to evaluate.
        """
        circuit, pbits_out = entry["circuit"], entry["pbits_out"]
        outputs = circuit["out"]
        garbled_tables = entry["garbled_tables"]
        b_wires = circuit.get("bob", [])  # list of Bob's wires

        print(f"======== {circuit['id']} ========")

        # Create dict mapping each wire of Bob to Bob's input
        b_inputs_clear = {
            b_wires[i]: self.input_bits[i]
            for i in range(len(b_wires))
        }

        # Evaluate and send result to Alice
        result = self.ot.send_result(circuit, garbled_tables, pbits_out,
                            b_inputs_clear)
        
        # Format output
        str_bits_b = ' '.join(str(b) for b in self.input_bits)
        str_result = ' '.join([str(result[w]) for w in outputs])

        output = (f"Bob{b_wires} = {str_bits_b}, Outputs{outputs} = {str_result}")
        return output
    
def read_input_from_file(filename, bits_supported=4):
    """TODO: Refactor

    Args:
        filename: The name of the file to read from.

    Returns:
        A tuple containing the input bits as a list of integers and the
        maximum number of bits.
    """
    inputs = []
    with open(filename, "r") as f:
        content = f.read().strip().split(',')

        for entry in content:
            try:
                if '.' in entry:
                    inputs.append(float(entry))
                else:
                    inputs.append(int(entry))
            except Exception as e:
                logging.error(f"Error parsing input '{entry}': {e}")

    try:
        max_input = max(inputs)
    except ValueError:
        logging.error("No valid inputs found in the file.")
        exit(1)

    is_max_input_float = type(max_input) is float

    if is_max_input_float:
        max_input = int(max_input*10)

    max_input_in_bits = bin(max_input)[2:].zfill(bits_supported)
    max_input_bit_array = [int(bit) for bit in max_input_in_bits]

    print(inputs, max_input, max_input_bit_array, is_max_input_float)

    return inputs, max_input, max_input_bit_array, is_max_input_float


def main():
    circuit_path = "circuits/cmp_4bit.json"
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
    parser.add_argument("--no-oblivious-transfer",
                        action="store_true",
                        help="disable oblivious transfer")
    parser.add_argument(
        "-m",
        metavar="mode",
        choices=["circuit", "table"],
        default="circuit",
        help="the print mode for local tests (default 'circuit')")
    parser.add_argument("-l",
                        "--loglevel",
                        metavar="level",
                        choices=loglevels.keys(),
                        default="warning",
                        help="the log level (default 'warning')")
    parser.add_argument("-v","--verify",
                        action="store_true",
                        help="additionally verify the result without oblivious transfer")
    
    args = parser.parse_args()

    logging.basicConfig(format="[%(levelname)s] %(message)s",
                    level=loglevels[args.loglevel])

    protocol_result = None
    if args.party == "alice":
        inputs, max_input, max_input_bit_array, is_max_input_float = read_input_from_file("input_alice.txt")
        alice = Alice(circuit_path, max_input_bit_array, oblivious_transfer=not args.no_oblivious_transfer)
        protocol_result = alice.start()
    elif args.party == "bob":
        inputs, max_input, max_input_bit_array, is_max_input_float = read_input_from_file("input_bob.txt")
        bob = Bob(max_input_bit_array, oblivious_transfer=not args.no_oblivious_transfer)
        protocol_result = bob.listen()
    else:
        logging.error(f"Unknown party '{args.party}'")
        parser.print_help()

    print(protocol_result)

    # verify result without Yao protocol
    if args.verify:
        _, alice_max_input, _, _ = read_input_from_file("input_alice.txt")
        _, bob_max_input, _, _ = read_input_from_file("input_bob.txt")

        max_input = max(alice_max_input, bob_max_input)

        if max_input != protocol_result:
            logging.error(f"Verification failed: expected {max_input}, got {protocol_result}")
        else:
            logging.info("Verification successful: results match the expected output.")

if __name__ == '__main__':
    main()
