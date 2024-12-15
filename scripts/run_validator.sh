#!/bin/bash

python3 -m venv venv_validator
source venv_validator/bin/activate
pip install -r requirements.txt

cp -r env venv_validator/

export PYTHONPATH=$(pwd)
echo "PYTHONPATH is set to $PYTHONPATH"
NETWORK_TYPE=${1:-mainnet}
echo "NETWORK_TYPE is set to $NETWORK_TYPE"
cd src
python3 subnet/cli.py $NETWORK_TYPE

deactivate