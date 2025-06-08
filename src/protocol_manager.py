import logging
from src.config import Config, ProtocolData
from src.alice import Alice
from src.bob import Bob


class ProtocolManager:
    """Manages the protocol for comparing maximum inputs between two parties (Alice and Bob)."""

    def __init__(self, config: Config):
        """Initialize the ProtocolManager with a configuration object.

        This method reads the input file specified in the configuration,
        initializes the protocol data, and sets it in the configuration.

        Args:
            config (Config): Configuration object containing protocol config.
        """
        self.config = config
        protocol_data = self.init_protocol_data(self.config.get_input_file())
        self.config.set_protocol_data(protocol_data)

    def read_input_file(self, input_file: str) -> list:
        """Read input values from a file and convert them to integers or floats.

        Args:
            input_file (str): The name of the file to read from.
        Returns:
            list: A list of integers or floats parsed from the file.
        Raises:
            Exception: If there is an error parsing the input values.
        """
        inputs = []
        with open(input_file, "r") as f:
            content = f.read().strip().split(',')
            for entry in content:
                try:
                    if '.' in entry:
                        inputs.append(float(entry))
                    else:
                        inputs.append(int(entry))
                except Exception as e:
                    logging.error(f"Error parsing input '{entry}': {e}")
        return inputs

    def init_protocol_data(self, input_file: str) -> ProtocolData:
        """Initialize ProtocolData with inputs from the specified input file.

        Args:
            input_file (str): The name of the file containing input values.
        Returns:
            ProtocolData: An instance of ProtocolData containing the inputs and their maximum.
        Raises:
            ValueError: If no valid inputs are found in the file.
        """
        inputs = self.read_input_file(input_file)

        try:
            max_input = max(inputs)
        except ValueError:
            raise ValueError("No valid inputs found in the input file.")

        # multiply input by 10 to also support floats in [-9.9, 9.9]
        max_input_scaled = int(max_input * 10)

        # if the input is negative, represent it in two's complement
        if max_input_scaled < 0:
            max_input_scaled = (
                1 << self.config.get_bits_supported()) + max_input_scaled

        max_input_in_bits = bin(max_input_scaled)[2:].zfill(
            self.config.get_bits_supported())
        max_input_scaled_bit_array = [int(bit) for bit in max_input_in_bits]

        protocol_data = ProtocolData(
            inputs, max_input, max_input_scaled, max_input_scaled_bit_array)

        logging.info(f"Inputs: {protocol_data.inputs}")
        logging.info(f"Local maximum: {protocol_data.max_input}")

        return protocol_data

    def compute_protocol(self):
        """Compute the protocol based on the role of the party (Alice or Bob).

        This method initializes the protocol based on the party's role,
        runs the protocol, and sets the protocol output in the configuration.

        Raises:
            ValueError: If the party is neither Alice nor Bob.
        """
        if self.config.is_alice():
            alice = Alice(self.config.circuit_path, self.config.get_protocol_data()
                          .max_input_scaled_bit_array, self.config.oblivious_transfer)
            protocol_output = alice.start()
            self.config.get_protocol_data().set_protocol_output(protocol_output)
        elif self.config.is_bob():
            bob = Bob(self.config.get_protocol_data()
                      .max_input_scaled_bit_array, self.config.oblivious_transfer)
            protocol_output = bob.listen()
            self.config.get_protocol_data().set_protocol_output(protocol_output)
        else:
            raise ValueError(
                "Invalid party specified. Must be 'alice' or 'bob'.")

    def print_protocol_result(self):
        """Print the result of the protocol.

        This method checks the protocol data to determine which party has the
        larger maximum input and prints the result accordingly.
        """
        protocol_data = self.config.get_protocol_data()

        if protocol_data.check_if_both_have_same_maximum():
            logging.info("The other party has the same maximum input.")
        elif protocol_data.check_if_bob_won():
            if self.config.is_alice():
                logging.info("Bob has a larger maximum input.")
            else:
                logging.info(
                    f"I have the global maximum input: {protocol_data.max_input}")
        elif protocol_data.check_if_alice_won():
            if self.config.is_alice():
                logging.info(
                    f"I have the global maximum input: {protocol_data.max_input}")
            else:
                logging.info("Alice has a larger maximum input.")

    def verify_result(self):
        """Verify the result of the protocol without using Yao's protocol.

        This method compares the local protocol data with the protocol data
        of the other party to ensure that the results are consistent.
        It checks if both parties have the same maximum input or if one party has a larger maximum input than the other.
        If the verification fails, it logs an error message; otherwise, it logs a success message.
        """
        logging.info("")
        logging.info("=== Verifying result without Yao's protocol ===")
        protocol_data_local = self.config.get_protocol_data()
        logging.info(
            f"Local protocol output: {protocol_data_local.get_protocol_output()}")

        logging.info("Loading input data of the other party only for verification:")
        input_file_of_other_party = self.config.get_input_file(
            other_party=True)
        protocol_data_of_other_party = self.init_protocol_data(
            input_file_of_other_party)

        verification_failed = False
        if protocol_data_local.check_if_both_have_same_maximum():
            if protocol_data_local.max_input != protocol_data_of_other_party.max_input:
                verification_failed = True
        elif protocol_data_local.check_if_bob_won():
            if self.config.is_alice():
                if protocol_data_local.max_input >= protocol_data_of_other_party.max_input:
                    verification_failed = True
            elif self.config.is_bob():
                if protocol_data_local.max_input <= protocol_data_of_other_party.max_input:
                    verification_failed = True
        elif protocol_data_local.check_if_alice_won():
            if self.config.is_alice():
                if protocol_data_local.max_input <= protocol_data_of_other_party.max_input:
                    verification_failed = True
            elif self.config.is_bob():
                if protocol_data_local.max_input >= protocol_data_of_other_party.max_input:
                    verification_failed = True

        if verification_failed:
            logging.error(f"VERIFICATION FAILED!")
        else:
            logging.info("VERIFICATION SUCCESSFUL!")
