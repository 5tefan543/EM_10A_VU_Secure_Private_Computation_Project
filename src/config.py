from garbled_circuit import util

ALICE_INPUT_FILE = "input_alice.txt"
BOB_INPUT_FILE = "input_bob.txt"


class ProtocolData():
    def __init__(
        self, inputs: list, max_input: int, max_input_scaled: int,
        max_input_scaled_bit_array: list, is_float: bool, is_negative: bool
    ):
        self.inputs = inputs
        self.max_input = max_input
        self.max_input_scaled = max_input_scaled
        self.max_input_scaled_bit_array = max_input_scaled_bit_array
        self.is_float = is_float
        self.is_negative = is_negative

    def set_protocol_output(self, protocol_output: list[int]):
        self.protocol_output = protocol_output

    def get_protocol_output(self) -> list[int]:
        if hasattr(self, 'protocol_output'):
            return self.protocol_output
        else:
            raise ValueError("Protocol output has not been set.")

    def check_if_bob_won(self) -> bool:
        """
        Check if Bob has the global maximum input.
        Returns True if Bob has the global maximum input, False otherwise.
        """
        return self.get_protocol_output() == [1, 1]

    def check_if_alice_won(self) -> bool:
        """
        Check if Alice has the global maximum input.
        Returns True if Alice has the global maximum input, False otherwise.
        """
        return self.get_protocol_output() == [0, 1]

    def check_if_both_have_same_maximum(self) -> bool:
        """
        Check if both parties have the same maximum input.
        Returns True if both parties have the same maximum input, False otherwise.
        """
        return self.get_protocol_output() == [0, 0]


class Config():
    def __init__(self, party: str, circuit_path: str, oblivious_transfer: bool, verify: bool):
        self.party = party
        self.circuit_path = circuit_path
        self.oblivious_transfer = oblivious_transfer
        self.verify = verify

    def is_alice(self) -> bool:
        return self.party == "alice"

    def is_bob(self) -> bool:
        return self.party == "bob"

    def get_input_file(self, other_party=False) -> str:
        if self.is_alice():
            if other_party:
                return BOB_INPUT_FILE
            return ALICE_INPUT_FILE
        elif self.is_bob():
            if other_party:
                return ALICE_INPUT_FILE
            return BOB_INPUT_FILE
        else:
            raise ValueError(
                "Invalid party specified. Must be 'alice' or 'bob'.")

    def get_bits_supported(self) -> int:
        circuit = util.parse_json(self.circuit_path)["circuits"][0]
        assert len(circuit["alice"]) == len(circuit["bob"])
        return len(circuit["alice"])

    def set_protocol_data(self, protocol_data: ProtocolData):
        self.protocol_data = protocol_data

    def get_protocol_data(self) -> ProtocolData:
        if hasattr(self, 'protocol_data'):
            return self.protocol_data
        else:
            raise ValueError("Protocol data has not been set.")
