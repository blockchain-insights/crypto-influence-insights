# Crypto Influence Insights - The validator Setup

## Table of Contents
- [Setup](#setup)
  - [Validator Setup](#validator-setup)
    - [Prerequisites](#prerequisites)
    - [Clone Repository](#clone-repository)
    - [Env configuration](#env-configuration)
    - [Validator wallet creation](#validator-wallet-creation)
    - [Running the validator and monitoring](#running-the-validator-and-monitoring)
    - [Running the validator api](#running-the-validator-api)
    - [Running the miner leaderboard](#running-the-miner-leaderboard)

## Setup

### Validator Setup

#### Prerequisites

- Ubuntu 22.04 LTS (or similar)
- Python 3.10+
- Node.js 18.x+
- PM2
- Communex
- Git

```shell
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv python3-dev git build-essential libssl-dev libffi-dev ca-certificates curl

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

pip install communex

curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install pm2 -g
pm2 startup
```

#### Clone Repository

```shell
git clone https://github.com/blockchain-insights/crypto-influence-insights.git ~/validator1
```

#### Env configuration

Navigate to validator directory and copy the `.env.validator.example` file to `.env.validator.mainnet`.
```shell
cd ~/validator1
cp ./env/.env.validator.example ./env/.env.validator.mainnet
```

Now edit the `.env.validator.mainnet` file to set the appropriate configurations.
```shell
VALIDATOR_KEY=<your_validator_comx_key>
ITERATION_INTERVAL=50
MAX_ALLOWED_WEIGHTS=64
NET_UID=22

GRAPH_DB_USER=mario
GRAPH_DB_PASSWORD=securepassword123
GRAPH_DB_URL="bolt://localhost:7687"

POSTGRES_DB=validator1
POSTGRES_USER=postgres
POSTGRES_PASSWORD={your-password}

DATABASE_URL=postgresql+asyncpg://postgres:{your-password}@localhost:5432/validator1

API_RATE_LIMIT=1000
REDIS_URL=redis://localhost:6379/0

SNAPSHOT_TIMEOUT=60

PORT=9900
WORKERS=1

TWITTER_BEARER_TOKENS=<you_twitter_API_bearer_tokens_separated_with_a_comma>
ENABLE_GATEWAY=True
```

#### Validator wallet creation

```shell
comx key create validator1
comx key list
# transfer COMAI to your validator wallet for registration (aprox 10 COMAI are needed)
comx module register validator1 validator1 22 --port 9900
# stake COMAI to your validator wallet
```

## Validator Configuration

### ENABLE_GATEWAY Flag

The `ENABLE_GATEWAY` flag defines how the validator operates:

- **`ENABLE_GATEWAY=True`**: This indicates the validator is running with a gateway. In this mode, the validator requires a Memgraph instance (running locally or in a separate instance). The validator will expose an API and write validation data to Memgraph.

- **`ENABLE_GATEWAY=False`**: In this mode, the validator operates without a gateway. It validates JSON datasets and scores miners but does not interact with Memgraph or expose an API.

## Starting the Infrastructure for the Validator

To start the required infrastructure for the validator:

1. Navigate to the `ops` directory:
   ```shell
   cd ./ops/validator
   ```

2. Copy the appropriate environment configuration file:
   ```shell
   cp ./env/.env.validator.mainnet ./ops/validator/.env
   ```

3. Adjust file permissions:
   ```shell
   chmod 644 .env
   ```

4. Start the infrastructure using Docker Compose:

For configurations without a gateway (just validation):
   ```shell
   docker compose -f docker-compose.yaml up -d
   ```
For configurations with a gateway:
   ```shell
   docker compose -f docker-compose.gateway.yaml up -d
   ```

## Starting the Validator

```shell
# use pm2 to run the validator
cd ~/validator1
pm2 start ./scripts/run_validator.sh --name validator1
pm2 save
```

### Running the validator api

```shell
cd ~/validator1
pm2 start ./scripts/run_gateway.sh --name gateway
pm2 save
```
