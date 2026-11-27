const fs = require("node:fs"),
  path = require("node:path"),
  http = require("node:http");
const root = path.resolve(__dirname, "../../dist");
http
  .createServer((req, res) => {
    let target;
    try {
      target = path.resolve(
        root,
        "." + decodeURIComponent(new URL(req.url, "http://localhost").pathname),
      );
    } catch {
      res.writeHead(400).end();
      return;
    }
    if (!target.startsWith(root + path.sep)) {
      res.writeHead(403).end();
      return;
    }
    fs.readFile(target, (error, data) => {
      if (error) {
        res.writeHead(404).end();
        return;
      }
      res.writeHead(200, {
        "Content-Type":
          {
            ".mjs": "text/javascript",
            ".js": "text/javascript",
            ".html": "text/html; charset=utf-8",
            ".json": "application/json",
            ".png": "image/png",
          }[path.extname(target)] || "application/octet-stream",
        "Cache-Control": "no-store",
      });
      res.end(data);
    });
  })
  .listen(4185, "127.0.0.1", () =>
    console.log("http://127.0.0.1:4185/javascript/example.html"),
  );
