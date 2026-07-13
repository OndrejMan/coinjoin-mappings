using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using NBitcoin;
using Sake;

static Dictionary<string, string> Options(string[] args)
{
    var values = new Dictionary<string, string>();
    for (var i = 0; i < args.Length; i++)
    {
        if (!args[i].StartsWith("--") || i + 1 >= args.Length) throw new ArgumentException($"Invalid argument: {args[i]}");
        values[args[i]] = args[++i];
    }
    return values;
}

static int MatchedOutputs(IEnumerable<ulong> generated, IEnumerable<ulong> actual)
{
    var remaining = generated.ToList();
    var matched = 0;
    foreach (var value in actual)
    {
        var index = remaining.IndexOf(value);
        if (index >= 0) { matched++; remaining.RemoveAt(index); }
    }
    return matched;
}

static bool OutputsMatchWithChangeTolerance(IEnumerable<ulong> expected, IEnumerable<ulong> candidate)
{
    var expectedValues = expected.OrderBy(value => value).ToList();
    var candidateValues = candidate.OrderBy(value => value).ToList();
    if (expectedValues.Count != candidateValues.Count) return false;
    var changedOutputFound = false;
    for (var index = 0; index < expectedValues.Count; index++)
    {
        if (expectedValues[index] == candidateValues[index]) continue;
        if (changedOutputFound) return false;
        var difference = expectedValues[index] > candidateValues[index]
            ? expectedValues[index] - candidateValues[index]
            : candidateValues[index] - expectedValues[index];
        if (difference >= 100) return false;
        changedOutputFound = true;
    }
    return true;
}

static int StableSeed(int seed, string txid, string scope)
{
    var material = Encoding.UTF8.GetBytes($"{seed}:{txid}:{scope}");
    return BinaryPrimitives.ReadInt32LittleEndian(SHA256.HashData(material)) & int.MaxValue;
}

var options = Options(args);
var unknownOptions = options.Keys.Except(new[] { "--input", "--output", "--seed", "--samples" }).ToList();
if (unknownOptions.Count > 0) throw new ArgumentException($"Unknown option: {unknownOptions[0]}");
if (!options.TryGetValue("--input", out var input)) throw new ArgumentException("--input is required");
if (!options.TryGetValue("--output", out var output)) throw new ArgumentException("--output is required");
var seed = options.TryGetValue("--seed", out var seedText) ? int.Parse(seedText) : 20260704;
var samples = options.TryGetValue("--samples", out var sampleText) ? int.Parse(sampleText) : 99;
if (samples <= 0) throw new ArgumentOutOfRangeException("--samples", "must be greater than zero");

var parser = new JsonParser(input);
var transactions = new Dictionary<string, object>();
long matchedOutputs = 0, totalOutputs = 0, walletMatches = 0, totalWallets = 0, perfectMatches = 0,
    lengthMatches = 0;
var hasNext = parser.HasCurrent;
while (hasNext)
{
    if (!parser.IsBlame())
    {
        var txid = parser.GetTXID();
        var feeRate = parser.GetFeeRate();
        var (groups, effectiveFeeRate, inputNames) = parser.GetInputGroups(feeRate);
        var (actualGroups, outputNames) = parser.GetOutputGroups();
        var mixer = new Mixer(effectiveFeeRate, Money.Satoshis(5000m), Money.Coins(43000m),
            new List<ScriptType> { ScriptType.P2WPKH, ScriptType.Taproot },
            new Random(StableSeed(seed, txid, "full")));
        var generated = mixer.CompleteMix(groups).Select(values => values.ToList()).ToList();
        var txMatched = 0;
        var txOutputs = generated.Sum(group => group.Count);
        var txActualOutputs = actualGroups.Sum(group => group.Count);
        var txWalletMatches = 0;
        var txLengthMatches = 0;
        for (var groupIndex = 0; groupIndex < generated.Count; groupIndex++)
        {
            var generatedGroup = generated[groupIndex];
            var actualGroup = groupIndex < actualGroups.Count ? actualGroups[groupIndex] : new List<ulong>();
            var matches = MatchedOutputs(generatedGroup, actualGroup);
            if (generatedGroup.Count == actualGroup.Count) txLengthMatches++;
            txMatched += matches;
            if (matches == generatedGroup.Count) txWalletMatches++;
        }
        var decomposition = new Dictionary<string, object>();
        foreach (var wallet in inputNames)
        {
            var walletIndex = inputNames.IndexOf(wallet);
            var counts = new Dictionary<string, int>();
            var random = new Random(StableSeed(seed, txid, $"wallet:{wallet}"));
            for (var sample = 0; sample < samples; sample++)
            {
                var sampleMixer = new Mixer(effectiveFeeRate, Money.Satoshis(5000m), Money.Coins(43000m),
                    new List<ScriptType> { ScriptType.P2WPKH, ScriptType.Taproot }, random);
                foreach (var values in sampleMixer.SingleWalletMix(groups[walletIndex],
                    groups.Where((_, other) => other != walletIndex).SelectMany(value => value).ToList()))
                {
                    var key = string.Join(",", values.OrderByDescending(value => value));
                    counts[key] = counts.GetValueOrDefault(key) + 1;
                }
            }
            var outputIndex = outputNames.IndexOf(wallet);
            var ranked = counts.OrderByDescending(pair => pair.Value).ThenBy(pair => pair.Key).ToList();
            int? rank = null;
            if (outputIndex >= 0)
            {
                var rankIndex = ranked.FindIndex(pair => OutputsMatchWithChangeTolerance(
                    actualGroups[outputIndex], pair.Key.Split(',').Select(ulong.Parse)));
                if (rankIndex >= 0) rank = rankIndex + 1;
            }
            decomposition[wallet] = new { options = counts.Count, actual_rank = rank == 0 ? null : rank };
        }
        var fullMatch = txWalletMatches == generated.Count;
        transactions[txid] = new { fee_rate_sat_per_byte = feeRate.SatoshiPerByte,
            matched_outputs = txMatched, total_outputs = txOutputs, actual_outputs = txActualOutputs,
            wallet_matches = txWalletMatches, total_wallets = generated.Count,
            actual_wallets = actualGroups.Count,
            length_matches = txLengthMatches,
            full_coinjoin_match = fullMatch, decomposition };
        matchedOutputs += txMatched; totalOutputs += txOutputs;
        walletMatches += txWalletMatches; totalWallets += generated.Count;
        lengthMatches += txLengthMatches;
        if (fullMatch) perfectMatches++;
    }
    hasNext = parser.NextCJ();
}

var result = new { schema_version = "1.0", tool = "sake", seed, samples,
    summary = new { transactions = transactions.Count, matched_outputs = matchedOutputs,
        total_outputs = totalOutputs, output_match_rate = totalOutputs == 0 ? null : (double?)matchedOutputs / totalOutputs,
        wallet_matches = walletMatches, total_wallets = totalWallets,
        wallet_match_rate = totalWallets == 0 ? null : (double?)walletMatches / totalWallets,
        length_matches = lengthMatches,
        length_match_rate = totalWallets == 0 ? null : (double?)lengthMatches / totalWallets,
        full_coinjoin_matches = perfectMatches,
        full_coinjoin_match_rate = transactions.Count == 0 ? null : (double?)perfectMatches / transactions.Count },
    transactions };
var rendered = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
File.WriteAllText(output, rendered + Environment.NewLine);
Console.WriteLine(rendered);
