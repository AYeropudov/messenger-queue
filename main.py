import argparse
from aiohttp import web
import aioredis
from handlers.ws import WebSocketHandler
from aioredis.pubsub import Receiver
from aioredis.abc import AbcChannel
import asyncio
import settings


async def setup_sub_pub(app):
    app['sub'] = await aioredis.create_redis(settings.REDIS_CON, db=1, loop=app.loop)
    await app['sub'].subscribe(app['receiver'].channel("room:public"))


async def reader(app):
    try:
        await setup_sub_pub(app)
        async for channel, msg in app['receiver'].iter():
            assert isinstance(channel, AbcChannel)
            if app.ws_list[channel.name.decode('utf-8')]:
                for ws in app.ws_list[channel.name.decode('utf-8')]:
                    await ws.send_str('from queue {}'.format(msg))
        await app['sub'].punsubscribe('room')
        print('Unsubscribe from channels')
        app['receiver'].stop()
    except asyncio.CancelledError:
        print('test')
        await app['sub'].punsubscribe('room')
        app['receiver'].stop()


def setup_routes(app):
    app.router.add_get('/{room}', WebSocketHandler)


async def start_background_tasks(app):
    app['redis_listener'] = app.loop.create_task(reader(app))

async def cleanup_background_tasks(app):
    app['redis_listener'].cancel()
    await app['redis_listener']

app = web.Application()
app['receiver'] = Receiver(loop=app.loop)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)
setup_routes(app)
app.ws_list=dict()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Single server node")
    parser.add_argument('--port')
    args = parser.parse_args()
    _port = args.port or 9100
    web.run_app(app=app, port=_port)
