# Crypto Influence Insights - The Miner Setup

## Table of Contents
- [Setup](#setup)
  - [Influence Insights Indexer Setup](#influence-insights-indexer-setup)
  - [Miner Setup](#miner-setup)
    - [Prerequisites](#prerequisites)
    - [Clone repository](#clone-repository)
    - [Env configutaion](#env-configuration)
    - [Miner wallet creation](#miner-wallet-creation)
    - [Running the miner](#running-the-miner-and-monitoring)
    - [Run multiple miners](#run-multiple-miners)

## Setup

### Influence Insights Indexer Setup

Miner requires an indexer to be able to fetch the twitter data on a particular token. The indexer should be running and accessible to the miner.
At the moment we deliver an open source version of the Influence Insights Indexer for one token.

More info about the indexer, its code, and setup instructions can be found at:
[Influence Insights Indexer](https://github.com/blockchain-insights/crypto-influence-insights-indexer)
  
### Miner Setup

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
sudo apt install python3-pip python3-venv python3-dev git build-essential libssl-dev libffi-dev

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
git clone https://github.com/blockchain-insights/crypto-influence-insights.git miner1
```

#### Env configuration

Navigate to miner directory and copy the `.env.miner.example` file to `.env.miner.mainnet`.
```shell
cd miner1
cp ./env/.env.miner.example ./env/.env.miner.mainnet
```

Now edit the `.env.miner.mainnet` file to set the appropriate configurations:
```shell
NET_UID=22
MINER_KEY=miner1
MINER_NAME=miner1
TOKEN=TAO
PORT=9962

POSTGRES_PASSWORD={your-password}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:{your-password}@localhost:5432/indexer_db

```
 
#### Miner wallet creation

```shell
comx key create miner1
comx key list
# transfer COMAI to your miner wallet for registration (aprox 10 COMAI are needed)
comx module register miner1 miner1 22 --ip {put-here-ip-address-of-your-miner-server} --port 9962
```

If something is wrongly created, you can deregister the miner and register it again (with new settings):
```shell
comx module deregister miner1 22
.. register again...
```

### Running the miner and monitoring

```shell
# use pm2 to run the miner
pm2 start ./scripts/run_miner.sh --name miner1
pm2 save
```


### Run Multiple Miners

To run multiple miners on a single machine, you can create additional `.env.miner.mainnet` files, set unique ports and registered keys in them, then pass it to pm2 like this for example:

```shell
pm2 start ./scripts/run_miner.sh --name miner2 --env .env.miner2.mainnet
pm2 save
# Repeat for minerN
```