A python discord bot that tracks parcels from Greek couriers.

It can function either as a simple parcel tracker by passing 1 or more ids or receive updates when a parcel moves by adding the ids.

Invite link: https://discord.com/api/oauth2/authorize?client_id=926129971037093929&permissions=18432&scope=bot

Or if you want to host it yourself:

## Installation
For any method you will need an api key from discord.

### Local:

1. Clone the repository

```
git clone https://github.com/DanielPikilidis/Greek-Courier-Tracker-Bot.git CourierTracking
cd CourierTracking
```

2. Install required dependencies: 

`pip3 install -r requirements.txt`

3. Start the bot:

`python3 bot.py`

4. A new directory named "data" is now created. Paste your api key in the config.txt file inside that directory.

5. Start the bot again:

`python3 bot.py`

### Docker:

1. Clone the repository:

```
git clone https://github.com/DanielPikilidis/Greek-Courier-Tracker-Bot.git CourierTracking
cd CourierTracking
```

2. Build the Docker image:

`docker build -t courier_tracking .`

3. Create and start the container:

`docker run -d -v $(pwd)/data:/data -v $(pwd)/logs:/logs --name courier_tracking courier_tracking`

4. A new directory named "data" is now created. Paste your api key in the config.txt file inside that directory.

5. Restart the container: 

`docker start courier_tracking`
