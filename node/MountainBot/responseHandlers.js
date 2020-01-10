const last = require("lodash/last");
const logger = require("node-color-log");
const apiCalls = require("./apiCalls");
const messages = require("./messages");

const getOrder = async text => {
  return text.includes("0")
    ? {
        id: "1234567",
        status: "Found",
        name: "Window"
      }
    : undefined;
};

const getCustomer = async phoneNumber => {
  return phoneNumber.includes("0")
    ? {
        id: "123456",
        name: "Bob Hope"
      }
    : undefined;
};

const promptOrderNumber = async conversation => {
  const lastCustomerMessage = last(conversation.messages.filter(m => m.fromCustomer)).text;

  const order = await getOrder(lastCustomerMessage);
  const customer = await getCustomer("+00009191818");

  if (order && customer) {
    const text = `${messages.orderFound}\n\n${order.name}: ${order.status}`;
    await apiCalls.sendMessage(conversation.id, {text});
    await apiCalls.close(conversation.id);
  } else {
    return "requestHuman";
  }
};

const requestHuman = async conversation => {
  const lastCustomerMessage = last(conversation.messages.filter(m => m.fromCustomer)).text;

  if (lastCustomerMessage.toLowerCase().includes(messages.tryAgain.toLowerCase())) {
    return "promptOrderNumber";
  } else {
    await apiCalls.sendMessage(conversation.id, {text: messages.connectToAgent});
    // Todo: Change to whatever queue they want
    await apiCalls.sendToQueue(conversation.id, {targetQueue: "default"});
  }
};

module.exports = {
  promptOrderNumber,
  requestHuman
};
