const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "../dist/viewer"),
  port = Number(process.env.PORT) || 4173;
const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".json": "application/json",
  ".png": "image/png",
  ".txt": "text/plain",
  ".md": "text/plain",
};
http
  .createServer((request, response) => {
    let pathname;
    try {
      pathname = decodeURIComponent(
        new URL(request.url, "http://localhost").pathname,
      );
    } catch {
      response.writeHead(400).end();
      return;
    }
    const target = path.resolve(
      root,
      "." + (pathname === "/" ? "/index.html" : pathname),
    );
    if (!target.startsWith(root + path.sep)) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(target, (error, bytes) => {
      if (error) {
        response.writeHead(404).end("Not found");
        return;
      }
      response.writeHead(200, {
        "Content-Type":
          types[path.extname(target)] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      response.end(bytes);
    });
  })
  .listen(port, "127.0.0.1", () =>
    console.log(`Model Studio Local: http://127.0.0.1:${port}`),
  );
