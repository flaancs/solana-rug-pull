import json
import requests
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt, RetryError
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
transaction_fee_sol = 0.003

wallets = []
purchased_tokens = []


def ensure_files_exist():
    open(wallets_file, "a").close()
    open(tokens_file, "a").close()
    open(log_file, "a").close()


def log_operation(operation):
    try:
        with open(log_file, "a") as f:
            f.write(f"{operation}\n")
    except Exception as e:
        print(Fore.RED + f"Error writing to log: {str(e)}")


def show_banner():
    print(Fore.RED + Style.BRIGHT + "SOLANA RUG PULL")
    print(Fore.YELLOW + "=" * 30 + "\n")


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


@retry(wait=wait_fixed(3), stop=stop_after_attempt(10))
def send_transaction_to_solana(tx_bytes, keypair):
    try:
        print(Fore.YELLOW + "Sending transaction to Solana network...")
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
            print(
                Fore.GREEN
                + f"Transaction successful: https://solscan.io/tx/{tx_signature}"
            )
            log_operation(
                f"Transaction successful: https://solscan.io/tx/{tx_signature}"
            )
        else:
            error_code = response.json().get("error", {}).get("code")
            error_msg = response.json().get("error", {}).get("message")

            if error_code == -32003:
                raise Exception("Transaction signature verification failure")
            elif error_code == 429:
                raise Exception("Too many requests, retrying...")

            print(Fore.RED + f"Error sending transaction: {response.text}")
            raise Exception(f"Error sending transaction: {response.text}")

    except Exception as e:
        print(Fore.RED + f"Error: {str(e)}")
        raise


@retry(wait=wait_fixed(2), stop=stop_after_attempt(5))
def buy_from_pump_fun(
    wallet,
    token_address,
    amount,
    token_name,
    slippage=10,
    priority_fee=0.005,
    pool="pump",
):
    public_key = str(wallet["keypair"].pubkey())
    print(
        Fore.YELLOW
        + f"Initiating purchase for {amount} SOL of {token_name} with wallet {public_key}..."
    )

    adjusted_amount = max(amount - transaction_fee_sol, 0)

    response = requests.post(
        pump_fun_api_url,
        data={
            "publicKey": public_key,
            "action": "buy",
            "mint": token_address,
            "amount": adjusted_amount,
            "denominatedInSol": "true",
            "slippage": slippage,
            "priorityFee": priority_fee,
            "pool": pool,
        },
    )

    if response.status_code == 200:
        tx_bytes = response.content
        send_transaction_to_solana(tx_bytes, wallet["keypair"])
        log_operation(
            f"Bought {adjusted_amount} SOL of {token_name} ({token_address}) with wallet {public_key}"
        )
        print(
            Fore.GREEN
            + f"Successfully bought {adjusted_amount} SOL of {token_name} with wallet {public_key}."
        )
        return adjusted_amount
    else:
        error_msg = f"Error buying for wallet {public_key}: {response.text}"
        print(Fore.RED + error_msg)
        log_operation(error_msg)
        raise Exception(error_msg)


@retry(wait=wait_fixed(2), stop=stop_after_attempt(5))
def sell_on_pump_fun(
    wallet, token_address, token_name, slippage=10, priority_fee=0.005, pool="pump"
):
    public_key = str(wallet["keypair"].pubkey())
    total_tokens = wallet.get("total_tokens", 0)

    print(
        Fore.YELLOW
        + f"Attempting to sell {total_tokens} tokens of {token_name} with wallet {public_key}..."
    )

    if total_tokens == 0:
        error_msg = f"No tokens available to sell in wallet {public_key}."
        print(Fore.RED + error_msg)
        log_operation(error_msg)
        raise Exception(error_msg)

    adjusted_total_tokens = max(total_tokens - transaction_fee_sol, 0)

    if adjusted_total_tokens > 0:
        response = requests.post(
            pump_fun_api_url,
            data={
                "publicKey": public_key,
                "action": "sell",
                "mint": token_address,
                "amount": adjusted_total_tokens,
                "denominatedInSol": "false",
                "slippage": slippage,
                "priorityFee": priority_fee,
                "pool": pool,
            },
        )

        if response.status_code == 200:
            tx_bytes = response.content
            send_transaction_to_solana(tx_bytes, wallet["keypair"])
            log_operation(
                f"Sold {adjusted_total_tokens} tokens of {token_name} ({token_address}) with wallet {public_key}"
            )
            print(
                Fore.GREEN
                + f"Successfully sold {adjusted_total_tokens} tokens of {token_name} with wallet {public_key}."
            )
            time.sleep(2)
            return True
        else:
            error_msg = f"Error selling for wallet {public_key}: {response.text}"
            print(Fore.RED + error_msg)
            log_operation(error_msg)
            raise Exception(error_msg)
    else:
        error_msg = (
            f"Not enough tokens to cover the transaction fee in wallet {public_key}."
        )
        print(Fore.RED + error_msg)
        log_operation(error_msg)
        raise Exception(error_msg)


async def async_sell_token(token_to_sell):
    all_successful = True
    tasks = []

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        for wallet in wallets:
            tasks.append(
                loop.run_in_executor(
                    executor,
                    handle_retries,
                    sell_on_pump_fun,
                    wallet,
                    token_to_sell["address"],
                    token_to_sell["name"],
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(Fore.RED + f"Sale failed: {str(result)}")
                log_operation(f"Sale failed: {str(result)}")
                all_successful = False

        if all_successful:
            purchased_tokens.remove(token_to_sell)
            persist_tokens()
            print(Fore.GREEN + "Sale completed.\n")
        else:
            print(
                Fore.RED
                + "Sale failed for one or more wallets. Please check the logs for details."
            )

    input(Fore.CYAN + "Press any key to continue...")


def handle_retries(func, *args):
    try:
        func(*args)
    except RetryError as e:
        error_msg = f"RetryError: {str(e)}"
        print(Fore.RED + error_msg)
        log_operation(error_msg)
        raise e
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(Fore.RED + error_msg)
        log_operation(error_msg)
        raise e


async def async_buy_token(token_address, token_name, total_sol):
    all_successful = True
    tasks = []

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        for wallet in wallets:
            sol_to_spend = total_sol * wallet["percentage"] / 100
            print(
                Fore.YELLOW
                + f"Buying {sol_to_spend} SOL of {token_name} with wallet {wallet['keypair'].pubkey()}."
            )
            tasks.append(
                loop.run_in_executor(
                    executor,
                    buy_from_pump_fun,
                    wallet,
                    token_address,
                    sol_to_spend,
                    token_name,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(Fore.RED + f"Purchase failed: {str(result)}")
                log_operation(f"Purchase failed: {str(result)}")
                all_successful = False

        if all_successful:
            purchased_tokens.append(
                {
                    "address": token_address,
                    "name": token_name,
                    "amount": sum(wallet["total_tokens"] for wallet in wallets),
                }
            )
            persist_tokens()
            print(Fore.GREEN + "Purchase completed.\n")
        else:
            print(
                Fore.RED
                + "Purchase failed for one or more wallets. Please check the logs for details."
            )

    input(Fore.CYAN + "Press any key to continue...")


async def buy_token():
    if not wallets:
        print("Please configure wallets before buying a token.\n")
        return

    token_address = input("Enter the token address: ")
    token_name = input("Enter a name to identify the token: ")
    total_sol = float(input("Enter the total amount of SOL to buy: "))
    await async_buy_token(token_address, token_name, total_sol)


async def sell_token():
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
        await async_sell_token(token_to_sell)
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


async def show_menu():
    ensure_files_exist()
    load_wallets()
    load_tokens()

    while True:
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
            show_banner()
            configure_wallets()
        elif choice == "2":
            show_banner()
            await buy_token()
        elif choice == "3":
            show_banner()
            await sell_token()
        elif choice == "4":
            show_banner()
            show_wallets()
            input("Press Enter to continue...")
        elif choice == "5":
            show_banner()
            watch_logs()
            input("Press Enter to continue...")
        elif choice == "6":
            show_banner()
            reset_wallets_configuration()
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print(Fore.RED + "Invalid option, please try again.\n")
            input("Press Enter to continue...")


asyncio.run(show_menu())
