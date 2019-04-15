using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using Newtonsoft.Json.Linq;

namespace ConsoleBot
{
    class Program
    { 
        static void Main(string[] args)
        {
            string token = "<hook secret>";
            string site = "https://<site>/";
            string username = "<app id>";
            string password = "<app secret>";


            Console.WriteLine("Hello Bot!");
            MountainBot bot = new MountainBot(site, token, username, password);

            using (HttpListener listener = new HttpListener())
            {
                listener.Prefixes.Add("http://*:8000/dotnetbot/");
                while (true)
                {
                    listener.Start();
                    Console.WriteLine("Listening...");
                    // Note: The GetContext method blocks while waiting for a request. 
                    HttpListenerContext context = listener.GetContext();
                    HttpListenerRequest request = context.Request;

                    var response = bot.HandleRequest(request);

                    context.Response.StatusCode = response.StatusCode;

                    if (response.Message != null)
                    {
                        byte[] buffer = System.Text.Encoding.UTF8.GetBytes(response.Message);
                        // Get a response stream and write the response to it.
                        context.Response.ContentLength64 = buffer.Length;
                        System.IO.Stream output = context.Response.OutputStream;
                        output.Write(buffer, 0, buffer.Length);
                    }
                    context.Response.Close();
                }
            }
        }
    }
}

public class BotResponse
{
    public int StatusCode
    {
        get;
        set;
    }

    public string Message
    {
        get;
        set;
    }
}

public class MountainBot
{
    private readonly string _token;
    private readonly string _site;
    private readonly string _username;
    private readonly string _password;

    private readonly Dictionary<string, Func<JToken, JToken, string>> responseHandlers = new Dictionary<string, Func<JToken, JToken, string>>();
    private readonly Dictionary<string, Action<JToken, JToken>> actionHandlers = new Dictionary<string, Action<JToken, JToken>>();


    public MountainBot(string site, string token, string username, string password) {
        _site = site;
        _token = token;
        _username = username;
        _password = password;

        responseHandlers.Add("send-top-menu", (JToken conversation, JToken botState) => { return TopMenuResponseHandler(conversation, botState); });
        responseHandlers.Add("send-triage", (JToken conversation, JToken botState) => { return TriageResponseHandler(conversation, botState); });

        actionHandlers.Add("send-top-menu", (JToken conversation, JToken botState) => { SendTopMenu(conversation, botState); });
        actionHandlers.Add("send-snow-report", (JToken conversation, JToken botState) => { SendSnowReport(conversation, botState); });
        actionHandlers.Add("send-hours", (JToken conversation, JToken botState) => { SendHours(conversation, botState); });
        actionHandlers.Add("send-ticket-prices", (JToken conversation, JToken botState) => { SendTicketPrices(conversation, botState); });
        actionHandlers.Add("send-triage", (JToken conversation, JToken botState) => { SendTriage(conversation, botState); });
    }

    private async void SendResponse(string url, string payload)
    {
        using (HttpClient client = new HttpClient())
        {
            client.DefaultRequestHeaders.Add(
                "Authorization",
                "Basic " + Convert.ToBase64String(Encoding.ASCII.GetBytes(string.Format("{0}:{1}", _username, _password))));

            if (payload == null)
            {
                payload = string.Empty;
            }
            var content = new StringContent(payload, Encoding.UTF8, "application/json");
            var fullUrl = Path.Join(_site, url);
            await client.PostAsync(fullUrl, content);
        }
    }

    private void QapiPong()
    {
        JToken response = JToken.FromObject(new object());
        response["healthy"] = true;

        SendResponse("api/v1/agent-hooks/pong", response.ToString());
    }

    private void QapiAcknowledge(string conversationId, string request)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/acknowledge", request);
    }

    private void QapiAccept(string conversationId)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/accept", null);
    }

    private void QapiAcceptTransfer(string conversationId)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/accept-transfer", null);
    }

    private void QapiSendMessage(string conversationId, string request)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/send-message", request);
    }

    private void QapiSendToQueue(string conversationId, string request)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/send-to-queue", request);
    }

    private void QapiSendToUser(string conversationId, string request)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/send-to-user", request);
    }

    private void QapiUpdateFields(string conversationId, string request)
    {
        SendResponse($"api/v1/messaging/conversations/{conversationId}/update-fields", request);
    }

    private string GetLastCustomerMessage(JToken conversation)
    {
        string response =null;
        foreach (var message in conversation["messages"].Reverse())
        {
            if (message["fromCustomer"].ToString() == "True")
            {
                response = message["text"].ToString().ToLower();
                break;
            }
        }

        return response;
    }

    private JToken GetTextReply(string reply)
    {
        JToken token = JToken.FromObject(new object());
        token["text"] = reply;

        return token; 
    }

    private void SendTriage(JToken conversation, JToken botState)
    {
        JToken response = JToken.FromObject(new object());
        response["text"] = "What do you need help with?";


        JToken replies = JToken.FromObject(new object());
        replies["replies"] = JToken.FromObject(new List<JToken>
        {
            GetTextReply("Purchase Tickets"),
            GetTextReply("Equipment Rental"),
            GetTextReply("Lodging"),
            GetTextReply("Ski School"),
            GetTextReply("Something Else"),
        });
        response["quiqReply"] = replies;

        QapiSendMessage(conversation["id"].ToString(), response.ToString());
    }

    private void SendTicketPrices(JToken conversation, JToken botState)
    {
        JToken response = JToken.FromObject(new object());
        response["text"] = "Adult full-day tickets are $49 (ages 13-64), $38 for seniors and $26 for children. Half-day tickets are available adults for $38 starting at 1pm";

        QapiSendMessage(conversation["id"].ToString(), response.ToString());
    }

    private void SendHours(JToken conversation, JToken botState)
    {
        JToken response = JToken.FromObject(new object());
        response["text"] = "Lifts are open from 9:30am - 4pm, except for the Mercury lift which closes at 3:30. The ticket office and rental shop are open from 8am-6pm";

        QapiSendMessage(conversation["id"].ToString(), response.ToString());
    }

    private void SendSnowReport(JToken conversation, JToken botState)
    {
        JToken response = JToken.FromObject(new object());
        response["text"] = "We\"ve received 6\" of new snow overnight! Our current summit depth is 82\". Current weather is 22° & calm with a few flakes falling";

        QapiSendMessage(conversation["id"].ToString(), response.ToString());
    }

    private void SendTopMenu(JToken conversation, JToken botState)
    {
        var firstTime = botState["botIntroduced"] == null || botState["botIntroduced"].ToString().ToLower() != "true";
        var text = "What else can I help you with today?";

        if (firstTime)
        {
            botState["botIntroduced"] = true;
            text = "Thanks for contacting Quiqsilver Mountain Resort! My name is Mountain Bot. How can I help you today?";
        }

        JToken sendMessage = JToken.FromObject(new object());
        sendMessage["text"] = text;
        sendMessage["quiqReply"] = JToken.FromObject(new object());
        sendMessage["quiqReply"]["replies"] = JToken.FromObject(new List<JToken>
        {
            GetTextReply("Snow Report"),
            GetTextReply("Hours of Operation"),
            GetTextReply("Ticket Prices"),
            GetTextReply("Live Representative")
        });

        QapiSendMessage(conversation["id"].ToString(), sendMessage.ToString());
    }

    private JToken GetFieldUpdate(string field, string value)
    {
        JToken fieldUpdate = JToken.FromObject(new object());

        fieldUpdate["field"] = field;
        fieldUpdate["value"] = value;

        return fieldUpdate; 
    }

    private string TriageResponseHandler(JToken conversation, JToken botState)
    {
        string response = GetLastCustomerMessage(conversation);

        var responseMap = new Dictionary<string, string>
        {
            {"purchase tickets", "tickets"},
            {"equipment rental", "rental"},
            {"lodging", "lodging"},
            {"ski school", "school"}
        };

        string intent = "other";
        if (responseMap.ContainsKey(response))
        {
            intent = responseMap[response];
        }

        JToken updateFields = JToken.FromObject(new object());
        updateFields["fields"] = JToken.FromObject(new List<JToken>
        {
            GetFieldUpdate("schema.conversation.custom.intent", intent)
        });

        QapiUpdateFields(conversation["id"].ToString(), updateFields.ToString());

        JToken sendToQueue = JToken.FromObject(new object());
        sendToQueue["targetQueue"] = JToken.FromObject("default");

        QapiSendToQueue(conversation["id"].ToString(), sendToQueue.ToString());

        return null;
    }

    private string TopMenuResponseHandler(JToken conversation, JToken botState)
    {
        string response = GetLastCustomerMessage(conversation);

        var actionMap = new Dictionary<string, string>
        {
            {"snow report", "send-snow-report"},
            {"hours of operation", "send-hours"},
            {"ticket prices", "send-ticket-prices"},
            {"live representative", "send-triage"}
        };

        if (actionMap.ContainsKey(response))
        {
            return actionMap[response];
        }
        else 
        {
            QapiSendMessage(conversation["id"].ToString(), GetTextReply("Sorry, I\"m not built to understand that!").ToString());
            return "send-top-menu";
        }
    }

    private void GenerateResponse(JToken conversationState, JToken botState)
    {
        var nextAction = "send-top-menu";

        if (botState["last-action"] != null && responseHandlers.ContainsKey(botState["last-action"].ToString()))
        {
            nextAction = responseHandlers[botState["last-action"].ToString()](conversationState, botState);
        }
    
        if (nextAction != null)
        {
            actionHandlers[nextAction](conversationState, botState);
        }

        botState["last-action"] = nextAction;
    }

    private void ReactToConversationUpdate(JToken conversationState, JToken conversationHints, JToken botState)
    {
        var conversationId = conversationState["id"].ToString();
        var hints = new List<string>();

        foreach (var hint in conversationHints)
        {
            hints.Add(hint["hint"].ToString()); 
        }

        if (hints.Contains("invitation-timer-active"))
        {
            QapiAccept(conversationId);
        }
        else if (hints.Contains("response-timer-active") || hints.Contains("no-message-since-assignment"))
        {
            GenerateResponse(conversationState, botState); 
        }
    }

    private void HandleConversationUpdate(JToken update)
    {
        var conversationState = update["state"];
        var conversationId = update["state"]["id"];
        var conversationHints = update["hints"];
        var conversationAckId = update["ackId"];

        JToken botState = JToken.FromObject(new object());
        if (update["clientState"].Type != JTokenType.Null) 
        {
            botState = update["clientState"];
        }

        ReactToConversationUpdate(conversationState, conversationHints, botState);

        var botStateString = botState.ToString();

        if (string.IsNullOrEmpty(botStateString))
        {
            botStateString = "{}"; 
        }

        JToken ack = JToken.FromObject(new object());
        ack["ackId"] = conversationAckId;
        ack["clientState"] = JToken.FromObject(botState);

        QapiAcknowledge(conversationId.ToString(), ack.ToString());
    }

    public BotResponse HandleRequest(HttpListenerRequest request)
    {
        string[] values = request.Headers.GetValues("X-Centricient-Hook-Token");

        if (values.Length != 1 || values[0] != _token)
        {
            return new BotResponse
            {
                StatusCode = 403, 
                Message = "Invalid verification token Provided"
            };
        }

        using (Stream body = request.InputStream) // here we have data
        {
            using (StreamReader reader = new StreamReader(body, request.ContentEncoding))
            {
                var payload = reader.ReadToEnd();
                Console.WriteLine(payload);

                var resource = JObject.Parse(payload);

                foreach (var update in resource["conversationUpdates"]) {
                    HandleConversationUpdate(update);
                }

                if (resource["ping"] != null)
                {
                    QapiPong();
                }
            }
        }

        return new BotResponse
        {
            StatusCode = 200
        };
    }
}
