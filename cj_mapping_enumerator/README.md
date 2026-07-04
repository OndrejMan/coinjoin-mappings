# CoinJoin mappings enumerator

This tool enumerates Wasabi 2.x CoinJoin mappings. By default it prints structured
JSON; use `--output PATH` to preserve the same result in a file. Each transaction
gets a 60-second attempt followed by one 600-second retry, configurable through
`--timeout` and `--retry-timeout`.

### Running 
Install requirements using:
``pip install -r requirements.txt``

Examples of how the enumeration can be run:

``$ python run.py ./data/emulated_cjs.json``

``$ python run.py -c 0 -d 5000 --min_mining_fee 4 --max_mining_fee 5 --linked_addresses '[["bc1qd5u4f3ghsx94hrwy8veu3g34j4uhu2eaazvh9w", "bc1q0zf5eas57dsmzv8rd0pv28tljqyfkqxsvxdfep"]]' ./data/7e875be692881180ed3f322831615c280daf077bfd14bc120fb3c03dc6d381f6.json``

``$ python run.py -c 0 -d 5000 --min_mining_fee 6 --max_mining_fee 7 --linked_addresses '[["bc1q6gjafmqpxsvlzfx4nhvp2rjkpmddrn8r88u3k0", "bc1pncrcenzr5ud52kdw426c4r7ssrnyp8ajfxkqglxs52ktlt0rm4nsq736r9", "bc1p9phhhgptr45p8ca56afsupgj4z5ew7zqez3h8f9wzjaexklc66jqwj2tpe", "bc1p88pwjk05z2q4wm53k8uhkvahrvmxxdanjjys0laf8plcl8yzy5vq5l3yjn", "bc1pws5gjzazwf6e2u63e4h2weqru78htda6a9xw7u0uy578xudae7mslrqhwl", "bc1psxwv8ww3sxrun42a72c2yjyl0vskk74rk045yc0r5pq0ayqu6jgqlkzayx", "bc1p4chc84aujdsayhce53nfh80nqhff7ngk0fy4k7utqmjawuduv9gsjrwyjd", "bc1p466dh30leh5zfdqkywhf9mpr6sd8uls9sh9fsaspynt9v6pdvd3qkk4pl0", "bc1p67tgzg6t9l7sm5tcma0ypr657jqxm93v5p0nlv9tjsh8m88499rq3rl86w", "bc1pue3jwuf6qjxx3j2cpwqcu55juuulm3t7dwv382dr4ynew8py7unsu6n4sy"]]' ./data/f5f4fbf79355c777b9a83aef9202e85d4af83ffaf4b7f14e5ff6fd1b163eb3b0.json``

``$ python run.py -c 0 -d 5000 --min_mining_fee 5 --max_mining_fee 7 --linked_addresses '[["bc1p708q33zlqrewf546c2t364tgcrh3haljrq7yrxkeez56g5aqksvsdlhyn6", "bc1qp3zr5v4nd8pfu63hpc3dz6zctkf0vepam0gfj5", "bc1qx8sl4aa6xvxx0h5775j7u4pexdjn2q4hn72ew3", "bc1p8086fhpkkkdpc0fegw3rgfk59cg8gnsy8lxrr9xjqeu5kgztkzvsfwu78w", "bc1pg8823tjdy5pxa06qk2updgupdppyk8zafzzt660pw9m9j2ks3rcq42lv4j", "bc1pmqyjxxfpfenlttsxznxzknhprrfrhwzm8004ney3gkyy2fgeytksx38qfv", "bc1pmvptzfxpx6y5g33c6l28fzc46nygfcaedv5gfafwxtddtf5g7p9scckgqx", "bc1qshkk73xjjp5nmxrvqhsveu4ejf6cp073866yr7"]]' ./data/a0ddfff8b16eaa9c461a15a2b70d174530b649426ac0472464b62f4a5ef02d6a.json``

``$ python run.py -c 0 -d 5000 --min_mining_fee 4 --max_mining_fee 7 --linked_addresses '[["bc1pdh4grq3vvfww9y490c3esj09a84uytnynxvzxj82tnyd8lld4l7sqxku6s", "bc1pkxdkxmslgtzte576fw73kdlesk42d8vxelajt0y3y2pqhztmxa3q9dp7sw"], ["bc1qx47xq4wwxfpl4z6sn4dqyl4q0ff7qv7ljtqf8e", "bc1q48rznp4v6m7sl4j5jnyqa873nzeqycm9y4r4k7"]]' ./data/c92a6046249fd613019e5dccb0f6c188e4d607eade2738250a10b7e1da2a0489.json``

``$ python run.py -c 0 -d 5000 --min_mining_fee 4 --max_mining_fee 5 --linked_addresses '[["bc1qvj50aml5avdpuny30jnz8h5e8gcchvlh6crf9t", "bc1q54c8tpqhzxuaw23q002sva56nyaqudgev0cuhd", "bc1qlddhjr5yt5zvkt4qdfgdsjeyew48l69u5v4r55", "bc1qjdh8glhkhhugl6ldn4zlzd2na2842wjawr4uvv"]]' ./data/ad5ad29922ab3067ecfcc608eba03c3d0aef08ce80a75e563ba8904875648743.json``

Help:

```
$ python run.py --help
usage: CoinJoin mapping enumerator [-h] [-m MINING_FEE_RATE] [-c COORDINATION_FEE_RATE] [-d MAX_DECOMPOSITION_FEE] [--min_mining_fee MIN_MINING_FEE]
                                   [--max_mining_fee MAX_MINING_FEE] [-t TIMEOUT] [--mode MODE] [--linked_addresses LINKED_ADDRESSES]
                                   json_filename

positional arguments:
  json_filename

options:
  -h, --help            show this help message and exit
  -m MINING_FEE_RATE, --mining_fee_rate MINING_FEE_RATE
  -c COORDINATION_FEE_RATE, --coordination_fee_rate COORDINATION_FEE_RATE
  -d MAX_DECOMPOSITION_FEE, --max_decomposition_fee MAX_DECOMPOSITION_FEE
  --min_mining_fee MIN_MINING_FEE
  --max_mining_fee MAX_MINING_FEE
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout for one transaction in seconds
  --mode {numeric,all}  Choose numeric-value mappings or all concrete mappings
  -o OUTPUT, --output OUTPUT
                        Write structured JSON to this path
  --retry-timeout RETRY_TIMEOUT
                        Timeout used for the single retry
  --linked_addresses LINKED_ADDRESSES
                        Provide groups of linked addresses, e.g. [['address1', 'address2'], ['address3', 'address4', 'address5']]
```
