
import logging
from parameterized import parameterized
import unittest
import threading
from unittest.mock import patch
from src.protocol_manager import ProtocolManager, Config, ProtocolData


class TestProtocolManager(unittest.TestCase):
    _logger = logging.getLogger(__name__)

    def setUp(self):
        self.config_alice = Config(
            "alice", "src/circuits/cmp-32bit-signed_generated.json", True, False)
        self.config_bob = Config(
            "bob", "src/circuits/cmp-32bit-signed_generated.json", True, False)

    def make_mock_read_input_file(self, inputs):
        def mock_read_input_file(self, input_file):
            return inputs
        return mock_read_input_file

    @parameterized.expand([
        ([1, 2, 3], 3),
        ([4, 5, 6], 6),
        ([7, 8, 9], 9)
    ])
    def test_init_protocol_data(self, inputs, expected_max_input):
        with patch.object(ProtocolManager, 'read_input_file', self.make_mock_read_input_file(inputs)):
            # ACT: Initialize ProtocolManager and get protocol data
            manager = ProtocolManager(self.config_alice)

            # ASSERT: Check if protocol data is initialized correctly
            protocol_data = manager.config.get_protocol_data()
            self.assertEqual(protocol_data.max_input, expected_max_input)

    def compute_protocol_thread_helper(self, config: Config, inputs: list, results: dict):
        with patch.object(ProtocolManager, 'read_input_file', self.make_mock_read_input_file(inputs)):
            manager = ProtocolManager(config)
            manager.compute_protocol()
            results[config.party] = manager.config.get_protocol_data()

    @parameterized.expand([
        # Test cases for integer inputs
        ([1, 2, 3], [4, 5, 6], "bob"),
        ([4, 5, 6], [1, 2, 3], "alice"),
        ([4, 5, 6], [4, 5, 6], "equal"),
        ([-1, -2, -3], [-4, -5, -6], "alice"),
        ([-4, -5, -6], [-1, -2, -3], "bob"),
        ([-4, -5, -6], [-4, -5, -6], "equal"),
        # Test cases for float inputs
        ([1.2, 2.3, 3.4], [4.5, 5.6, 6.7], "bob"),
        ([4.5, 5.6, 6.7], [1.2, 2.3, 3.4], "alice"),
        ([4.5, 5.6, 6.7], [4.5, 5.6, 6.7], "equal"),
        ([-1.2, -2.3, -3.4], [-4.5, -5.6, -6.7], "alice"),
        ([-4.5, -5.6, -6.7], [-1.2, -2.3, -3.4], "bob"),
        ([-4.5, -5.6, -6.7], [-4.5, -5.6, -6.7], "equal"),
        # Test cases for mixed inputs (integers and floats)
        ([1, 2.3, 3], [4.5, 5, 6], "bob"),
        ([4.5, 5, 6], [1, 2.3, 3], "alice"),
        ([4.5, 5, 6], [4.5, 5, 6], "equal"),
        ([-1.2, -2, -3], [-4.5, -5, -6], "alice"),
        ([-4.5, -5, -6], [-1.2, -2, -3], "bob"),
        ([-4.5, -5, -6], [-4.5, -5, -6], "equal"),
        # Test cases to support 16-bit signed integers in range [-32768, 32767]
        ([32767], [32766], "alice"),
        ([32766], [32767], "bob"),
        ([32765], [32765], "equal"),
        ([-32768], [-32767], "bob"),
        ([-32767], [-32768], "alice"),
        ([-32766], [-32766], "equal"),
        # Test cases to support floats in range [-9.9, 9.9]
        ([9.9], [9.8], "alice"),
        ([9.8], [9.9], "bob"),
        ([9.7], [9.7], "equal"),
        ([-9.9], [-9.8], "bob"),
        ([-9.8], [-9.9], "alice"),
        ([-9.7], [-9.7], "equal")
    ])
    def test_compute_protocol(self, inputs_alice: list, inputs_bob: list, winning_party: str):
        """Test compute_protocol with various input pairs and expected winner."""
        # ARRANGE: create ProtocolManager instances for Alice and Bob in separate threads
        results = {}
        thread_alice = threading.Thread(target=self.compute_protocol_thread_helper, args=(
            self.config_alice, inputs_alice, results))
        thread_bob = threading.Thread(target=self.compute_protocol_thread_helper, args=(
            self.config_bob, inputs_bob, results))

        # ACT: Start threads to compute protocol
        thread_alice.start()
        thread_bob.start()

        thread_alice.join()
        thread_bob.join()

        # ASSERT: Check if results are computed correctly
        protocol_data_alice: ProtocolData = results['alice']
        protocol_data_bob: ProtocolData = results['bob']

        if winning_party == "alice":
            self.assertTrue(protocol_data_alice.check_if_alice_won())
            self.assertTrue(protocol_data_bob.check_if_alice_won())
        if winning_party == "bob":
            self.assertTrue(protocol_data_alice.check_if_bob_won())
            self.assertTrue(protocol_data_bob.check_if_bob_won())
        if winning_party == "equal":
            self.assertTrue(
                protocol_data_alice.check_if_both_have_same_maximum())
            self.assertTrue(
                protocol_data_bob.check_if_both_have_same_maximum())
