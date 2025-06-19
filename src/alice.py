import logging
from abc import ABC, abstractmethod
from garbled_circuit import util, ot, yao


class YaoGarbler(ABC):
    """An abstract class for Yao garblers (e.g. Alice)."""

    def __init__(self, circuit_path: str):
        """Initialize the Yao garbler.

        Args:
            circuit_path (str): Path to the JSON file containing the circuit.
        """
        circuit_path = util.parse_json(circuit_path)
        self.name = circuit_path["name"]
        self.circuits = []

        for circuit in circuit_path["circuits"]:
            garbled_circuit = yao.GarbledCircuit(circuit)
            pbits = garbled_circuit.get_pbits()
            entry = {
                "circuit": circuit,
                "garbled_circuit": garbled_circuit,
                "garbled_tables": garbled_circuit.get_garbled_tables(),
                "keys": garbled_circuit.get_keys(),
                "pbits": pbits,
                "pbits_out": {w: pbits[w]
                              for w in circuit["out"]},
            }
            self.circuits.append(entry)

    @abstractmethod
    def start(self):
        pass


class Alice(YaoGarbler):
    """Alice is the creator of the Yao circuit.

    Alice creates a Yao circuit and sends it to the evaluator along with her
    encrypted inputs. After evaluating the circuit, Alice returns the
    output of the circuit.
    """

    def __init__(self, circuit_path: str, input_bits: list[int], oblivious_transfer=True):
        """Initialize Alice.

        Args:
            circuit_path (str): Path to the JSON file containing the circuit.
            input_bits (list[int]): List of bits representing Alice's inputs.
            oblivious_transfer (bool): Whether to enable oblivious transfer.
        """
        super().__init__(circuit_path)
        self.input_bits = input_bits
        self.socket = util.GarblerSocket()
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def start(self) -> list[int]:
        """Start Yao protocol.

        Returns:
            list[int]: The output of the evaluated circuit.
        Raises:
            ValueError: If multiple circuits are found in the JSON config.
        """
        result = None
        if len(self.circuits) != 1:
            raise ValueError(
                "Multiple circuits found in json config. Current implementation only supports one circuit at a time.")

        circuit = self.circuits[0]
        to_send = {
            "circuit": circuit["circuit"],
            "garbled_tables": circuit["garbled_tables"],
            "pbits_out": circuit["pbits_out"],
        }
        logging.debug(f"Sending circuit definition '{circuit['circuit']['id']}' to Bob")
        logging.debug(f"Sending pbits_out to Bob: {circuit['pbits_out']}")
        if logging.getLogger(__name__).getEffectiveLevel() <= logging.DEBUG:
            garbled_circuit: yao.GarbledCircuit = circuit['garbled_circuit']
            garbled_table_list = list(garbled_circuit.garbled_tables.items())
            logging.debug(f"Sending {len(garbled_table_list)} garbled tables to Bob")
            for garbled_table in garbled_table_list[:3]:
                logging.debug(f"Garbled table for gate {garbled_table[0]}: {garbled_table[1]}")
            logging.debug(f"Truncated remaining {len(garbled_table_list) - 3} garbled tables")

        self.socket.send_wait(to_send)
        result = self.evaluate(circuit)
        # close the socket after processing
        self.socket.close()
        return result

    def evaluate(self, entry: dict) -> list[int]:
        """Evaluate the circuit.

        Args:
            entry (dict): A dict representing the circuit to evaluate.
        Returns:
            list[int]: The output of the evaluated circuit.
        """
        circuit, pbits, keys = entry["circuit"], entry["pbits"], entry["keys"]
        a_wires = circuit.get("alice", [])  # Alice's wires
        a_inputs = {}  # map from Alice's wires to (key, encr_bit) inputs
        b_wires = circuit.get("bob", [])  # Bob's wires
        b_keys = {  # map from Bob's wires to a pair (key, encr_bit)
            w: self._get_encr_bits(pbits[w], key0, key1)
            for w, (key0, key1) in keys.items() if w in b_wires
        }

        logging.info("")
        logging.info(f"======== {circuit['id']} ========")

        # Map Alice's wires to (key, encr_bit)
        for i in range(len(a_wires)):
            a_inputs[a_wires[i]] = (keys[a_wires[i]][self.input_bits[i]],
                                    pbits[a_wires[i]] ^ self.input_bits[i])

        # Send Alice's encrypted inputs and keys to Bob
        result = self.ot.get_result(a_inputs, b_keys)

        return list(result.values())

    def _get_encr_bits(self, pbit, key0, key1) -> tuple[tuple[int, int], tuple[int, int]]:
        return ((key0, 0 ^ pbit), (key1, 1 ^ pbit))
