import json
import requests
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair as SoldersKeypair
from solders.commitment_config import CommitmentLevel
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig
from tabulate import tabulate
import os
from colorama import init, Fore, Style

init(autoreset=True)

rpc_url = "https://api.mainnet-beta.solana.com"
pump_fun_api_url = "https://pumpportal.fun/api/trade-local"
wallets_file = "wallets.txt"
tokens_file = "tokens.txt"
log_file = "wallet_operations.log"

wallets = []
purchased_tokens = []


def ensure_files_exist():
    open(wallets_file, "a").close()
    open(tokens_file, "a").close()
    open(log_file, "a").close()


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def show_banner():
    print(Fore.RED + Style.BRIGHT + "SOLANA RUG PULL")
    print(Fore.YELLOW + "=" * 30 + "\n")


def log_operation(operation):
    with open(log_file, "a") as f:
        f.write(f"{operation}\n")


def persist_wallets():
    with open(wallets_file, "w") as f:
        for wallet in wallets:
            wallet_data = {
                "public_key": str(wallet["keypair"].pubkey()),
                "json": wallet["json"],
                "percentage": wallet["percentage"],
                "total_tokens": wallet["total_tokens"],
            }
            f.write(json.dumps(wallet_data) + "\n")


def load_wallets():
    if os.path.exists(wallets_file):
        with open(wallets_file, "r") as f:
            for line in f:
                wallet_data = json.loads(line.strip())
                keypair = SoldersKeypair.from_base58_string(wallet_data["json"])
                wallets.append(
                    {
                        "keypair": keypair,
                        "json": wallet_data["json"],
                        "percentage": wallet_data["percentage"],
                        "total_tokens": wallet_data["total_tokens"],
                    }
                )


def persist_tokens():
    with open(tokens_file, "w") as f:
        for token in purchased_tokens:
            f.write(json.dumps(token) + "\n")


def load_tokens():
    if os.path.exists(tokens_file):
        with open(tokens_file, "r") as f:
            for line in f:
                token_data = json.loads(line.strip())
                purchased_tokens.append(token_data)


def configure_wallets():
    global wallets
    wallets = []
    total_percentage = 0

    while total_percentage != 100:
        print(f"Total allocated so far: {total_percentage}%")

        private_key = input("Enter the private key of the wallet in base58 format: ")
        keypair = SoldersKeypair.from_base58_string(private_key)

        public_key = keypair.pubkey()
        print(f"Wallet with public address: {public_key}")

        try:
            percentage = float(
                input(
                    "Enter the percentage of the total purchase to use for this wallet: "
                )
            )
        except ValueError:
            print("Please enter a valid numeric value for the percentage.")
            continue

        if total_percentage + percentage > 100:
            print("The total percentage exceeds 100%. Restarting configuration...\n")
            wallets = []
            total_percentage = 0
        else:
            wallets.append(
                {
                    "keypair": keypair,
                    "percentage": percentage,
                    "json": private_key,
                    "total_tokens": 0,
                }
            )
            total_percentage += percentage
            print("Wallet added successfully.\n")

    print("Wallet configuration completed successfully.\n")
    persist_wallets()


def show_wallets():
    if not wallets:
        print("No wallets configured.\n")
        return

    wallet_info = [
        (
            wallet["keypair"].pubkey(),
            wallet["percentage"],
            wallet["total_tokens"],
        )
        for wallet in wallets
    ]
    print(
        tabulate(
            wallet_info,
            headers=["Wallet Address", "Percentage (%)", "Total Tokens"],
        )
    )
    print("\n")


def send_transaction_to_solana(tx_bytes, keypair):
    tx = VersionedTransaction.from_bytes(tx_bytes)
    commitment = CommitmentLevel.Confirmed
    config = RpcSendTransactionConfig(preflight_commitment=commitment)
    tx_payload = SendVersionedTransaction(tx, config)

    response = requests.post(
        url=rpc_url,
        headers={"Content-Type": "application/json"},
        data=tx_payload.to_json(),
    )
    tx_signature = response.json().get("result", None)

    if tx_signature:
        print(f"Transaction successful: https://solscan.io/tx/{tx_signature}")
        log_operation(f"Transaction successful: https://solscan.io/tx/{tx_signature}")
    else:
        print(f"Error sending transaction: {response.text}")
        log_operation(f"Error sending transaction: {response.text}")


def buy_from_pump_fun(
    wallet,
    token_address,
    amount,
    token_name,
    slippage=10,
    priority_fee=0.005,
    pool="pump",
):
    public_key = str(wallet.pubkey())

    response = requests.post(
        pump_fun_api_url,
        data={
            "publicKey": public_key,
            "action": "buy",
            "mint": token_address,
            "amount": amount,
            "denominatedInSol": "true",
            "slippage": slippage,
            "priorityFee": priority_fee,
            "pool": pool,
        },
    )

    if response.status_code == 200:
        tx_bytes = response.content
        send_transaction_to_solana(tx_bytes, wallet)
        log_operation(
            f"Bought {amount} SOL of {token_name} ({token_address}) with wallet {public_key}"
        )
        return amount
    else:
        print(f"Error buying for wallet {public_key}: {response.text}")
        log_operation(f"Error buying for wallet {public_key}: {response.text}")
        return 0


def sell_on_pump_fun(
    wallet, token_address, token_name, slippage=10, priority_fee=0.005, pool="pump"
):
    public_key = str(wallet.pubkey())
    total_tokens = wallet["total_tokens"]

    if total_tokens > 0:
        response = requests.post(
            pump_fun_api_url,
            data={
                "publicKey": public_key,
                "action": "sell",
                "mint": token_address,
                "amount": total_tokens,
                "denominatedInSol": "false",
                "slippage": slippage,
                "priorityFee": priority_fee,
                "pool": pool,
            },
        )

        if response.status_code == 200:
            tx_bytes = response.content
            send_transaction_to_solana(tx_bytes, wallet)
            log_operation(
                f"Sold {total_tokens} tokens of {token_name} ({token_address}) with wallet {public_key}"
            )
            return True
        else:
            print(f"Error selling for wallet {public_key}: {response.text}")
            log_operation(f"Error selling for wallet {public_key}: {response.text}")
            return False
    else:
        print(f"No tokens available to sell in wallet {public_key}.")
        log_operation(f"No tokens available to sell in wallet {public_key}.")
        return False


def buy_token():
    if not wallets:
        print("Please configure wallets before buying a token.\n")
        return

    token_address = input("Enter the token address: ")
    token_name = input("Enter a name to identify the token: ")
    total_sol = float(input("Enter the total amount of SOL to buy: "))

    all_successful = True

    for wallet in wallets:
        sol_to_spend = total_sol * wallet["percentage"] / 100
        print(
            f"Buying {sol_to_spend} SOL of {token_name} ({token_address}) with wallet {wallet['keypair'].pubkey()}."
        )
        total_tokens = buy_from_pump_fun(
            wallet["keypair"], token_address, sol_to_spend, token_name
        )
        if total_tokens == 0:
            all_successful = False
            break
        wallet["total_tokens"] = total_tokens

    if all_successful:
        purchased_tokens.append(
            {
                "address": token_address,
                "name": token_name,
                "amount": sum(wallet["total_tokens"] for wallet in wallets),
            }
        )
        persist_tokens()
        print("Purchase completed.\n")
    else:
        print(
            Fore.RED
            + "Purchase failed for one or more wallets. Please check the logs for details."
        )


def sell_token():
    if not wallets:
        print("Please configure wallets before selling a token.\n")
        return

    if not purchased_tokens:
        print("No purchased tokens to sell.\n")
        return

    print("Available tokens to sell:")
    for idx, token in enumerate(purchased_tokens):
        print(
            f"{idx + 1}. {token['name']} ({token['address']}) - {token['amount']} tokens"
        )

    choice = int(input("Select the token to sell: ")) - 1
    if 0 <= choice < len(purchased_tokens):
        token_to_sell = purchased_tokens[choice]
        all_successful = True
        for wallet in wallets:
            success = sell_on_pump_fun(
                wallet["keypair"], token_to_sell["address"], token_to_sell["name"]
            )
            if not success:
                all_successful = False
                break

        if all_successful:
            purchased_tokens.pop(choice)
            persist_tokens()
            print("Sale completed.\n")
        else:
            print(
                Fore.RED
                + "Sale failed for one or more wallets. Please check the logs for details."
            )
    else:
        print("Invalid selection.\n")


def reset_wallets_configuration():
    global wallets
    confirmation = input(
        Fore.RED
        + "Are you sure you want to reset wallet configuration? This will delete all configured wallets. (y/n): "
    )
    if confirmation.lower() == "y":
        wallets = []
        os.remove(wallets_file)
        ensure_files_exist()
        print(Fore.GREEN + "Wallet configuration successfully reset.\n")
    else:
        print(Fore.YELLOW + "Wallet configuration reset canceled.\n")
        input("Press Enter to continue…")


def watch_logs():
    if not os.path.exists(log_file):
        print("No logs found.")
        return

    with open(log_file, "r") as f:
        logs = f.readlines()
        if logs:
            print("Wallet Operations Log:")
            for log in logs:
                print(log.strip())
        else:
            print("No logs available.")


def show_menu():
    ensure_files_exist()
    load_wallets()
    load_tokens()

    while True:
        clear_terminal()
        show_banner()
        print(Fore.CYAN + "Menu:")
        print(Fore.YELLOW + "1. Configure wallets")
        print(Fore.YELLOW + "2. Buy a meme coin")
        print(Fore.YELLOW + "3. Sell the purchased token")
        print(Fore.YELLOW + "4. View configured wallets")
        print(Fore.YELLOW + "5. Watch logs")
        print(Fore.RED + "6. Reset wallet configuration")
        print(Fore.RED + "7. Exit")
        choice = input(Fore.CYAN + "Select an option: ")

        if choice == "1":
            clear_terminal()
            show_banner()
            configure_wallets()
        elif choice == "2":
            clear_terminal()
            show_banner()
            buy_token()
        elif choice == "3":
            clear_terminal()
            show_banner()
            sell_token()
        elif choice == "4":
            clear_terminal()
            show_banner()
            show_wallets()
            input("Press Enter to continue...")
        elif choice == "5":
            clear_terminal()
            show_banner()
            watch_logs()
            input("Press Enter to continue...")
        elif choice == "6":
            clear_terminal()
            show_banner()
            reset_wallets_configuration()
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print(Fore.RED + "Invalid option, please try again.\n")
            input("Press Enter to continue...")


show_menu()
