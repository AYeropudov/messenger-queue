import settings
import aioredis
from aiohttp import web
from aiohttp import WSMsgType


class WebSocketHandler(web.View):
    def __init__(self, request):
        super().__init__(request)

    async def log(self, msg):
        print(msg)

    async def subscribe_channel(self, channel):
        _app = self.request.app
        await _app['sub'].subscribe(_app['mpsc'].channel(channel))

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
        _channel = "room:{}".format(_room_id)
        try:
            _app.ws_list[_channel].append(ws)
        except KeyError:
            _app.ws_list[_channel] = [ws]
        await self.subscribe_channel(_channel)
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    text = msg.data.strip()
                    if text.startswith('/'):
                        await self.command(text)
                    else:
                        await self.log(msg)
                        with await self.redis_pub_conn as publisher:
                            await self.log('try to publish')
                            await publisher.publish_json("room:{}".format(_room_id), msg.json())
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                      ws.exception())

        await self.log('websocket connection closed')
        _app.ws_list[_channel].remove(ws)

        await self.un_subscribe_channel(channel=_channel)
        await self.log('Channel close')
        return ws

    async def command(self, cmd):
        if cmd.startswith('/list'):
            await self.log(self.request.app.registered_servers)
        else:
            await self.log('Нет такой команды')