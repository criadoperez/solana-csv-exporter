# solana-csv-exporter

Transaction history exporter for Solana blockchain

## Overview

`solana-csv-exporter.py` is a Python tool that exports the transaction history of any Solana address into a CSV file, supporting both native SOL transfers and SPL tokens, as well as DEX trades. The tool leverages the Helius Enhanced Transactions API to provide comprehensive and accurate transaction data without requiring complex instruction decoding.

## Features

- **Complete transaction history export** with categorization of deposits, withdrawals, and trades
- **DEX-aware** through Helius enhanced transaction data
- **Native SOL and SPL token support**
- **Rate-limit handling** with automatic retries and backoff
- **Simple CSV output format** ready for accounting or portfolio software

## CSV Output Format

| Column | Description |
|--------|-------------|
| `Date` | UTC timestamp of the transaction |
| `TxHash` | Transaction signature (unique identifier) |
| `TxSrc` | Source address for incoming funds |
| `TxDest` | Destination address for outgoing funds |
| `Sent Amount` | Amount of tokens sent from the wallet |
| `Sent Currency` | Currency/token identifier for sent tokens |
| `Received Amount` | Amount of tokens received by the wallet |
| `Received Currency` | Currency/token identifier for received tokens |
| `Fee Amount` | Transaction fee (in SOL) |
| `Fee Currency` | Always "SOL" for transaction fees |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/criadoperez/solana-csv-exporter.git
cd solana-csv-exporter

# 2. Set up a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install requests python-dotenv

# 4. Set your Helius API key
echo 'HELIUS_API_KEY=your_api_key_here' > .env

# 5. Make the script executable
chmod +x solana-csv-exporter.py
```

## Usage

Basic usage:
```bash
./solana-csv-exporter.py -a DeutWrchKzcSZM9HxoXkpGfYhMVzFabkf5NQvSKDUYJ5
```

Specify an output file:
```bash
./solana-csv-exporter.py -a DeutWrchKzcSZM9HxoXkpGfYhMVzFabkf5NQvSKDUYJ5 -o my_transactions.csv
```

### Command-line Arguments

```
-a, --address   Required   Solana wallet address to export
-o, --output               Output CSV file path (default: transactions.csv)
```

## How It Works

1. **API Connection**: The tool connects to Helius Enhanced Transactions API using your API key from the `.env` file
2. **Transaction Fetching**: All transactions for the address are retrieved with pagination
3. **Transaction Processing**: Each transaction is analyzed to identify:
   - Tokens sent from the address
   - Tokens received by the address
   - Transaction fees paid
4. **CSV Generation**: Data is formatted and written to a CSV file with the specified columns

## Technical Details

- **Token Handling**: Native SOL is treated as a token with mint address `So11111111111111111111111111111111111111112`
- **Aggregation**: Multiple transfers of the same token in a transaction are summed up
- **Rate Limiting**: The script implements exponential backoff when rate limited by the API

## Limitations

- Complex multi-asset trades are simplified to show only the primary token exchanges
- Very new or exotic DEX protocols may not be fully decoded by Helius, appearing as simple transfers
- Only includes on-chain activity; off-chain actions like CEX transfers aren't captured

## Requirements

- Python 3.8 or higher
- `requests` and `python-dotenv` Python packages
- Helius API key (free tier available at [helius.xyz](https://helius.xyz))

## License

This project is free and open source software, released under the GNU AGPL v3 license. 