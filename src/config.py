from garbled_circuit import util

ALICE_INPUT_FILE = "input_alice.txt"
BOB_INPUT_FILE = "input_bob.txt"


class ProtocolData():
    """Class to hold protocol data for the protocol."""

    def __init__(
        self, inputs: list, max_input: any, max_input_scaled: int,
        max_input_scaled_bit_array: list
    ):
        """Initialize ProtocolData with the given parameters.

        Args:
            inputs (list): List of integer/float inputs of a party.
            max_input (int/float): The maximum input value.
            max_input_scaled (int): The maximum input value multiplied by 10 and casted to an integer.
            max_input_scaled_bit_array (list[int]): Bit array representation of the scaled maximum
                input in two's complement form.
        """
        self.inputs = inputs
        self.max_input = max_input
        self.max_input_scaled = max_input_scaled
        self.max_input_scaled_bit_array = max_input_scaled_bit_array

    def set_protocol_output(self, protocol_output: list[int]):
        """Set the protocol output.

        Args:
            protocol_output (list[int]): The output of the protocol, which is a list of bits.
        """
        self.protocol_output = protocol_output

    def get_protocol_output(self) -> list[int]:
        """Get the protocol output.

        Returns:
            list[int]: The output of the protocol, which is a list of bits.
        Raises:
            ValueError: If the protocol output has not been set.
        """
        if hasattr(self, 'protocol_output'):
            return self.protocol_output
        else:
            raise ValueError("Protocol output has not been set.")

    def check_if_bob_won(self) -> bool:
        """Check if Bob has the global maximum input.

        Returns:
            bool: True if Bob has the global maximum input, False otherwise.
        """
        return self.get_protocol_output() == [1, 1]

    def check_if_alice_won(self) -> bool:
        """Check if Alice has the global maximum input.

        Returns:
            bool: True if Alice has the global maximum input, False otherwise.
        """
        return self.get_protocol_output() == [0, 1]

    def check_if_both_have_same_maximum(self) -> bool:
        """Check if both parties have the same maximum input.

        Returns:
            bool: True if both parties have the same maximum input, False otherwise.
        """
        return self.get_protocol_output() == [0, 0]


class Config():
    """Configuration class for the protocol."""

    def __init__(self, party: str, circuit_path: str, oblivious_transfer: bool, verify: bool):
        """Initialize the configuration for the protocol.

        Args:
            party (str): The party running the protocol, either "alice" or "bob".
            circuit_path (str): Path to the circuit specification file.
            oblivious_transfer (bool): Whether to use oblivious transfer.
            verify (bool): Whether to verify the result additionally without Yao's protocol.
        """
        self.party = party
        self.circuit_path = circuit_path
        self.oblivious_transfer = oblivious_transfer
        self.verify = verify

    def is_alice(self) -> bool:
        """Check if the current party is Alice.

        Returns:
            bool: True if the party is Alice, False otherwise.
        """
        return self.party == "alice"

    def is_bob(self) -> bool:
        """Check if the current party is Bob.

        Returns:
            bool: True if the party is Bob, False otherwise.
        """
        return self.party == "bob"

    def get_input_file(self, other_party=False) -> str:
        """Get the input file path based on the party.

        Args:
            other_party (bool): If True, return the input file of the other party.
                (only relevant for verification on same machine)
        Returns:
            str: The input file path for the current party or the other party.
        Raises:
            ValueError: If the party is not "alice" or "bob".
        """
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
        """Get the number of bits supported by the circuit.

        Returns:
            int: The number of bits supported by the circuit.
        Raises:
            ValueError: If the circuit format is invalid or if 'alice' and 'bob' have different
                number of bits in the circuit.
        """
        circuit = util.parse_json(self.circuit_path)
        if "circuits" not in circuit:
            raise ValueError("Invalid circuit format. 'circuits' key is required.")
        circuit = circuit["circuits"][0]
        if "alice" not in circuit or "bob" not in circuit:
            raise ValueError("Invalid circuit format. 'alice' and 'bob' keys are required.")
        if len(circuit["alice"]) != len(circuit["bob"]):
            raise ValueError("Alice and Bob must have the same number of bits in the circuit.")
        return len(circuit["alice"])

    def set_protocol_data(self, protocol_data: ProtocolData):
        """Set the protocol data.

        Args:
            protocol_data (ProtocolData): The protocol data to set.
        """
        self.protocol_data = protocol_data

    def get_protocol_data(self) -> ProtocolData:
        """Get the protocol data.

        Returns:
            ProtocolData: The protocol data containing inputs, maximum input, scaled maximum input,
                and scaled maximum input in bit array form.
        Raises:
            ValueError: If the protocol data has not been set.
        """
        if hasattr(self, 'protocol_data'):
            return self.protocol_data
        else:
            raise ValueError("Protocol data has not been set.")
