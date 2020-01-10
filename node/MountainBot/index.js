const express = require("express");
const morgan = require("morgan");
const {pong} = require("./apiCalls");
const bodyParser = require("body-parser");
const app = express();
const handleConversationEvent = require("./conversationEvents");

(async () => {
  var jsonParser = bodyParser.json();

  app.use(morgan("combined"));
  app.post("/handler", jsonParser, async (req, res) => {
    const event = req.body;

    if (req.headers["x-centricient-hook-token"] !== process.env.hookSecret) {
      res.statusMessage = "Invalid verification token provided";
      return res.status(400).end();
    }

    if (event.ping) await pong();
    else await handleConversationEvent(event.conversationUpdates);

    return res.status(204).end();
  });

  app.listen(3000, function() {
    console.log("Listening on port 3000");
  });
})();
