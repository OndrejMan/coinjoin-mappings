using Newtonsoft.Json.Linq;
using NBitcoin;
using WalletWasabi.Extensions;

namespace Sake;

public class JsonParser
{
	private List<string> txids;
	private JObject CoinJoins;
	public int Index;
	public bool HasCurrent => txids.Count > 0;
	public JsonParser(string Path)
	{
		var text = File.ReadAllText(Path);
		var json = JObject.Parse(text);
		CoinJoins = (JObject)json["coinjoins"];
		txids = CoinJoins.Properties().Select(x => x.Name).ToList();
		Index = 0;
	}


	public bool NextCJ() {
		Index++;
		if (Index >= txids.Count()) {
			return false;
		}
		return true;
	}

	public bool IsBlame() {
		var cj = (JObject)CoinJoins[txids[Index]];
		return cj["is_blame_round"].Value<bool>();
	}

	long CoordFee(long amount, string event_type, bool freeRemix) {
		if (amount <= 1000000 || (freeRemix && event_type != "MIX_ENTER")) {
			return 0;
		}
		return (long)(0.003*(double)amount);
	}

	ScriptType GuessScript(string address) {
		if (address.Length > 60) {
			return ScriptType.Taproot;
		}
		return ScriptType.P2WPKH;
	}

	long Vsize(IEnumerable<string> in_addresses, IEnumerable<string> out_addresses) {
		long vsize = 0;
		foreach (var a  in in_addresses) {
			vsize += GuessScript(a).EstimateInputVsize();
		}
		foreach (var a  in out_addresses) {
			vsize += GuessScript(a).EstimateOutputVsize();
		}
		return vsize;
	}

	public (List<Input>, FeeRate) GetInputs(bool freeRemix=true) {
		var cj = (JObject)CoinJoins[txids[Index]];
		var jInputs = (JObject)cj["inputs"];
		var jOutputs = (JObject)cj["outputs"];

		List<(long, string, string)> input_data = jInputs.Values().Select(i => (i["value"].Value<long>(), i["mix_event_type"].ToString(), i["address"].ToString())).ToList();

		List<(long, string)> output_data = jOutputs.Values().Select(i => (i["value"].Value<long>(), i["address"].ToString())).ToList();

		var output_sum = output_data.Select(x => x.Item1).Sum();
		var input_sum = input_data.Select(x => x.Item1).Sum();

		long vsize = Vsize(input_data.Select(x => x.Item3), output_data.Select(x => x.Item2));

		var fee_rate = new FeeRate((decimal)((input_sum - output_sum)/vsize));

		return (input_data.Select(x => new Input(Money.Satoshis(x.Item1), GuessScript(x.Item3), fee_rate, Money.Satoshis(CoordFee(x.Item1, x.Item2, freeRemix)))).ToList(), fee_rate);

	}

	public FeeRate GetFeeRate() {
		List<string> wallets = new();

		var cj = (JObject)CoinJoins[txids[Index]];
		var jInputs = (JObject)cj["inputs"];
		var jOutputs = (JObject)cj["outputs"];

		List<(long, string, string, string)> input_data = jInputs.Values().Select(i => (i["value"].Value<long>(), i["mix_event_type"].ToString(), i["address"].ToString(), i["wallet_name"].ToString())).ToList();

		List<(long, string, string)> output_data = jOutputs.Values().Select(i => (i["value"].Value<long>(), i["address"].ToString(), i["wallet_name"].ToString())).ToList();

		foreach (var x in input_data) {
			if (!wallets.Contains(x.Item4)){
				wallets.Add(x.Item4);
			}
		}
		var min_fee_rate = new FeeRate(1000m);
		foreach (var w in wallets) {
			var output_sum = output_data.Where(x => x.Item3 == w).Select(x => x.Item1).Sum();
			var input_sum = input_data.Where(x => x.Item4 == w).Select(x => x.Item1).Sum();
			long vsize = Vsize(input_data.Where(x => x.Item4 == w).Select(x => x.Item3), output_data.Where(x => x.Item3 == w).Select(x => x.Item2));
			var fee_rate = new FeeRate((decimal)((input_sum - output_sum)/vsize));
			if (fee_rate < min_fee_rate) {
				min_fee_rate = fee_rate;
			}
		}
		if (min_fee_rate < new FeeRate(1m)) {
			return new FeeRate(1m);
		}

		return min_fee_rate;
	}

	public string GetTXID() {
		return txids[Index];
	}

	public List<ulong> GetOutputValues() {
		var cj = (JObject)CoinJoins[txids[Index]];
		var jOutputs = (JObject)cj["outputs"];
		return jOutputs.Values().Select(i => i["value"].Value<ulong>()).ToList();
	}

	public (List<List<Input>>, FeeRate, List<string>) GetInputGroups(FeeRate? fee_rate=null, bool freeRemix=true) {
		
		var cj = (JObject)CoinJoins[txids[Index]];
		var jInputs = (JObject)cj["inputs"];
		var jOutputs = (JObject)cj["outputs"];
		Console.WriteLine((cj["txid"]).ToString());

		List<(long, string, string, string)> input_data = jInputs.Values().Select(i => (i["value"].Value<long>(), i["mix_event_type"].ToString(), i["address"].ToString(), i["wallet_name"].ToString())).ToList();

		List<(long, string, string)> output_data = jOutputs.Values().Select(i => (i["value"].Value<long>(), i["address"].ToString(), i["wallet_name"].ToString())).ToList();

		var output_sum = output_data.Select(x => x.Item1).Sum();
		var input_sum = input_data.Select(x => x.Item1).Sum();

		long vsize = Vsize(input_data.Select(x => x.Item3), output_data.Select(x => x.Item2));

		fee_rate ??= new FeeRate((decimal)((input_sum - output_sum)/vsize));

		input_data.Sort((x, y) => y.Item4.CompareTo(x.Item4));

		var w = input_data[0].Item4;
		List<List<Input>> result = new();
		List<Input> group = new();
		List<string> group_names = new();
		int i = 0;
		foreach (var x in input_data){
			if (x.Item4 != w){
				i++;
				result.Add(group);
				group_names.Add(w);
				w = x.Item4;
				group = new();
			}
			group.Add(new Input(Money.Satoshis(x.Item1), GuessScript(x.Item3), fee_rate, CoordFee(x.Item1, x.Item2, freeRemix)));
		}
		result.Add(group);
		group_names.Add(w);

		return (result, fee_rate, group_names);
	}


	public (List<List<ulong>>, List<string>) GetOutputGroups() {
		var cj = (JObject)CoinJoins[txids[Index]];
		var jOutputs = (JObject)cj["outputs"];

		List<(ulong, string)> output_data = jOutputs.Values().Select(i => (i["value"].Value<ulong>(), i["wallet_name"].ToString())).ToList();

		output_data.Sort((x, y) => y.Item2.CompareTo(x.Item2));

		var w = output_data[0].Item2;
		List<List<ulong>> result = new();
		List<ulong> group = new();
		List<string> group_names = new();

		foreach (var x in output_data){
			if (x.Item2 != w){
				result.Add(group);
				group_names.Add(w);
				w = x.Item2;
				group = new();
			}
			group.Add(x.Item1);
		}
		result.Add(group);
		group_names.Add(w);
		return (result, group_names);
	}

}
