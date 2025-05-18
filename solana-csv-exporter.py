#!/usr/bin/env python3
"""
solana-csv-exporter.py - Export Solana wallet transaction history to CSV

Exports transaction history for a Solana wallet address to a CSV file,
supporting SPL tokens, native SOL transfers, and DEX trades through
Helius enhanced transaction data.

Usage: ./solana-csv-exporter.py -a <ADDRESS> [-o output.csv]

Required environment variable: HELIUS_API_KEY
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
if not HELIUS_API_KEY:
    print("Error: HELIUS_API_KEY not found in environment or .env file", file=sys.stderr)
    sys.exit(1)

API_URL = "https://api.helius.xyz/v0/addresses/{address}/transactions"
SOL_MINT = "So11111111111111111111111111111111111111112"  # SOL pseudo-mint

def lamports_to_sol(lamports):
    """Convert lamports to SOL"""
    return lamports / 1_000_000_000

def get_token_amount(transfer):
    """Get human-readable token amount from transfer object"""
    if "rawTokenAmount" in transfer:
        raw = transfer["rawTokenAmount"]
        return float(raw["tokenAmount"]) / (10 ** raw.get("decimals", 0))
    return float(transfer.get("tokenAmount", 0))

def fetch_transactions(address):
    """Fetch all transactions for an address with pagination"""
    before = None
    session = requests.Session()
    
    while True:
        url = API_URL.format(address=address)
        params = {"api-key": HELIUS_API_KEY}
        if before:
            params["before"] = before
            
        # Simple retry with backoff
        for attempt in range(5):
            try:
                response = session.get(url, params=params, timeout=30)
                if response.status_code == 429:  # Rate limited
                    delay = min(2 ** attempt, 60)
                    print(f"Rate limited - retrying in {delay}s...", file=sys.stderr)
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == 4:  # Last attempt
                    print(f"Error fetching transactions: {e}", file=sys.stderr)
                    sys.exit(1)
                time.sleep(2 ** attempt)
        
        data = response.json()
        if not data:
            break
            
        for tx in data:
            yield tx
            
        before = data[-1]["signature"]
        time.sleep(0.1)  # Gentle rate limiting

def process_transaction(tx, wallet_address):
    """Process transaction into CSV row format"""
    # Track incoming and outgoing transfers
    sent = []
    received = []
    
    # Process token transfers
    for transfer in tx.get("tokenTransfers", []):
        if transfer["fromUserAccount"] == wallet_address and transfer["toUserAccount"] != wallet_address:
            sent.append(transfer)
        elif transfer["toUserAccount"] == wallet_address and transfer["fromUserAccount"] != wallet_address:
            received.append(transfer)
    
    # Process native SOL transfers
    for transfer in tx.get("nativeTransfers", []):
        sol_transfer = {
            "fromUserAccount": transfer["fromUserAccount"],
            "toUserAccount": transfer["toUserAccount"],
            "mint": SOL_MINT,
            "rawTokenAmount": {"tokenAmount": transfer["amount"], "decimals": 9},
        }
        
        if transfer["fromUserAccount"] == wallet_address and transfer["toUserAccount"] != wallet_address:
            sent.append(sol_transfer)
        elif transfer["toUserAccount"] == wallet_address and transfer["fromUserAccount"] != wallet_address:
            received.append(sol_transfer)
    
    # Skip if no relevant transfers
    if not sent and not received:
        return None
        
    # Aggregate transfers by currency
    def aggregate_transfers(transfers):
        if not transfers:
            return None, None, None
            
        totals = {}
        counterparty = transfers[0]["toUserAccount"]
        if transfers[0]["fromUserAccount"] != wallet_address:
            counterparty = transfers[0]["fromUserAccount"]
            
        for t in transfers:
            mint = t["mint"]
            amount = get_token_amount(t)
            totals[mint] = totals.get(mint, 0) + amount
            
        if not totals:
            return None, None, None
            
        primary_mint = next(iter(totals))
        return round(totals[primary_mint], 9), primary_mint, counterparty
    
    # Get aggregated data
    sent_amount, sent_currency, sent_counterparty = aggregate_transfers(sent)
    received_amount, received_currency, received_counterparty = aggregate_transfers(received)
    
    # Calculate fee
    fee_lamports = int(tx.get("fee", 0))
    fee_sol = round(lamports_to_sol(fee_lamports), 9) if fee_lamports else ""
    
    # Create CSV row
    return {
        "Date": datetime.fromtimestamp(tx["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "TxHash": tx["signature"],
        "TxSrc": sent_counterparty or received_counterparty or "",
        "TxDest": received_counterparty or sent_counterparty or "",
        "Sent Amount": sent_amount or "",
        "Sent Currency": sent_currency or "",
        "Received Amount": received_amount or "",
        "Received Currency": received_currency or "",
        "Fee Amount": fee_sol,
        "Fee Currency": "SOL" if fee_lamports else "",
    }

def export_to_csv(address, output_file):
    """Export transactions to CSV file"""
    fieldnames = [
        "Date", "TxHash", "TxSrc", "TxDest",
        "Sent Amount", "Sent Currency", "Received Amount", "Received Currency",
        "Fee Amount", "Fee Currency"
    ]
    
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for tx in fetch_transactions(address):
            row = process_transaction(tx, address)
            if row:
                writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="Export Solana transaction history to CSV")
    parser.add_argument("-a", "--address", required=True, help="Solana wallet address")
    parser.add_argument("-o", "--output", default="transactions.csv", help="Output CSV file")
    args = parser.parse_args()
    
    print(f"Exporting transactions for {args.address} to {args.output}...")
    try:
        export_to_csv(args.address, args.output)
        print("Export completed successfully!")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()