## Second Batch Chain Checks

Date: March 16, 2026

Purpose:

- spot-check whether the strongest names from the second scan batch have usable long-dated public call chains
- see whether the current `shares` bias is caused by missing chain evidence or by genuinely weak LEAPS setups

## Names checked

### `AXTI`

Source:

- [AXTI raw capture](/home/d/codex/MiroFish/research/options-data/raw/AXTI/2026-03-16T10-33-58-169Z/best-table.csv)
- [AXTI normalized chain](/home/d/codex/MiroFish/research/options-data/2026-03-16/AXTI-chain-yahoo-2027-01-15.json)

Result:

- Jan 15, 2027 calls were present
- every captured call had `bid = 0` and `ask = 0`
- open interest was effectively unusable

Read:

- this supports the engine keeping `AXTI` as a `shares` expression
- even if the equity thesis is attractive, the public LEAPS path is currently too illiquid to treat as a serious expression

### `MTSI`

Source:

- [MTSI raw capture](/home/d/codex/MiroFish/research/options-data/raw/MTSI/2026-03-16T10-35-28-099Z/best-table.csv)

Result:

- Yahoo showed `There are no calls.`
- no usable far-dated chain was available on the checked page

Read:

- this also supports the engine staying with `shares`

### `AMBA`

Source:

- [AMBA raw capture](/home/d/codex/MiroFish/research/options-data/raw/AMBA/2026-03-16T10-36-38-375Z/best-table.csv)
- [AMBA normalized chain](/home/d/codex/MiroFish/research/options-data/2026-03-16/AMBA-chain-yahoo-2027-01-15.json)

Result:

- Jan 15, 2027 calls were available
- there were `12` contracts with positive bid and ask
- representative live rows:
  - `27.5c`: bid `26.5`, ask `30.3`, OI `69`, IV `88.99%`
  - `32.5c`: bid `23.0`, ask `26.6`, OI `308`, IV `84.18%`
  - `37.5c`: bid `20.0`, ask `23.4`, OI `300`, IV `81.79%`
  - `75c`: bid `4.7`, ask `8.1`, OI `114`, IV `66.75%`
  - `105c`: bid `6.3`, ask `9.0`, OI `97`, IV `96.89%`

Read:

- unlike `AXTI`, `AMBA` does have a real far-dated call surface
- but the combination of high implied volatility and wide spreads does not obviously argue for a strong LEAPS bias
- that supports the current engine keeping `AMBA` as a stock thesis unless better relative-value evidence appears

## Takeaway

The second batch chain checks support the current expression logic:

- `AXTI`: stock thesis, not realistic LEAPS path on current public chain evidence
- `MTSI`: stock thesis, no useful far-dated public chain found
- `AMBA`: usable LEAPS exist, but not obviously cheap enough to override shares

This is useful because it means the lack of new `LEAPS` picks in the second batch is not just a scoring artifact. At least for these checked names, the public long-dated options path really does look weaker than the stock path.
