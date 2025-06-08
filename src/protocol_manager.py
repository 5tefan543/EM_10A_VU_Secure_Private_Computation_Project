import logging
from src.config import Config, ProtocolData
from src.alice import Alice
from src.bob import Bob


class ProtocolManager:
    def __init__(self, config: Config):
        self.config = config
        protocol_data = self.init_protocol_data(self.config.get_input_file())
        self.config.set_protocol_data(protocol_data)

    def read_input_file(self, input_file: str) -> list:
        """TODO"""
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

    def init_protocol_data(self, input_file) -> ProtocolData:
        """
        TODO: Refactor
        Read input values from a file and compute the maximum input value.

        Args:
            filename: The name of the file to read from.

        Returns:
            A tuple containing the input bits as a list of integers,
            the maximum input value, and the maximum input represented as a bit array.
        """
        inputs = self.read_input_file(input_file)

        try:
            max_input = max(inputs)
        except ValueError:
            logging.error("No valid inputs found in the file.")
            exit(1)

        # multiply input by 10 to also support floats in [-9.9, 9.9]
        is_float = isinstance(max_input, float)
        max_input_scaled = int(max_input * 10)

        # if the input is negative, represent it in two's complement
        is_negative = max_input < 0
        if max_input_scaled < 0:
            max_input_scaled = (
                1 << self.config.get_bits_supported()) + max_input_scaled

        max_input_in_bits = bin(max_input_scaled)[2:].zfill(
            self.config.get_bits_supported())
        max_input_scaled_bit_array = [int(bit) for bit in max_input_in_bits]

        protocol_data = ProtocolData(
            inputs, max_input, max_input_scaled, max_input_scaled_bit_array, is_float, is_negative)

        print(f"Inputs: {protocol_data.inputs}")
        print(f"Local maximum: {protocol_data.max_input}")

        return protocol_data

    def print_protocol_result(self):
        protocol_data = self.config.get_protocol_data()

        if protocol_data.check_if_both_have_same_maximum():
            print("The other party has the same maximum input.")
        elif protocol_data.check_if_bob_won():
            if self.config.is_alice():
                print("Bob has a larger maximum input.")
            else:
                print(
                    f"I have the global maximum input: {protocol_data.max_input}")
        elif protocol_data.check_if_alice_won():
            if self.config.is_alice():
                print(
                    f"I have the global maximum input: {protocol_data.max_input}")
            else:
                print("Alice has a larger maximum input.")

    def compute_protocol(self) -> str:
        if self.config.is_alice():
            # print current directory
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

    def verify_result(self):
        print("\n=== Verifying result without Yao's protocol ===")
        protocol_data_local = self.config.get_protocol_data()
        print(
            f"Local protocol output: {protocol_data_local.get_protocol_output()}")

        print("Loading local input data of the other party only for verification...")
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
            print(f"VERIFICATION FAILED: '{self.config.party.capitalize()}' protocol output: "
                  f"{protocol_data_local.get_protocol_output()}.")
        else:
            print("VERIFICATION SUCCESSFUL!")
