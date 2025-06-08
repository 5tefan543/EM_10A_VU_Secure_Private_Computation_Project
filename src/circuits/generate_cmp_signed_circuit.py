import argparse


def generate_cmp_signed_circuit(bits: int) -> str:
    """
    Generates a comparison circuit for signed integers in two's complement representation.
    The circuit compares two signed integers represented by Alice and Bob, each using `bits` bits.
    The output is a JSON file containing the circuit description.

    The generated circuit has the following output:
        - [11] => [Bob > Alice, equality check failed]
        - [01] => [Bob < Alice, equality check failed]
        - [00] => [Bob == Alice, equality check passed]

    Args:
        bits (int): The number of bits that should be supported by the generated circuit.
    Returns:
        str: The path to the generated JSON file containing the circuit.
    """
    # declare input bits for Alice as A1A2A3A4...
    alice = list(range(1, bits + 1))
    # declare input bits for Bob as B1B2B3B4...
    bob = list(range(bits + 1, 2 * bits + 1))
    # start first gate id after input bits of Alice and Bob + 1
    wire_id = 2 * bits + 1 + 2
    gates = []

    # === compare bits and determine if Bob wins (first output bit) ===

    # check if B1 > A1 => Bob wins
    gates.append({"id": wire_id, "type": "NOT", "in": [alice[0]]})
    wire_id += 1
    gates.append({"id": wire_id, "type": "AND", "in": [wire_id-1, bob[0]]})
    wire_id += 1

    for i in range(1, bits):
        # check on each level i if Bi > Ai => Bob wins if for all higher bits Bj == Aj holds
        gates.append({"id": wire_id, "type": "NOT", "in": [alice[i]]})
        wire_id += 1
        gates.append({"id": wire_id, "type": "AND", "in": [wire_id-1, bob[i]]})
        wire_id += 1
        gates.append({"id": wire_id, "type": "XNOR", "in": [alice[i-1], bob[i-1]]})
        wire_id += 1

        if i != 1:
            # need to AND Bj-1 == Aj-1 check with Bj == Aj check
            gates.append({"id": wire_id, "type": "AND", "in": [wire_id-6, wire_id-1]})
            wire_id += 1
            gates.append({"id": wire_id, "type": "AND", "in": [wire_id-3, wire_id-1]})
            wire_id += 1
            gates.append({"id": wire_id, "type": "OR", "in": [wire_id-6, wire_id-1]})
            wire_id += 1

        # if i == 1 then we don't have a previous equality check
        else:
            gates.append({"id": wire_id, "type": "AND", "in": [wire_id-2, wire_id-1]})
            wire_id += 1
            gates.append({"id": wire_id, "type": "OR", "in": [wire_id-5, wire_id-1]})
            wire_id += 1

    # add logic for signed integers with two's complement

    # check if A1 != B1 => Bob wins if A1 = 1 and loses if A1 = 0 => so output A1
    gates.append({"id": wire_id, "type": "XOR", "in": [alice[0], bob[0]]})
    wire_id += 1
    gates.append({"id": wire_id, "type": "AND", "in": [alice[0], wire_id-1]})
    wire_id += 1

    # check if A1 == B1 => Bob wins if Bi > Ai for some level i and for all higher bits Bj == Aj holds
    gates.append({"id": wire_id, "type": "NOT", "in": [wire_id-2]})  # NOT of A1 XOR B1
    wire_id += 1
    gates.append({"id": wire_id, "type": "AND", "in": [wire_id-1, wire_id-4]})
    wire_id += 1

    # now combine following results with OR to determine if Bob wins => if Bob wins then output 1, else output 0
    # - check if A1 != B1 => Bob wins if A1 = 1 and loses if A1 = 0 => so output A1
    # - check if A1 == B1 => Bob wins if Bi > Ai for some level i and for all higher bits Bj == Aj holds
    gates.append({"id": wire_id, "type": "OR", "in": [wire_id-3, wire_id-1]})

    # save the first output bit id
    first_output_bit_id = wire_id
    wire_id += 1

    # === check for equality of bits (second output bit) ===

    # check if A_LSB == B_LSB
    gates.append({"id": wire_id, "type": "XNOR", "in": [alice[bits-1], bob[bits-1]]})
    wire_id += 1

    # now combine the previous equality checks of higher bits Bj == Aj with the lsb equality check
    # NAND(AND (Bj == Aj for j = 1 to bits-1), A_LSB == B_LSB)
    gates.append({"id": wire_id, "type": "NAND", "in": [wire_id-9, wire_id-1]})

    # save the second output bit id
    second_output_bit_id = wire_id

    # build circuit dict
    circuit = {
        "name": "cmp",
        "circuits": [
            {
                "id": f"{bits}-bit CMP signed (two's complement)",
                "alice": alice,
                "bob": bob,
                "out": [first_output_bit_id, second_output_bit_id],
                "gates": gates
            }
        ]
    }

    path = f"cmp-{bits}bit-signed_generated.json"
    write_compact_and_readable_json(circuit, path)
    return path


def write_compact_and_readable_json(circuit_dict, path):
    with open(path, "w") as f:
        f.write('{\n')
        f.write(f'  "name": "{circuit_dict["name"]}",\n')
        f.write('  "circuits": [\n')

        circuit = circuit_dict["circuits"][0]
        f.write('    {\n')
        f.write(f'      "id": "{circuit["id"]}",\n')
        f.write(f'      "alice": {circuit["alice"]},\n')
        f.write(f'      "bob": {circuit["bob"]},\n')
        f.write(f'      "out": {circuit["out"]},\n')
        f.write('      "gates": [\n')

        for i, gate in enumerate(circuit["gates"]):
            comma = ',' if i < len(circuit["gates"]) - 1 else ''
            gate_str = (
                f'        {{"id": {gate["id"]}, '
                f'"type": "{gate["type"]}", '
                f'"in": {gate["in"]}}}{comma}\n'
            )
            f.write(gate_str)

        f.write('      ]\n')
        f.write('    }\n')
        f.write('  ]\n')
        f.write('}\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate N-bit comparison circuit for signed integers.")
    parser.add_argument("-b",
                        "--bits",
                        type=int,
                        default=32,
                        help="Number of bits that should be supported by the generated circuit (default: 32)")
    args = parser.parse_args()
    output_path = generate_cmp_signed_circuit(args.bits)
    print(f"Circuit generated and saved to {output_path}")
