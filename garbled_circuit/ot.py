import hashlib
import logging
import pickle
from . import util, yao


class ObliviousTransfer:
    def __init__(self, socket, enabled=True, group=None):
        self.socket = socket
        self.enabled = enabled
        self.group = group

    def get_result(self, a_inputs, b_keys):
        """Send Alice's inputs and retrieve Bob's result of evaluation.

        Args:
            a_inputs: A dict mapping Alice's wires to (key, encr_bit) inputs.
            b_keys: A dict mapping each Bob's wire to a pair (key, encr_bits).

        Returns:
            The result of the yao circuit evaluation.
        """
        logging.debug(f"Sending inputs to Bob: {a_inputs}")
        self.socket.send_wait(a_inputs)

        logging.debug("Init OT protocol:")
        logging.debug("Generating prime group to use for OT")
        self.group = self.enabled and (self.group or util.PrimeGroup())
        logging.debug(f"Sending prime group: {self.group}")
        self.socket.send(self.group)

        for _ in range(len(b_keys)):
            w = self.socket.receive()  # receive gate ID where to perform OT
            logging.debug(f"Received gate ID {w}")

            if self.enabled:  # perform oblivious transfer
                pair = (pickle.dumps(b_keys[w][0]), pickle.dumps(b_keys[w][1]))
                self.ot_garbler(pair)
            else:
                to_send = (b_keys[w][0], b_keys[w][1])
                self.socket.send(to_send)
        result = self.socket.receive()
        logging.debug(f"Received circuit evaluation from Bob: {result}")
        return result

    def send_result(self, circuit, g_tables, pbits_out, b_inputs):
        """Evaluate circuit and send the result to Alice.

        Args:
            circuit: A dict containing circuit spec.
            g_tables: Garbled tables of yao circuit.
            pbits_out: p-bits of outputs.
            b_inputs: A dict mapping Bob's wires to (clear) input bits.

        Returns:
            The result of the yao circuit evaluation.
        """
        # map from Alice's wires to (key, encr_bit) inputs
        a_inputs = self.socket.receive()
        self.socket.send(True)
        # map from Bob's wires to (key, encr_bit) inputs
        b_inputs_encr = {}

        logging.debug(f"Received Alice's inputs: {a_inputs}")

        self.group = self.socket.receive()
        logging.debug(f"Received group to use for OT: {self.group}")

        for w, b_input in b_inputs.items():
            logging.debug(f"Sending gate ID {w}")
            self.socket.send(w)

            if self.enabled:
                b_inputs_encr[w] = self.ot_evaluator(b_input)
            else:
                pair = self.socket.receive()
                logging.debug(f"Received key pair, key {b_input} selected")
                b_inputs_encr[w] = pair[b_input]

        result = yao.evaluate(circuit, g_tables, pbits_out, a_inputs,
                              b_inputs_encr)

        logging.debug(f"Sending circuit evaluation: {result}")
        self.socket.send(result)
        return result

    def ot_garbler(self, msgs):
        """Oblivious transfer, Alice's side.

        Args:
            msgs: A pair (msg1, msg2) to suggest to Bob.
        """
        logging.debug("OT protocol started")
        G = self.group

        # OT protocol based on Nigel Smart’s "Cryptography Made Simple"
        c = G.gen_pow(G.rand_int())
        logging.debug(f"Sending commitment: {c}")
        h0 = self.socket.send_wait(c)
        logging.debug(f"Received h corresponding to Bob's input: {h0}")
        h1 = G.mul(c, G.inv(h0))
        k = G.rand_int()
        c1 = G.gen_pow(k)
        e0 = util.xor_bytes(msgs[0], self.ot_hash(G.pow(h0, k), len(msgs[0])))
        e1 = util.xor_bytes(msgs[1], self.ot_hash(G.pow(h1, k), len(msgs[1])))

        logging.debug(f"Sending encrypted messages and second commitment: {e0}, {e1}, {c1}")
        self.socket.send((c1, e0, e1))
        logging.debug("OT protocol ended")

    def ot_evaluator(self, b):
        """Oblivious transfer, Bob's side.

        Args:
            b: Bob's input bit used to select one of Alice's messages.

        Returns:
            The message selected by Bob.
        """
        logging.debug("OT protocol started")
        G = self.group

        # OT protocol based on Nigel Smart’s "Cryptography Made Simple"
        c = self.socket.receive()
        logging.debug(f"Received commitment: {c}")
        x = G.rand_int()
        x_pow = G.gen_pow(x)
        h = (x_pow, G.mul(c, G.inv(x_pow)))
        logging.debug(f"Sending h depending on input b={b}: {h}")
        c1, e0, e1 = self.socket.send_wait(h[b])
        logging.debug(f"Received encrypted messages and second commitment: {e0}, {e1}, {c1}")
        e = (e0, e1)
        ot_hash = self.ot_hash(G.pow(c1, x), len(e[b]))
        mb = pickle.loads(util.xor_bytes(e[b], ot_hash))

        logging.debug(f"Decrypted (key, encr_bit) pair: {mb}")
        logging.debug("OT protocol ended")
        return mb

    @staticmethod
    def ot_hash(pub_key, msg_length):
        """Hash function for OT keys."""
        key_length = (pub_key.bit_length() + 7) // 8  # key length in bytes
        bytes = pub_key.to_bytes(key_length, byteorder="big")
        return hashlib.shake_256(bytes).digest(msg_length)
