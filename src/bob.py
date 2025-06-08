import logging
from garbled_circuit import util, ot


class Bob:
    """Bob is the receiver and evaluator of the Yao circuit.

    Bob receives the Yao circuit from Alice, computes the result and sends
    it back.
    """

    def __init__(self, input_bits: list[int], oblivious_transfer=True):
        """Initialize Bob.

        Args:
            input_bits (list[int]): List of bits representing Bob's inputs.
            oblivious_transfer (bool): Whether to enable oblivious transfer.
        """
        self.input_bits = input_bits
        self.socket = util.EvaluatorSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def listen(self) -> list[int]:
        """Start listening for Alice messages.

        Returns:
            list[int]: The output of the evaluated circuit.
        """
        logging.debug("Start listening")
        result = None
        try:
            for entry in self.socket.poll_socket():
                self.socket.send(True)
                result = self.send_evaluation(entry)
                break  # Only process one circuit at a time
        except KeyboardInterrupt:
            logging.debug("Stop listening")
        # close the socket after processing
        self.socket.close()
        return result

    def send_evaluation(self, entry: dict) -> list[int]:
        """Evaluate the circuit and send the result back to Alice.

        Args:
            entry (dict): A dict representing the circuit to evaluate.
        Returns:
            list[int]: The output of the evaluated circuit.
        """
        circuit, pbits_out = entry["circuit"], entry["pbits_out"]
        garbled_tables = entry["garbled_tables"]
        b_wires = circuit.get("bob", [])  # list of Bob's wires

        logging.info("")
        logging.info(f"======== {circuit['id']} ========")

        # Create dict mapping each wire of Bob to Bob's input
        b_inputs_clear = {
            b_wires[i]: self.input_bits[i]
            for i in range(len(b_wires))
        }

        # Evaluate and send result to Alice
        result = self.ot.send_result(circuit, garbled_tables, pbits_out,
                                     b_inputs_clear)

        return list(result.values())
