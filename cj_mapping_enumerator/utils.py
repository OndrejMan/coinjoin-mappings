from Txo import (
    Txo,
    P2trInputVirtualSize,
    P2trOutputVirtualSize,
    P2wpkhInputVirtualSize,
    P2wpkhOutputVirtualSize,
    P2wshOutputVirtualSize,
)
import multiprocessing
from math import inf
from collections import defaultdict
import time
from queue import Empty


BECH32_HRPS = ("bc", "tb", "bcrt")
BECH32_WITNESS_ADDRESS_OVERHEAD = 8  # separator, version, and six-character checksum
WITNESS_20_BYTE_PROGRAM_ENCODED_LENGTH = 32
WITNESS_32_BYTE_PROGRAM_ENCODED_LENGTH = 52


def _matches_witness_address(address, version_character, encoded_program_length):
    normalized = address.lower()
    return any(
        normalized.startswith(f"{hrp}1{version_character}")
        and len(normalized)
        == len(hrp) + encoded_program_length + BECH32_WITNESS_ADDRESS_OVERHEAD
        for hrp in BECH32_HRPS
    )


def is_taproot(address):
    return _matches_witness_address(
        address,
        "p",
        WITNESS_32_BYTE_PROGRAM_ENCODED_LENGTH,
    )


def is_p2wsh(address):
    return _matches_witness_address(
        address,
        "q",
        WITNESS_32_BYTE_PROGRAM_ENCODED_LENGTH,
    )


def is_p2wpkh(address):
    return _matches_witness_address(
        address,
        "q",
        WITNESS_20_BYTE_PROGRAM_ENCODED_LENGTH,
    )


def guess_script(address):
    if is_taproot(address):
        return "P2tr"
    if is_p2wsh(address):
        return "P2wsh"
    if is_p2wpkh(address):
        return "P2wpkh"
    raise ValueError(f"Unsupported or invalid witness address: {address}")


def input_vsize(address):
    script_type = guess_script(address)
    if script_type == "P2tr":
        return P2trInputVirtualSize
    if script_type == "P2wpkh":
        return P2wpkhInputVirtualSize
    raise ValueError(
        "P2WSH input virtual size depends on its witness script "
        "and cannot be inferred from the address"
    )


def output_vsize(address):
    script_type = guess_script(address)
    if script_type == "P2tr":
        return P2trOutputVirtualSize
    if script_type == "P2wsh":
        return P2wshOutputVirtualSize
    return P2wpkhOutputVirtualSize


def cfee_rate(inp, base_cfee_rate):
     if inp["mix_event_type"] == "MIX_ENTER" and inp["value"] > 1000000:
          return base_cfee_rate
     return 0


def load_cj(cj, mfee_rate, base_cfee_rate):
    txid = cj["txid"]
    inputs = []
    outputs = []

    for ind, inp in cj["inputs"].items():
        inputs.append(Txo(inp["value"], inp["address"], guess_script(inp["address"]), "input", mfee_rate, cfee_rate(inp, base_cfee_rate)))

    for ind, out in cj["outputs"].items():
        outputs.append(Txo(out["value"], out["address"], guess_script(out["address"]), "output", mfee_rate, 0))

    return inputs, outputs


def load_real_mapping(cj, mfee_rate, base_cfee_rate):

    inputs = defaultdict(list)
    txid = cj["txid"]


    for ind, inp in cj["inputs"].items():
        if inp["wallet_name"] == "Coordinator":
            print("Coordinator in input")

        if "-" not in inp["wallet_name"]:
            print(inp["wallet_name"], "strange name")

        inputs[inp["wallet_name"]].append(Txo(inp["value"], inp["address"], guess_script(inp["address"]), "input", mfee_rate, cfee_rate(inp, base_cfee_rate) ))

    outputs = defaultdict(list)
    for ind, out in cj["outputs"].items():

        if out["wallet_name"] == "Coordinator":
             print("coordinator:", out["value"])

        if "-" not in out["wallet_name"] and out["wallet_name"] != "Coordinator":
            print(out["wallet_name"], "strange name")
        
        outputs[out["wallet_name"]].append(Txo(out["value"], out["address"], guess_script(out["address"]), "output", mfee_rate, 0))


    return inputs, outputs

def real_num_mapping(ins, outs):
    num_mapping = []
    for k in ins:
        inps = [i.effective_value for i in ins[k]]
        outps = [i.effective_value for i in outs[k]]
        num_mapping.append((inps, outps))
    return num_mapping

def compare_num_mappings(m1, m2):
    if len(m1) != len(m2):
        return False
    
    v = [False]*len(m2)

    for sm1 in m1:
        for i,sm2 in enumerate(m2):
            if v[i]:
                continue
            if len(sm1[0]) != len(sm2[0]) or len(sm1[1]) != len(sm2[1]):
                   continue
              
            if sorted(sm1[0]) == sorted(sm2[0]) and sorted(sm1[1]) == sorted(sm2[1]):
                v[i] = True
                break
        else:
            return False
    return True


def run_with_timeout(timeout, func, *args, **kwargs):
    total_time = 0
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=func, args=args + (result_queue, ), kwargs=kwargs)
    start = time.time()
    process.start()
    process.join(timeout)
    end = time.time()
    total_time = end - start

    if process.is_alive():
        total_time = inf
        process.terminate()  # Forcefully kill the process
        process.join()  # Ensure cleanup
        result = inf
    else:
        try:
            result = result_queue.get(timeout=1)
        except Empty as error:
            raise RuntimeError(
                f"enumeration worker exited with code {process.exitcode} without returning a result"
            ) from error

    return total_time, result
