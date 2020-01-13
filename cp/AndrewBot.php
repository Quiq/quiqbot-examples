<?php

namespace Custom\Controllers;
// use RightNow\Utils\Framework,
//     RightNow\Utils\Text,
//     RightNow\Libraries\ResponseObject;

class QuiqBot //extends \RightNow\Controllers\Base
{
  const messages = array(
    'promptOrderNumber' => "Hello! Thanks for contacting Pella. I'm the Order Bot. Could I please get your order number?",
    'promptOrderAgain' => "Let's try that again.  Could I please get your order number?",
    'orderNotFound' =>
      "Hmm, I wasn't able to find an order matching that number.  Would you like me to connect you to a live agent?",
    'orderFound' => 'Thanks! I found your order, here you go.',
    'connectToAgent' => "Let's get you connected to an agent.  One moment.",
    'yes' => 'Yes',
    'tryAgain' => "No, Let's Try Again"
  );
  
  //This is the constructor for the custom controller. Do not modify anything within
  //this function.
  function __construct()
  {
    $this->recieve();
    // parent::__construct();
  }

  private function log($message, $title = 'LOG')
  {
    error_log(print_r('-------------' . $title . '------------', true));
    error_log(print_r($message, true));
    error_log(print_r('-------------' . $title . '------------', true));
  }

  public function recieve()
  {
    $appId = 'de649dd7-074c-4de1-9391-9b25ac7fb5c7';
    $appSecret =
      'eyJhbGciOiJIUzI1NiIsImtpZCI6ImJhc2ljOjAifQ.eyJ0ZW5hbnQiOiJhbmRyZXciLCJzdWIiOiIxNjIwMTAifQ.bSvfLe_xf2AmbsV2F2JG8wqDwTvlGJPyM339qyoLo-E';
    $hookSecret = '3d227436-e7f3-4705-8390-3b97edca2cbb';
    $site = 'https://andrew.goquiq.com';

    $headers = apache_request_headers();

    if ($headers['X-Centricient-Hook-Token'] !== $hookSecret) {
      header($_SERVER['SERVER_PROTOCOL'] . ' 403 Unauthorized');
      // Framework::writeContentWithLengthAndExit(json_encode(Config::getMessage(END_REQS_BODY_REQUESTS_FORMATTED_MSG)) . str_repeat("\n", 512), 'application/json');
      exit();
    }

    $raw_post = trim(file_get_contents('php://input'));

    $data = json_decode($raw_post, true);

    if (!$data) {
      header($_SERVER['SERVER_PROTOCOL'] . ' 400 Bad Request');
      // Pad the error message with spaces so IE will actually display it instead of a misleading, but pretty, error message.
      // Framework::writeContentWithLengthAndExit(json_encode(Config::getMessage(END_REQS_BODY_REQUESTS_FORMATTED_MSG)) . str_repeat("\n", 512), 'application/json');
    }

    if ($data['ping']) {
      $this->qApiPong($site, $appId, $appSecret);
    }

    foreach ($data['conversationUpdates'] as $update) {
      $this->conversationUpdateHandler($site, $appId, $appSecret, $update);
    }
  }

  private function conversationUpdateHandler($site, $appId, $appSecret, $update)
  {
    $conversationState = $update['state'];
    $conversationId = $update['state']['id'];
    $conversationHints = $update['hints'];
    $conversationAckId = $update['ackId'];
    $botState = $update['clientState'];

    try {
      $this->reactToConversationUpdate($site, $appId, $appSecret, $conversationState, $conversationHints, $botState);
    } catch (Exception $e) {
      // do nothing
    }

    $request = json_encode(array('ackId' => $conversationAckId, 'clientState' => $botState));
    $this->qApiAcknowledge($site, $appId, $appSecret, $conversationId, $request);
  }

  private function reactToConversationUpdate($site, $appId, $appSecret, $conversation, $conversationHints, &$botState)
  {
    $hints = array();
    foreach ($conversationHints as $hint) {
      array_push($hints, $hint['hint']);
    }

    $conversationId = $conversation['id'];

    if (in_array('invitation-timer-active', $hints)) {
      $this->qApiAccept($site, $appId, $appSecret, $conversationId);
    } elseif (in_array('response-timer-active', $hints) or in_array('no-message-since-assignment', $hints)) {
      $this->generateResponse($site, $appId, $appSecret, $conversation, $botState);
    }
  }

  private function qApiPong($site, $appId, $appSecret)
  {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/agent-hooks/pong", json_encode(array('healthy' => true)));
  }

  private function qApiAcknowledge($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/acknowledge", $request);
  }

  private function qApiAccept($site, $appId, $appSecret, $conversationId) {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/accept", '');
  }

  private function qApiClose($site, $appId, $appSecret, $conversationId)
  {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/close", '');
  }

  private function qApiSendMessage($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost(
      $appId,
      $appSecret,
      "$site/api/v1/messaging/conversations/$conversationId/send-message",
      $request
    );
  }

  private function qApiSendToQueue($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost(
      $appId,
      $appSecret,
      "$site/api/v1/messaging/conversations/$conversationId/send-to-queue",
      $request
    );
  }

  private function qApiUpdateFields($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost(
      $appId,
      $appSecret,
      "$site/api/v1/messaging/conversations/$conversationId/update-fields",
      $request
    );
  }

  // TODO: UPDATE ME
  private function fetchOrder($site, $appId, $appSecret, $conversationId, $request)
  {
    return null;
    return array(
      'id' => '123456',
      'status' => 'Found',
      'name' => 'Fancy Window'
    );
  }

  // TODO: UPDATE ME
  private function fetchCustomer($site, $appId, $appSecret, $conversationId, $request)
  {
    return array(
      'id' => '123456',
      'name' => 'Bob Hope'
    );
  }

  private function getOrderNumber($text)
  {
    // TODO: Validate and get order number out of it
    return $text;
  }

  private function getLastMessage($conversation)
  {
    $customerMessages = array_filter($conversation['messages'], function ($message) {
      return $message['fromCustomer'];
    });

    return strtolower(end($customerMessages)['text']);
  }

  private function doCurlPost($appId, $appSecret, $url, $payload)
  {
    //    load_curl();

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
    curl_setopt($ch, CURLOPT_USERPWD, $appId . ':' . $appSecret);
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

  private function generateResponse($site, $appId, $appSecret, $conversation, &$botState)
  {
    if ($botState['last-action'] === 'prompt-order-number') {
      $this->promptOrderNumberResponseHandler($site, $appId, $appSecret, $conversation, $botState);
    } elseif ($botState['last-action'] === 'request-human') {
      $this->requestHumanResponseHandler($site, $appId, $appSecret, $conversation, $botState);
    } else {
      $this->promptOrderNumber($site, $appId, $appSecret, $conversation, $botState);
    }
  }

  // Prompt Order Action
  private function promptOrderNumber($site, $appId, $appSecret, $conversation, &$botState)
  {
    if (in_array('introduced', $botState)) {
      $firstTime = !$botState['introduced'];
    } else {
      $firstTime = true;
    }

    if ($firstTime) {
      $text = self::messages['promptOrderNumber'];
      $botState['introduced'] = true;
    } else {
      $text = self::messages['promptOrderAgain'];
    }

    $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => $text)));
    $botState['last-action'] = 'prompt-order-number';
  }

  // Prompt Order Response Handler
  private function promptOrderNumberResponseHandler($site, $appId, $appSecret, $conversation, &$botState)
  {
    $phoneNumber = '+00001929192'; // TODO: UPDATE ME;
    $order = $this->fetchOrder(
      $site,
      $appId,
      $appSecret,
      $conversation,
      $this->getOrderNumber($this->getLastMessage($conversation))
    );
    $customer = $this->fetchCustomer($site, $appId, $appSecret, $conversation, $phoneNumber);

    if (!is_null($customer) && !is_null($order)) {
      $text = self::messages['orderFound'] . "\n\n" . $order['name'] . ': ' . $order['status'];
      $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => $text)));
      $this->qApiClose($site, $appId, $appSecret, $conversation['id']);
    } else {
      $this->requestHuman($site, $appId, $appSecret, $conversation, $botState);
    }
  }

  // Request Human Action
  private function requestHuman($site, $appId, $appSecret, $conversation, &$botState)
  {
    $replies = array('replies' => array(array('text' => self::messages['yes']), array('text' => self::messages['tryAgain'])));
    $text = self::messages['orderNotFound'];
    $this->qApiSendMessage(
      $site,
      $appId,
      $appSecret,
      $conversation['id'],
      json_encode(array('text' => $text, 'quiqReply' => $replies))
    );
    $botState['last-action'] = 'request-human';
  }

  // Request Human Response Handler
  private function requestHumanResponseHandler($site, $appId, $appSecret, $conversation, &$botState)
  {
    $text = strtolower($this->getLastMessage($conversation));
    $tryAgain = strtolower(self::messages['tryAgain']);

    if (strpos($text, $tryAgain) !== false) {
      $this->promptOrderNumber($site, $appId, $appSecret, $conversation, $botState);
    } else {
      $this->qApiSendMessage(
        $site,
        $appId,
        $appSecret,
        $conversation['id'],
        json_encode(array('text' => self::messages['connectToAgent']))
      );
      // TODO: Update queue
      $this->qApiSendToQueue(
        $site,
        $appId,
        $appSecret,
        $conversation['id'],
        json_encode(array('targetQueue' => 'default'))
      );
    }
  }
}
