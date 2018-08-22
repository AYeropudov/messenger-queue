import settings
import aioredis
from aiohttp import web
from aiohttp import WSMsgType


class WebSocketHandler(web.View):
    def __init__(self, request):
        self.channel = None
        self.redis_pub_conn = None
        super().__init__(request)

    async def log(self, msg):
        print(msg)

    async def subscribe_channel(self):
        _app = self.request.app
        await _app['sub'].subscribe(_app['receiver'].channel(self.channel))

    async def un_subscribe_channel(self, channel):
        _app = self.request.app
        await _app['sub'].unsubscribe(channel)

    async def get(self):
        _room_id = int(self.request.match_info['room'])
        self.redis_pub_conn = await aioredis.create_redis_pool(settings.REDIS_CON, db=1)
        _app = self.request.app
        await self.log('init connection')
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)
        await self.log('Connected to server')
        self.channel = "room:{}".format(_room_id)
        try:
            _app.ws_list[self.channel].append(ws)
        except KeyError:
            _app.ws_list[self.channel] = [ws]

        await self.subscribe_channel()

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    text = msg.data.strip()
                    if text.startswith('/'):
                        await self.command(text)
                    else:
                        await self.process_message(msg)
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())

        await self.log('websocket connection closed')
        _app.ws_list[self.channel].remove(ws)

        await self.un_subscribe_channel(channel=self.channel)
        await self.log('Channel close')
        return ws

    async def command(self, cmd):
        if cmd.startswith('/list'):
            await self.log(self.request.app.registered_servers)
        else:
            await self.log('Нет такой команды')

    async def process_message(self, msg):
        await self.log(msg)
        with await self.redis_pub_conn as publisher:
            await self.log('try to publish')
            await publisher.publish_json(self.channel, msg.json())
