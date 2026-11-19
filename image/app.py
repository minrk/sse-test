import json
import time
from pathlib import Path


from tornado.log import app_log
from tornado.iostream import StreamClosedError
from tornado.web import RequestHandler
from tornado import web
import asyncio
import tornado

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class SSEHandler(RequestHandler):
    async def send_event(self, event):
        try:
            self.write(f'data: {json.dumps(event)}\n\n')
            await self.flush()
        except StreamClosedError:
            app_log.warning("Stream closed while handling %s", self.request.uri)
            # raise Finish to halt the handler
            raise web.Finish()

    def initialize(self):
        super().initialize()
        self._finish_future = asyncio.Future()

    def on_finish(self):
        self._finish_future.set_result(None)

    async def keepalive(self, interval):
        """Write empty lines periodically

        to avoid being closed by intermediate proxies
        when there's a large gap between events.
        """
        start = time.monotonic()
        while not self._finish_future.done():
            elapsed = int(time.monotonic() - start)
            app_log.info("sending keepalive %s", elapsed)
            try:
                self.write("\n\n")
                await self.flush()
            except (StreamClosedError, RuntimeError) as e:
                app_log.info("keepalive error: %s", e)
                return

            await asyncio.wait([self._finish_future], timeout=interval)
        app_log.info("finishing keepalive %s", elapsed)

    async def get(self):
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Content-Type', 'text/event-stream')
        delay = int(self.get_argument("delay", "30"))
        keepalive = int(self.get_argument("keepalive", "8"))
        app_log.info(f"Sending events {delay=}, {keepalive=}")
        # start sending keepalive to avoid proxies closing the connection
        asyncio.ensure_future(self.keepalive(keepalive))
        for i in range(100):
            app_log.info("sending %s", i)
            await self.send_event({"i": i})
            await asyncio.sleep(delay)


class IndexHandler(RequestHandler):
    def get(self):
        index_html = Path("index.html").read_text()
        self.write(index_html)

async def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/sse/", IndexHandler),
        (r"/sse/events", SSEHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
