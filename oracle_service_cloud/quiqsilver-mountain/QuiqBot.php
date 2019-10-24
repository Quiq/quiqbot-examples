<?php

namespace Custom\Controllers;
use RightNow\Utils\Framework,
    RightNow\Utils\Text,
    RightNow\Libraries\ResponseObject;

class QuiqBot extends \RightNow\Controllers\Base
{
    //This is the constructor for the custom controller. Do not modify anything within
    //this function.
    function __construct()
    {
        parent::__construct();
    }

    public function recieve()
    {
        $appId = 'CHANGE THIS'; //TODO - CHANGE THIS
        $appSecret = 'CHANGE THIS'; //TODO - CHANGE THIS
        $hookSecret = 'CHANGE THIS'; //TODO - CHANGE THIS
        $site = 'CHANGE THIS'; //TODO - CHANGE THIS

        $headers = apache_request_headers();

        if($headers['X-Centricient-Hook-Token'] !== $hookSecret){
            header($_SERVER['SERVER_PROTOCOL'] . ' 403 Unauthorized');
            Framework::writeContentWithLengthAndExit(json_encode(Config::getMessage(END_REQS_BODY_REQUESTS_FORMATTED_MSG)) . str_repeat("\n", 512), 'application/json');
            exit();
        }

        $raw_post = trim(file_get_contents("php://input"));

        $data = json_decode($raw_post, true);
        
        if(!$data)
        {
            header($_SERVER['SERVER_PROTOCOL'] . ' 400 Bad Request');
            // Pad the error message with spaces so IE will actually display it instead of a misleading, but pretty, error message.
            Framework::writeContentWithLengthAndExit(json_encode(Config::getMessage(END_REQS_BODY_REQUESTS_FORMATTED_MSG)) . str_repeat("\n", 512), 'application/json');
        }

        if($data['ping'])
            $this->qApiPong($site, $appId, $appSecret);


        foreach($data['conversationUpdates'] as $update) {
            $this->conversationUpdateHandler($site, $appId, $appSecret, $update);
        }
    }

    private function conversationUpdateHandler($site, $appId, $appSecret, $update) {
        $conversationState = $update['state'];
        $conversationId = $update['state']['id'];
        $conversationHints = $update['hints'];
        $conversationAckId = $update['ackId'];
        $botState = $update['clientState'];

        try {
            $this->reactToConversationUpdate($site, $appId, $appSecret, $conversationState, $conversationHints, $botState);
        } catch(Exception $e) {
            // do nothing
        }

        $request = json_encode(array('ackId' => $conversationAckId, 'clientState' => $botState));
        $this->qApiAcknowledge($site, $appId, $appSecret, $conversationId, $request);
    }
    
    private function reactToConversationUpdate($site, $appId, $appSecret, $conversation, $conversationHints, &$botState) {
        $hints = array();
        foreach($conversationHints as $hint) {
            array_push($hints, $hint['hint']);
        }

        $conversationId = $conversation['id'];

        if (in_array('invitation-timer-active', $hints)) {
            $this->qApiAccept($site, $appId, $appSecret, $conversationId);
        } elseif (in_array('response-timer-active', $hints) or in_array('no-message-since-assignment', $hints)) {
            $this->generateResponse($site, $appId, $appSecret, $conversation, $botState);
        }
    }

    private function generateResponse($site, $appId, $appSecret, $conversation, &$botState) {
        if ($botState['last-action'] === 'send-top-menu') {
            $this->topMenuResponseHandler($site, $appId, $appSecret, $conversation, $botState);
        } else {
            $this->sendTopMenu($site, $appId, $appSecret, $conversation, $botState);
        }
    }
 
    private function sendTopMenu($site, $appId, $appSecret, $conversation, &$botState) {
        if (in_array('introduced', $botState)) {
            $firstTime = !$botState['introduced'];
        } else {
            $firstTime = true;
        }

        $replies = array('replies' => array(
            array('text' => 'Snow Report'), 
            array('text' => 'Hours of Operation'), 
            array('text' => 'Ticket Prices'), 
            array('text' => 'Live Representative')));
        if ($firstTime) {
            $text = 'Thanks for contacting Quiqsilver Mountain Resort! My name is Mountain Bot. How can I help you today?';
            $botState['introduced'] = true;
        } else {
            $text = 'What else can I help you with today?';
        }

        $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => $text, 'quiqReply' => $replies)));
        $botState['last-action'] = 'send-top-menu';
    }

    private function topMenuResponseHandler($site, $appId, $appSecret, $conversation, &$botState) {
        $customerMessages = array_filter($conversation['messages'], function($message){
            return $message['fromCustomer'];
        });

        $response = strtolower(end($customerMessages)['text']);

        if ($response === 'snow report') {
            $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => 'We\'ve received 6" of new snow overnight! Our current summit depth is 82". Current weather is 22° & calm with a few flakes falling!')));
            $this->sendTopMenu($site, $appId, $appSecret, $conversation, $botState);
        } elseif ($response === 'hours of operation') {
            $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => 'Lifts are open from 9:30am - 4pm, except for the Mercury lift which closes at 3:30. The ticket office and rental shop are open from 8am-6pm')));
            $this->sendTopMenu($site, $appId, $appSecret, $conversation, $botState);
        } elseif ($response === 'ticket prices') {
            $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => 'Adult full-day tickets are $49 (ages 13-64), $38 for seniors and $26 for children. Half-day tickets are available adults for $38 starting at 1pm')));
            $this->sendTopMenu($site, $appId, $appSecret, $conversation, $botState);
        } elseif ($response === 'live representative') {
            $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => 'OK, sending you to a live representative!')));
            $this->qApiSendToQueue($site, $appId, $appSecret, $conversation['id'], json_encode(array('targetQueue' => 'default')));
        } else {
            $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => 'Sorry, I\'m not built to understand that!')));
   
        }
    }

    private function qApiPong($site, $appId, $appSecret) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/agent-hooks/pong", json_encode(array("healthy" => true)));
    }

    private function qApiAcknowledge($site, $appId, $appSecret, $conversationId, $request) {
        $this->doCurlPost($appId, $appSecret,"$site/api/v1/messaging/conversations/$conversationId/acknowledge", $request);
    }

    private function qApiAccept($site, $appId, $appSecret, $conversationId) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/accept", "");
    }

    private function qApiAcceptTransfer($site, $appId, $appSecret, $conversationId) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/accept-transfer", '');
    }

    private function qApiSendMessage($site, $appId, $appSecret, $conversationId, $request) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/send-message", $request);
    }

    private function qApiSendToQueue($site, $appId, $appSecret, $conversationId, $request) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/send-to-queue", $request);
    }

    private function qApiSendToUser($site, $appId, $appSecret, $conversationId, $request) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/send-to-user", $request);
    }

    private function qApiUpdateFields($site, $appId, $appSecret, $conversationId, $request) {
        $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/update-fields", $request);
    }

    private function doCurlPost($appId, $appSecret, $url, $payload) {
       load_curl();

       $ch = curl_init($url);
       curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
       curl_setopt($ch, CURLOPT_USERPWD, $appId . ":" . $appSecret);
       curl_setopt($ch, CURLOPT_TIMEOUT, 30);
       curl_setopt($ch, CURLOPT_POST, 1);
       curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
       curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
       curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
       curl_setopt($ch, CURLOPT_URL, $url);
       curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
       $res = curl_exec($ch);

       curl_close($ch);
    }
}

