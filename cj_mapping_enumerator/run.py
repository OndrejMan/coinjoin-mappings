import argparse
import json
from utils import load_cj, run_with_timeout
from cj_mappings import get_all_mappings, get_numeric_mappings
from math import inf
from preprocessing import preprocess

import sys
sys.setrecursionlimit(500000000)

max_vsize = 10*69 + 10*58

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog="CoinJoin mapping enumerator")
    parser.add_argument("json_filename")
    parser.add_argument("-m", "--mining_fee_rate", default=1, type=int)
    parser.add_argument("-c", "--coordination_fee_rate", default=0.003, type=float)
    parser.add_argument("-d", "--max_decomposition_fee", default=6000, type=int)
    parser.add_argument("--min_mining_fee", type=int)
    parser.add_argument("--max_mining_fee", type=int)
    parser.add_argument("-t", "--timeout", help="Timeout for one transaction in seconds", default=60, type=int)
    parser.add_argument("--mode", help="Choose mode 'numeric' or 'all' mappings", default="numeric")
    parser.add_argument("--linked_addresses", type=str, help="Provide groups of linked addresses, e.g. [['address1', 'address2'], ['address3', 'address4', 'address5']]")

    args = parser.parse_args()
    

    with open(args.json_filename, "r") as file:
        j = json.load(file)

    mfee_diff = 0
    mfee_rate = args.mining_fee_rate

    if args.min_mining_fee is not None:
        mfee_rate = args.min_mining_fee
        mfee_diff = args.max_mining_fee - args.min_mining_fee
    
    else:
        mfee_rate = args.mining_fee_rate
    
    max_error = args.max_decomposition_fee + mfee_diff * max_vsize


    for txid,cj in j["coinjoins"].items():

        inputs, outputs = load_cj(cj, mfee_rate, args.coordination_fee_rate)

        if args.linked_addresses is not None:
            l_addresses = json.loads(args.linked_addresses)
            inputs,outputs = preprocess(inputs, outputs, l_addresses)

        print("TXID:", txid)


        if args.mode == "numeric":
            def callable_enum(result_queue):
                c = 0
                for m in get_numeric_mappings(inputs, outputs, max_error=max_error):
                    c += 1
                result_queue.put(c)

            t,c = run_with_timeout(args.timeout, callable_enum)
        
        elif args.mode == "all":
            def callable_enum(result_queue):
                c = 0
                for m in get_all_mappings(inputs, outputs, max_error=args.max_decomposition_fee):
                    c += 1
                result_queue.put(c)

            t,c = run_with_timeout(args.timeout, callable_enum)

        else:
            raise Exception("Invalid mode {}", args.mode)

        if t == inf:
            print("Enumeration not finished before timeout")
        
        else:
            print("Enumeration time:", t)
            print("Total mappings:", c)
            print()
        


