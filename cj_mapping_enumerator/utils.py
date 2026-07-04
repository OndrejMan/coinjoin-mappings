from Txo import Txo, P2trInputVirtualSize, P2trOutputVirtualSize, P2wpkhInputVirtualSize, P2wpkhOutputVirtualSize
import multiprocessing
from math import inf
from collections import defaultdict
import time
from queue import Empty

def guess_script(address):
		if (len(address) > 60):
			return "P2tr"		
		return "P2wpkh"

def input_vsize(address):
    if (len(address) > 60):
        return P2trInputVirtualSize	
    return P2wpkhInputVirtualSize

def output_vsize(address):
    if (len(address) > 60):
        return P2trOutputVirtualSize	
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
