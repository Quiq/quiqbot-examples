const apiCalls = require("./apiCalls");
const messages = require("./messages");

const promptOrderNumber = async (conversation, botState) => {
  let text = "";
  if (!botState.introduced) {
    text = messages.promptOrderNumber;
    botState.introduced = true;
  } else {
    text = messages.promptOrderAgain;
  }

  await apiCalls.sendMessage(conversation.id, {text});
};

const requestHuman = async (conversation, botState) => {
  await apiCalls.sendMessage(conversation.id, {
    text: messages.orderNotFound,
    quiqReply: {
      replies: [{text: messages.yes}, {text: messages.tryAgain}]
    }
  });
};

module.exports = {
  promptOrderNumber,
  requestHuman
};
