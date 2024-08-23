# Solana Rug Pull Script

This script allows you to configure multiple Solana wallets and perform token purchases and sales using the Pump.fun API. Additionally, the configured wallets and purchased tokens are saved in files for later use, and all operations performed are logged in a log file.

## Requisitos

1. Python 3.7 or higher
2. Pip (Python package manager)

## Virtual Environment Setup (venv)

It is recommended to create a virtual environment (venv) to avoid conflicts between the dependencies of this project and other Python applications on your system.

1. Create the virtual environment

```bash
python3 -m venv venv
```

2. Activate the virtual environment

```bash
source venv/bin/activate
```

3. Install the dependencies
   Ensure that the requirements.txt file is in the same directory as the script.

```bash
pip install -r requirements.txt
```

## Running the Script

Once you have set up and activated the virtual environment and installed the dependencies, you can run the script:

```bash
make start
```

## Script Usage

The script will guide you through a menu where you can:

1. Configure Wallets: Set up one or more Solana wallets, assigning a percentage of the total purchase to each.
2. Buy a Meme Coin: Purchase tokens using the configured wallets.
3. Sell Purchased Token: Select and sell a previously purchased token using the configured wallets.
4. View Configured Wallets: Display a list of the configured wallets, with their assigned percentage and total tokens purchased.
5. View the logs
6. Reset wallets configuration
7. Exit: Exit the script.

## Note

1. Persistence: The configured wallets and purchased tokens are saved in text files (wallets.txt and tokens.txt) for use in future sessions.
2. Operation Log: All performed operations are logged in a log file (wallet_operations.log).

## Deactivating the Virtual Environment

Deactivating the Virtual Environment

```bash
    deactivate
```

You are now ready to use the script and perform rug pulls on the Solana network!
