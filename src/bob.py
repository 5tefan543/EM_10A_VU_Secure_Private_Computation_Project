import logging
from garbled_circuit import util, ot

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

        print(f"\n======== {circuit['id']} ========")

        # Create dict mapping each wire of Bob to Bob's input
        b_inputs_clear = {
            b_wires[i]: self.input_bits[i]
            for i in range(len(b_wires))
        }

        # Evaluate and send result to Alice
        result = self.ot.send_result(circuit, garbled_tables, pbits_out,
                                     b_inputs_clear)

        # Format output
        # str_bits_b = ' '.join(str(b) for b in self.input_bits)
        # str_result = ' '.join([str(result[w]) for w in outputs])

        # protocol_output_str = (
        #     f"Bob{b_wires} = {str_bits_b}, Outputs{outputs} = {str_result}")
        return list(result.values())
