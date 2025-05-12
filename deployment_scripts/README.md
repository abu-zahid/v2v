# Deployment Instructions

## Setup Dependencies

```bash
source ./setup_dependencies.sh
```
This will install the dependencies and setup the logs, including `python3-venv` and `nginx`.

## Setup App

```bash
source ./setup_app.sh
```
This will install the app and configure the systemd service and nginx config files.
Update the `.env` file with the correct values.
Remember to attach IAM Role to the EC2 instance with necessary permissions.

Note: This will delete the existing repo and clone a new one.


## Redeploy App

```bash
source ./update_app.sh
```
This will update the app and restart the systemd service.
Update the `.env` file with the correct values if needed.
