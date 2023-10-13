A python discord bot that tracks parcels from Greek couriers.

It can function either as a simple parcel tracker by passing 1 or more ids or receive updates when a parcel moves by adding the ids.
It is getting the data from this API: https://courier-api.danielpikilidis.com/

Currently supported couriers:
  - ACS
  - CourierCenter
  - EasyMail
  - ELTA Courier
  - Skroutz Last Mile
  - Speedex Courier
  - Geniki Taxydromiki
  - Delatolas Courier
  - IKEA


Invite Link: https://discord.com/api/oauth2/authorize?client_id=947975790409154620&permissions=18432&scope=bot.

Note: It is self hosted so expect some downtime

## Installation
You can also host it yourself:


1) Get an API key from discord (https://discord.com/developers/docs/intro) (free)
2) Clone the repository or download the docker-compose.yaml
3) Modify the envs and volumes in docker-compose.yaml however you like.
4) Start the container:
```
docker compose up -d
```
