
package com.goquiq.bots;

import com.mashape.unirest.http.HttpResponse;
import com.mashape.unirest.http.Unirest;
import com.mashape.unirest.request.HttpRequest;
import fi.iki.elonen.NanoHTTPD;
import fi.iki.elonen.util.ServerRunner;
import org.json.JSONArray;
import org.json.JSONObject;

import java.util.*;

public class RepeaterBot extends NanoHTTPD {

    public static void main(String[] args) {
        ServerRunner.run(RepeaterBot.class);
    }

    private static final String HOOK_SECRET_HEADER = "x-centricient-hook-token";

    private String appId;
    private String appSecret;
    private String webhookSecret;
    private String site;

    public RepeaterBot() {
        super(8099);

        this.appId         = System.getenv("appId");
        this.appSecret     = System.getenv("appSecret");;
        this.webhookSecret = System.getenv("hookSecret");
        this.site          = System.getenv("site");

        if (appId == null || appSecret == null || webhookSecret == null || site == null) {
            System.out.println("Insure that the following environment variables are set: appId, appSecret, hookSecret, site");
            System.exit(-1);
        }
    }

    @Override public Response serve(IHTTPSession session) {

        boolean validRequest = session.getMethod() == Method.POST &&
            session.getUri().equals("/") &&
            session.getHeaders().get("content-type").equals("application/json");

        boolean secureRequest = session.getHeaders().containsKey(HOOK_SECRET_HEADER) &&
            session.getHeaders().get(HOOK_SECRET_HEADER).equals(this.webhookSecret);

        if (validRequest) {
            if (secureRequest) {
                try {
                    Scanner s = new Scanner(session.getInputStream()).useDelimiter("\\A");
                    String body = s.hasNext() ? s.next() : "";
                    JSONObject event = new JSONObject(body);

                    handleAgentHookEvent(event);

                    return newFixedLengthResponse(Response.Status.NO_CONTENT, null, null);

                } catch (Exception e) {
                    System.out.println(e.getMessage());
                    e.printStackTrace(System.out);

                    return newFixedLengthResponse(Response.Status.INTERNAL_ERROR, null, null);
                }
            } else {
                return newFixedLengthResponse(Response.Status.UNAUTHORIZED, null, null);
            }
        } else {
            return newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "Not found");
        }
    }

    private void handleAgentHookEvent(JSONObject event) throws Exception {
        if (event.has("ping") && event.getBoolean("ping")) {
            pong();
        }

        if (event.has("conversationUpdates")) {
            JSONArray updates = event.getJSONArray("conversationUpdates");


            for (int i = 0; i < updates.length(); i++) {
                JSONObject update = updates.getJSONObject(i);

                System.out.println("Received update: " + update);

                String conversationId = update.getJSONObject("state").getString("id");
                int stateId = update.getInt("stateId");
                try {
                    handleConversationUpdate(update);
                } catch (Exception e) {
                    System.out.println(e.getMessage());
                    e.printStackTrace(System.out);
                } finally {
                    // We want to call acknowledge for each state ID no matter what so
                    // that Quiq continues to send us more state updates
                    acknowledge(conversationId, stateId);
                }
            }
        }
    }

    private void handleConversationUpdate(JSONObject update) throws Exception {
        JSONObject conversation = update.getJSONObject("state");
        String conversationId = conversation.getString("id");

        Set<String> hints = extractHints(update);

        if (hints.contains("invitation-timer-active")) {
            accept(conversationId);
        } else if (hints.contains("response-timer-active") || hints.contains("no-message-since-assignment")) {
            respondToCustomer(conversation);
        }
    }

    private void respondToCustomer(JSONObject conversation) throws Exception {
        String conversationId = conversation.getString("id");
        Optional<JSONObject> lastCustomerMessage = getMostRecentCustomerMessage(conversation);

        if (lastCustomerMessage.isPresent()) {
            String text = lastCustomerMessage.get().getString("text");
            text = (text == null) ? "" : text.toLowerCase();

            if (text.contains("requeue")) {
                sendToQueue(conversationId, "default");
            } else if (text.contains("close")) {
                close(conversationId);
            } else if (text.contains("eggs")) {
                JSONObject payload = new JSONObject();
                payload.put("text", "How do you like your eggs?");

                List<JSONObject> replies = new ArrayList<>();
                replies.add(new JSONObject().put("text", "Over-Easy"));
                replies.add(new JSONObject().put("text", "Over-Medium"));
                replies.add(new JSONObject().put("text", "Over-Hard"));
                replies.add(new JSONObject().put("text", "Scrambled"));

                payload.put("quiqReply", new JSONObject().put("quiqReply", new JSONObject()).put("replies", new JSONArray(replies)));

                sendMessage(conversationId, payload);
            } else if (text.length() > 0) {
                sendTextMessage(conversationId, "You said '" + text + "'");
            } else {
                sendTextMessage(conversationId, "Interesting!");
            }
        } else {
            sendTextMessage(conversationId, "Hello there!");
        }
    }

    private Optional<JSONObject> getMostRecentCustomerMessage(JSONObject conversation) {
        JSONArray messagesArr = conversation.getJSONArray("messages");
        List<JSONObject> messages = new ArrayList<>();

        for (int i = 0; i < messagesArr.length(); i++)
            messages.add(0, messagesArr.getJSONObject(i));

        return messages.stream().filter(m -> m.getBoolean("fromCustomer")).findFirst();
    }

    private Set<String> extractHints(JSONObject update) {
        JSONArray hintObjects = update.getJSONArray("hints");
        Set<String> hints = new HashSet<>();

        for (int i = 0; i < hintObjects.length(); i++) {
            hints.add(hintObjects.getJSONObject(i).getString("hint"));
        }

        return hints;
    }

    // --------------------- Quiq REST API Wrappers -------------------------

    private void pong() throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("healthy", true);

        invokeQuiqApi("api/v1/agent-hooks/pong", payload);
    }

    private void acknowledge(String conversationId, int stateId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("stateId", stateId);

        invokeQuiqApi("api/v1/messaging/conversations/" + conversationId + "/acknowledge", payload);
    }

    private void accept(String conversationId) throws Exception {
        invokeQuiqApi("api/v1/messaging/conversations/" + conversationId + "/accept", null);
    }

    private void sendTextMessage(String conversationId, String text) throws Exception {
       JSONObject payload = new JSONObject();
       payload.put("text", text);
       sendMessage(conversationId, payload);
    }

    private void sendMessage(String conversationId, JSONObject message) throws Exception {
        invokeQuiqApi("api/v1/messaging/conversations/" + conversationId + "/send-message", message);
    }

    private void sendToQueue(String conversationId, String queueId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("targetQueue", queueId);
        invokeQuiqApi("api/v1/messaging/conversations/" + conversationId + "/send-to-queue", payload);
    }

    private void close(String conversationId) throws Exception {
        invokeQuiqApi("api/v1/messaging/conversations/" + conversationId + "/close", null);
    }

    private void invokeQuiqApi(String api, JSONObject payload) throws Exception {

        System.out.println(this.site + "/" + api + ": " + payload);

        HttpResponse<String> response = null;

        if (payload != null) {
            response = Unirest.post(this.site + "/" + api)
                .header("accept", "application/json")
                .header("Content-Type", "application/json")
                .basicAuth(appId, appSecret)
                .body(payload)
                .asString();
        } else {
            response = Unirest.post(this.site + "/" + api)
                .header("accept", "application/json")
                .header("Content-Type", "application/json")
                .basicAuth(appId, appSecret)
                .asString();
        }

        System.out.println("Returned " + response.getStatus());
    }
}
