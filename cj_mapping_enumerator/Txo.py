from math import floor, ceil


P2wpkhInputVirtualSize = 69
P2wpkhOutputVirtualSize = 31

P2wshOutputVirtualSize = 43

P2trInputVirtualSize = 58
P2trOutputVirtualSize = 43



def effective_value(type, value, script_type, mfee_rate, cfee_rate):
    evalue = value
    if type == "input":
        evalue -= floor(cfee_rate*value)

        if cfee_rate != 0:
            print("cfee", cfee_rate*value)

        if script_type == "P2wpkh":
            evalue -= floor(mfee_rate*P2wpkhInputVirtualSize)
        
        elif script_type == "P2tr":
            evalue -= floor(mfee_rate*P2trInputVirtualSize)

        elif script_type == "P2wsh":
            raise ValueError(
                "P2WSH input virtual size depends on its witness script "
                "and cannot be inferred from the address"
            )
    
    elif type == "output":

        if script_type == "P2wpkh":
            evalue += floor(mfee_rate*P2wpkhOutputVirtualSize)
        
        elif script_type == "P2tr":
            evalue += floor(mfee_rate*P2trOutputVirtualSize)

        elif script_type == "P2wsh":
            evalue += floor(mfee_rate*P2wshOutputVirtualSize)

    else:
        raise Exception("Invalid Txo type") 

    return evalue


class Txo:

    def __init__(self, value, address, script_type, type, mfee_rate, cfee_rate=0):
        self.value = value
        self.address = address
        self.script_type = script_type
        self.type = type
        self.effective_value = effective_value(type, value, script_type, mfee_rate, cfee_rate)
